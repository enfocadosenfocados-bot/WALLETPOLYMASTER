"""
Motor de Ejecución Dual + Gestor Dinámico de Margen ($1,000 USDC) + Auto-Merge / Auto-Conversion On-Chain:
1. Controla el margen bloqueado en órdenes abiertas + inventario por cada una de las 10 estrategias.
2. Protege una Reserva Intocable de Cobertura ($120 USDC) para que NUNCA falte margen al cerrar la Pata B de un arbitraje.
3. Ejecuta automáticamente MERGE y CONVERSION (estilo e46m3 y Bigggggggg) para liberar el capital de vuelta a USDC en segundos.
"""
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from config import BotConfig

@dataclass
class OrderRecord:
    order_id: str
    condition_id: str
    token_id: str
    question: str
    outcome_label: str
    strategy_tag: str
    side: str          # 'BUY' o 'SELL'
    price: float
    size_shares: float
    post_only: bool
    is_hedge_leg: bool = False
    status: str = "OPEN"  # 'OPEN' | 'FILLED' | 'CANCELLED'
    created_at: float = field(default_factory=time.time)
    filled_at: Optional[float] = None

    @property
    def locked_usdc(self) -> float:
        # En Polymarket CLOB, una orden BUY abierta bloquea (price * size_shares) en USDC.e
        if self.side == "BUY" and self.status == "OPEN":
            return round(self.price * self.size_shares, 4)
        return 0.0

@dataclass
class ConditionInventory:
    condition_id: str
    question: str
    strategy_tag: str
    token_a: str
    token_b: str
    outcome_a: str
    outcome_b: str
    shares_a: float = 0.0
    cost_usdc_a: float = 0.0
    shares_b: float = 0.0
    cost_usdc_b: float = 0.0
    realized_spread_pnl: float = 0.0
    realized_merge_conv_pnl: float = 0.0
    maker_rebates_earned: float = 0.0
    friction_costs_usdc: float = 0.0
    merge_conv_count: int = 0
    fills_count: int = 0
    queue_missed_count: int = 0
    legging_exits_count: int = 0
    unhedged_since: Optional[float] = None

    @property
    def vwap_a(self) -> float:
        return round(self.cost_usdc_a / self.shares_a, 4) if self.shares_a > 0 else 0.0

    @property
    def vwap_b(self) -> float:
        return round(self.cost_usdc_b / self.shares_b, 4) if self.shares_b > 0 else 0.0

    @property
    def matched_dutch_book_shares(self) -> float:
        return min(self.shares_a, self.shares_b)

    @property
    def locked_dutch_book_profit(self) -> float:
        matched = self.matched_dutch_book_shares
        if matched <= 0:
            return 0.0
        combined_vwap = self.vwap_a + self.vwap_b
        return round(matched * (1.0 - combined_vwap), 4)

class ExecutionEngine:
    def __init__(self, config: BotConfig):
        self.cfg = config
        self.open_orders: Dict[str, OrderRecord] = {}
        self.filled_orders: List[OrderRecord] = []
        self.total_fills_count: int = 0
        self.total_queue_missed_count: int = 0
        self.total_legging_exits_count: int = 0
        self.total_friction_costs_usdc: float = 0.0
        self.inventories: Dict[str, ConditionInventory] = {}
        self.peak_strategy_committed_usdc: Dict[str, float] = {}
        self.total_recycled_by_strategy: Dict[str, float] = {}
        self.total_exposure_usdc: float = 0.0
        self.total_recycled_usdc: float = 0.0
        self.onchain_ops_count: int = 0
        self.clob_client = None

        if self.cfg.LIVE_TRADING:
            self._init_live_clob_client()

    def _init_live_clob_client(self):
        from py_clob_client.client import ClobClient
        from py_clob_client.clob_types import ApiCreds

        creds = None
        if self.cfg.POLY_API_KEY and self.cfg.POLY_API_SECRET and self.cfg.POLY_API_PASSPHRASE:
            creds = ApiCreds(
                api_key=self.cfg.POLY_API_KEY,
                api_secret=self.cfg.POLY_API_SECRET,
                api_passphrase=self.cfg.POLY_API_PASSPHRASE,
            )
        self.clob_client = ClobClient(
            host=self.cfg.CLOB_HOST,
            key=self.cfg.PRIVATE_KEY,
            chain_id=self.cfg.CHAIN_ID,
            creds=creds,
            signature_type=self.cfg.SIGNATURE_TYPE,
            funder=self.cfg.FUNDER_ADDRESS or None,
        )
        if not creds:
            self.clob_client.set_api_creds(self.clob_client.create_or_derive_api_creds())

    # =========================================================================
    # GESTOR DINÁMICO DE MARGEN ($1,000 REAL / 6 CAMPEONAS O $10,000 TORNEO)
    # =========================================================================
    def get_open_order_margin_usdc(self, strategy_tag: Optional[str] = None) -> float:
        return round(
            sum(
                o.locked_usdc for o in self.open_orders.values()
                if o.status == "OPEN" and (strategy_tag is None or o.strategy_tag == strategy_tag)
            ),
            2,
        )

    def get_invested_inventory_usdc(self, strategy_tag: Optional[str] = None) -> float:
        return round(
            sum(
                (inv.cost_usdc_a + inv.cost_usdc_b)
                for inv in self.inventories.values()
                if strategy_tag is None or inv.strategy_tag == strategy_tag
            ),
            2,
        )

    def get_strategy_committed_usdc(self, strategy_tag: str) -> float:
        val = round(
            self.get_open_order_margin_usdc(strategy_tag) + self.get_invested_inventory_usdc(strategy_tag),
            2,
        )
        if val > self.peak_strategy_committed_usdc.get(strategy_tag, 0.0):
            self.peak_strategy_committed_usdc[strategy_tag] = val
        return val

    def get_total_committed_usdc(self) -> float:
        return round(self.get_open_order_margin_usdc() + self.get_invested_inventory_usdc(), 2)

    def get_free_margin_usdc(self, include_hedge_reserve: bool = False) -> float:
        cap = self.cfg.TOTAL_BANKROLL_USDC if include_hedge_reserve else self.cfg.MAX_TOTAL_EXPOSURE_USDC
        return round(max(0.0, cap - self.get_total_committed_usdc()), 2)

    def can_allocate_margin(self, strategy_tag: str, usdc_amount: float, is_hedge_leg: bool = False) -> bool:
        strat_committed = self.get_strategy_committed_usdc(strategy_tag)

        if self.cfg.PORTFOLIO_MODE == "TOURNAMENT_10K_EQUAL":
            if is_hedge_leg:
                return (strat_committed + usdc_amount) <= self.cfg.TOURNAMENT_STRATEGY_TOTAL_USDC
            return (strat_committed + usdc_amount) <= self.cfg.TOURNAMENT_STRATEGY_ENTRY_CAP_USDC

        if is_hedge_leg:
            return (self.get_total_committed_usdc() + usdc_amount) <= self.cfg.TOTAL_BANKROLL_USDC

        strat_cap = self.cfg.STRATEGY_MAX_BUDGET_USDC.get(strategy_tag, 80.0)
        if strat_cap <= 0.0:
            return False
        if self.cfg.PORTFOLIO_MODE == "CORE_CONCENTRATED":
            strat_cap *= 1.8

        if (strat_committed + usdc_amount) > strat_cap:
            return False

        return (self.get_total_committed_usdc() + usdc_amount) <= self.cfg.MAX_TOTAL_EXPOSURE_USDC

    def register_market_inventory(
        self, condition_id: str, question: str, strategy_tag: str,
        token_a: str, token_b: str, outcome_a: str, outcome_b: str
    ):
        if condition_id not in self.inventories:
            self.inventories[condition_id] = ConditionInventory(
                condition_id=condition_id,
                question=question,
                strategy_tag=strategy_tag,
                token_a=token_a,
                token_b=token_b,
                outcome_a=outcome_a,
                outcome_b=outcome_b,
            )

    def has_open_order(self, token_id: str, side: str) -> bool:
        return any(
            o.token_id == token_id and o.side == side and o.status == "OPEN"
            for o in self.open_orders.values()
        )

    def place_limit_order(
        self,
        condition_id: str,
        token_id: str,
        question: str,
        outcome_label: str,
        strategy_tag: str,
        side: str,
        price: float,
        usdc_amount: Optional[float] = None,
        post_only: bool = True,
        best_bid: float = 0.0,
        best_ask: float = 1.0,
        is_hedge_leg: bool = False,
    ) -> Optional[OrderRecord]:
        if usdc_amount is None:
            usdc_amount = self.cfg.STRATEGY_ORDER_SIZE_USDC.get(strategy_tag, self.cfg.ORDER_SIZE_USDC)
        if usdc_amount <= 0:
            return None

        price = round(price, 3)
        min_allowed_px = 0.002 if strategy_tag == "S10_TENNIS_PENNY_DUST" else 0.005
        if price < min_allowed_px or price >= 0.996:
            return None

        # Regla Post-Only: garantizar ejecución 100% Maker ($0.00 fee + Maker Rebates)
        if post_only:
            if side == "BUY" and best_ask > 0 and price >= best_ask:
                price = round(best_ask - 0.005 if price < 0.05 else best_ask - 0.01, 3)
            elif side == "SELL" and best_bid > 0 and price <= best_bid:
                price = round(best_bid + 0.01, 3)
            if price < min_allowed_px or price >= 0.996:
                return None

        if side == "BUY" and not self.can_allocate_margin(strategy_tag, usdc_amount, is_hedge_leg=is_hedge_leg):
            return None

        size_shares = round(usdc_amount / price, 2)
        if size_shares < 5.0:
            size_shares = 5.0
            usdc_amount = round(size_shares * price, 4)

        order_id = f"sim-{uuid.uuid4().hex[:10]}"

        if self.cfg.LIVE_TRADING and self.clob_client:
            try:
                from py_clob_client.clob_types import OrderArgs, OrderType
                from py_clob_client.order_builder.constants import BUY, SELL

                clob_side = BUY if side == "BUY" else SELL
                signed_order = self.clob_client.create_order(
                    OrderArgs(price=price, size=size_shares, side=clob_side, token_id=token_id)
                )
                resp = self.clob_client.post_order(signed_order, OrderType.GTC, post_only=post_only)
                order_id = resp.get("orderID") or order_id
            except Exception as e:
                print(f"  [CLOB ERROR] Rechazo de orden ({strategy_tag}): {e}")
                return None

        rec = OrderRecord(
            order_id=order_id,
            condition_id=condition_id,
            token_id=token_id,
            question=question,
            outcome_label=outcome_label,
            strategy_tag=strategy_tag,
            side=side,
            price=price,
            size_shares=size_shares,
            post_only=post_only,
            is_hedge_leg=is_hedge_leg,
        )
        self.open_orders[order_id] = rec
        return rec

    def cancel_orders_for_token(self, token_id: str, reason: str = ""):
        to_cancel = [
            oid for oid, o in self.open_orders.items()
            if o.token_id == token_id and o.status == "OPEN"
        ]
        for oid in to_cancel:
            if self.cfg.LIVE_TRADING and self.clob_client:
                try:
                    self.clob_client.cancel(oid)
                except Exception:
                    pass
            self.open_orders[oid].status = "CANCELLED"
            del self.open_orders[oid]

    def cancel_entry_orders_for_condition(self, condition_id: str, include_hedge: bool = False) -> int:
        to_cancel = [
            oid for oid, o in self.open_orders.items()
            if o.condition_id == condition_id
            and o.status == "OPEN"
            and (include_hedge or not o.is_hedge_leg)
        ]
        for oid in to_cancel:
            if self.cfg.LIVE_TRADING and self.clob_client:
                try:
                    self.clob_client.cancel(oid)
                except Exception:
                    pass
            self.open_orders[oid].status = "CANCELLED"
            del self.open_orders[oid]
        return len(to_cancel)

    def prune_stale_entry_orders(self, live_book_state: Dict[str, Dict[str, float]], now: float) -> int:
        cancelled = 0
        for oid, o in list(self.open_orders.items()):
            if o.status != "OPEN" or o.is_hedge_leg or o.strategy_tag == "S10_TENNIS_PENNY_DUST":
                continue
            age = now - o.created_at
            if age < self.cfg.STALE_ENTRY_ORDER_TIMEOUT_SEC:
                continue
            st = live_book_state.get(o.token_id)
            if st and st.get("bid", 0.0) > 0:
                drift = abs(st["bid"] - o.price)
                if drift >= self.cfg.REQUOTE_PRICE_DRIFT_THRESHOLD:
                    if self.cfg.LIVE_TRADING and self.clob_client:
                        try:
                            self.clob_client.cancel(oid)
                        except Exception:
                            pass
                    o.status = "CANCELLED"
                    del self.open_orders[oid]
                    cancelled += 1
        return cancelled

    def prune_unhedged_legging_risk(self, live_book_state: Dict[str, Dict[str, float]], now: float) -> int:
        """
        SIMULACIÓN Y GESTIÓN REALISTA DE "PATA COJA" (LEGGING RISK + SPREAD + SLIPPAGE):
        Si una estrategia compró la Pata A pero el partido se fue en contra (o pasó el tiempo máximo sin que se llene la Pata B):
        - Liquidamos el excedente no emparejado al mejor Bid actual menos el Slippage/Fee de salida Taker.
        - Liberamos el margen de vuelta a la cuenta y registramos la pérdida/costo de spread en realized_spread_pnl y friction_costs_usdc.
        """
        if not self.cfg.REALISTIC_FRICTION_ENABLED:
            return 0

        exits = 0
        for cid, inv in list(self.inventories.items()):
            if inv.strategy_tag == "S10_TENNIS_PENNY_DUST":
                continue
            unhedged_a = round(inv.shares_a - inv.shares_b, 4)
            unhedged_b = round(inv.shares_b - inv.shares_a, 4)
            if unhedged_a < 1.0 and unhedged_b < 1.0:
                inv.unhedged_since = None
                continue

            if inv.unhedged_since is None:
                inv.unhedged_since = now
                continue

            elapsed_unhedged = now - inv.unhedged_since
            max_wait = (
                self.cfg.LEGGING_PREMATCH_UNHEDGED_SEC
                if inv.strategy_tag in ("S1_VIGFREE_MAKER", "S7_SPREAD_MIDDLING")
                else self.cfg.LEGGING_MAX_UNHEDGED_SEC
            )

            if unhedged_a >= 1.0:
                st = live_book_state.get(inv.token_a, {})
                curr_bid = st.get("bid", 0.0)
                if curr_bid <= 0:
                    continue
                price_drop = inv.vwap_a - curr_bid
                if elapsed_unhedged >= max_wait or price_drop >= self.cfg.LEGGING_STOP_LOSS_DROP_CENTS:
                    slippage_px = round(max(0.002, curr_bid * self.cfg.TAKER_EMERGENCY_SLIPPAGE_BPS), 4)
                    exit_px = round(max(0.005, curr_bid - slippage_px), 4)
                    cost_basis = round(unhedged_a * inv.vwap_a, 4)
                    proceeds = round(unhedged_a * exit_px, 4)
                    spread_slip_loss = round(proceeds - cost_basis, 4)
                    friction_hit = round(max(0.0, cost_basis - proceeds), 4)

                    inv.realized_spread_pnl = round(inv.realized_spread_pnl + spread_slip_loss, 4)
                    inv.friction_costs_usdc = round(inv.friction_costs_usdc + friction_hit, 4)
                    self.total_friction_costs_usdc = round(self.total_friction_costs_usdc + friction_hit, 4)
                    inv.shares_a = round(max(0.0, inv.shares_a - unhedged_a), 4)
                    inv.cost_usdc_a = round(inv.shares_a * inv.vwap_a, 4)
                    inv.unhedged_since = None
                    inv.legging_exits_count += 1
                    self.total_legging_exits_count += 1
                    self.total_exposure_usdc = max(0.0, self.total_exposure_usdc - cost_basis)
                    self.cancel_entry_orders_for_condition(cid, include_hedge=True)
                    exits += 1
                    print(
                        f"  🛡️ [LEGGING SCRATCH/STOP {inv.strategy_tag}] Cerrada pata suelta ({unhedged_a:.1f} sh '{inv.outcome_a}') "
                        f"en '{inv.question[:34]}' @ Bid ${exit_px:.3f} (VWAP ${inv.vwap_a:.3f}) -> "
                        f"Costo Spread/Slippage: ${spread_slip_loss:+.3f} USDC | Margen liberado"
                    )

            elif unhedged_b >= 1.0:
                st = live_book_state.get(inv.token_b, {})
                curr_bid = st.get("bid", 0.0)
                if curr_bid <= 0:
                    continue
                price_drop = inv.vwap_b - curr_bid
                if elapsed_unhedged >= max_wait or price_drop >= self.cfg.LEGGING_STOP_LOSS_DROP_CENTS:
                    slippage_px = round(max(0.002, curr_bid * self.cfg.TAKER_EMERGENCY_SLIPPAGE_BPS), 4)
                    exit_px = round(max(0.005, curr_bid - slippage_px), 4)
                    cost_basis = round(unhedged_b * inv.vwap_b, 4)
                    proceeds = round(unhedged_b * exit_px, 4)
                    spread_slip_loss = round(proceeds - cost_basis, 4)
                    friction_hit = round(max(0.0, cost_basis - proceeds), 4)

                    inv.realized_spread_pnl = round(inv.realized_spread_pnl + spread_slip_loss, 4)
                    inv.friction_costs_usdc = round(inv.friction_costs_usdc + friction_hit, 4)
                    self.total_friction_costs_usdc = round(self.total_friction_costs_usdc + friction_hit, 4)
                    inv.shares_b = round(max(0.0, inv.shares_b - unhedged_b), 4)
                    inv.cost_usdc_b = round(inv.shares_b * inv.vwap_b, 4)
                    inv.unhedged_since = None
                    inv.legging_exits_count += 1
                    self.total_legging_exits_count += 1
                    self.total_exposure_usdc = max(0.0, self.total_exposure_usdc - cost_basis)
                    self.cancel_entry_orders_for_condition(cid, include_hedge=True)
                    exits += 1
                    print(
                        f"  🛡️ [LEGGING SCRATCH/STOP {inv.strategy_tag}] Cerrada pata suelta ({unhedged_b:.1f} sh '{inv.outcome_b}') "
                        f"en '{inv.question[:34]}' @ Bid ${exit_px:.3f} (VWAP ${inv.vwap_b:.3f}) -> "
                        f"Costo Spread/Slippage: ${spread_slip_loss:+.3f} USDC | Margen liberado"
                    )

        return exits

    def on_market_tick_simulate_fills(
        self, token_id: str, live_best_bid: float, live_best_ask: float, last_trade_price: Optional[float] = None
    ) -> List[OrderRecord]:
        newly_filled: List[OrderRecord] = []
        for oid, order in list(self.open_orders.items()):
            if order.token_id != token_id or order.status != "OPEN":
                continue

            crossed_through = False
            touched_exact = False

            if order.side == "BUY":
                if (0 < live_best_ask < order.price) or (last_trade_price is not None and 0 < last_trade_price < order.price):
                    crossed_through = True
                elif (live_best_ask == order.price) or (last_trade_price is not None and last_trade_price == order.price):
                    touched_exact = True
            elif order.side == "SELL":
                if (live_best_bid > order.price) or (last_trade_price is not None and last_trade_price > order.price):
                    crossed_through = True
                elif (live_best_bid == order.price) or (last_trade_price is not None and last_trade_price == order.price):
                    touched_exact = True

            filled = False
            if crossed_through:
                filled = True
            elif touched_exact:
                if self.cfg.REALISTIC_FRICTION_ENABLED:
                    # Simulación de Prioridad de Cola FIFO: cuando el precio solo toca nuestro límite sin atravesarlo,
                    # aplicamos la probabilidad real de estar adelante en la cola según la estrategia.
                    q_prob = self.cfg.QUEUE_TOUCH_FILL_PROB.get(order.strategy_tag, 0.65)
                    if random.random() <= q_prob:
                        filled = True
                    else:
                        inv = self.inventories.get(order.condition_id)
                        if inv:
                            inv.queue_missed_count += 1
                        self.total_queue_missed_count += 1
                else:
                    filled = True

            if filled:
                order.status = "FILLED"
                order.filled_at = time.time()
                del self.open_orders[oid]
                self.filled_orders.append(order)
                if len(self.filled_orders) > 5000:
                    self.filled_orders = self.filled_orders[-2500:]
                self._apply_fill_to_inventory(order)
                newly_filled.append(order)

        return newly_filled

    def _apply_fill_to_inventory(self, order: OrderRecord):
        inv = self.inventories.get(order.condition_id)
        if not inv:
            return
        inv.fills_count += 1
        self.total_fills_count += 1
        usdc_val = round(order.price * order.size_shares, 4)
        rebate_rate = (
            self.cfg.REALISTIC_MAKER_REBATE_RATE
            if self.cfg.REALISTIC_FRICTION_ENABLED
            else 0.0015
        )
        rebate = round(usdc_val * rebate_rate, 4) if order.post_only else 0.0
        inv.maker_rebates_earned += rebate

        if order.side == "BUY":
            self.total_exposure_usdc += usdc_val
            if order.token_id == inv.token_a:
                inv.shares_a += order.size_shares
                inv.cost_usdc_a += usdc_val
            elif order.token_id == inv.token_b:
                inv.shares_b += order.size_shares
                inv.cost_usdc_b += usdc_val
        elif order.side == "SELL":
            self.total_exposure_usdc = max(0.0, self.total_exposure_usdc - usdc_val)
            if order.token_id == inv.token_a and inv.shares_a > 0:
                avg_cost = inv.vwap_a
                pnl = (order.price - avg_cost) * min(order.size_shares, inv.shares_a)
                inv.realized_spread_pnl += round(pnl, 4)
                inv.shares_a = max(0.0, inv.shares_a - order.size_shares)
                inv.cost_usdc_a = round(inv.shares_a * avg_cost, 4)
            elif order.token_id == inv.token_b and inv.shares_b > 0:
                avg_cost = inv.vwap_b
                pnl = (order.price - avg_cost) * min(order.size_shares, inv.shares_b)
                inv.realized_spread_pnl += round(pnl, 4)
                inv.shares_b = max(0.0, inv.shares_b - order.size_shares)
                inv.cost_usdc_b = round(inv.shares_b * avg_cost, 4)

        # Actualizar reloj de exposición de pata suelta (unhedged_since)
        if abs(inv.shares_a - inv.shares_b) >= 1.0:
            if inv.unhedged_since is None:
                inv.unhedged_since = time.time()
        else:
            inv.unhedged_since = None

        # AUTO-RECICLAJE DE MARGEN (CONVERSION + MERGE ON-CHAIN):
        if inv.matched_dutch_book_shares >= 5.0 and (inv.vwap_a + inv.vwap_b) < 1.0:
            self.execute_instant_merge_or_conversion(inv)

    def execute_instant_merge_or_conversion(self, inv: ConditionInventory):
        """
        Fusiona automáticamente (MERGE / CONVERSION) los pares complementarios (1 Yes + 1 No = $1.00 USDC)
        descontando el costo real de Gas en Polygon (POLYGON_MERGE_GAS_USDC) y liberando el capital al instante.
        """
        matched = inv.matched_dutch_book_shares
        if matched <= 0:
            return
        vwap_a = inv.vwap_a
        vwap_b = inv.vwap_b
        combined_cost = matched * (vwap_a + vwap_b)
        payout_usdc = matched * 1.00
        gas_fee_usdc = self.cfg.POLYGON_MERGE_GAS_USDC if self.cfg.REALISTIC_FRICTION_ENABLED else 0.0
        net_profit = round(payout_usdc - combined_cost - gas_fee_usdc, 4)

        if self.cfg.LIVE_TRADING and self.cfg.PRIVATE_KEY:
            try:
                from web3 import Web3
                w3 = Web3(Web3.HTTPProvider(self.cfg.POLYGON_RPC_URL))
                if w3.is_connected():
                    ctf_abi = [{
                        "constant": False,
                        "inputs": [
                            {"name": "collateralToken", "type": "address"},
                            {"name": "parentCollectionId", "type": "bytes32"},
                            {"name": "conditionId", "type": "bytes32"},
                            {"name": "partition", "type": "uint256[]"},
                            {"name": "amount", "type": "uint256"}
                        ],
                        "name": "mergePositions",
                        "outputs": [],
                        "type": "function"
                    }]
                    acct = w3.eth.account.from_key(self.cfg.PRIVATE_KEY)
                    ctf = w3.eth.contract(address=Web3.to_checksum_address(self.cfg.CTF_ADDRESS), abi=ctf_abi)
                    amt_raw = int(matched * 1e6)
                    tx = ctf.functions.mergePositions(
                        Web3.to_checksum_address(self.cfg.USDC_E_ADDRESS),
                        b"\x00" * 32,
                        bytes.fromhex(inv.condition_id.replace("0x", "")),
                        [1, 2],
                        amt_raw,
                    ).build_transaction({
                        "from": acct.address,
                        "nonce": w3.eth.get_transaction_count(acct.address),
                        "gas": 160000,
                        "gasPrice": int(w3.eth.gas_price * 1.15),
                        "chainId": 137,
                    })
                    signed = w3.eth.account.sign_transaction(tx, private_key=self.cfg.PRIVATE_KEY)
                    w3.eth.send_raw_transaction(signed.raw_transaction)
            except Exception as e:
                print(f"  [ON-CHAIN MERGE INFO] {e}")

        inv.shares_a = round(max(0.0, inv.shares_a - matched), 4)
        inv.shares_b = round(max(0.0, inv.shares_b - matched), 4)
        inv.cost_usdc_a = round(inv.shares_a * vwap_a, 4)
        inv.cost_usdc_b = round(inv.shares_b * vwap_b, 4)
        if abs(inv.shares_a - inv.shares_b) < 1.0:
            inv.unhedged_since = None
        inv.realized_merge_conv_pnl += net_profit
        inv.friction_costs_usdc = round(inv.friction_costs_usdc + gas_fee_usdc, 4)
        self.total_friction_costs_usdc = round(self.total_friction_costs_usdc + gas_fee_usdc, 4)
        inv.merge_conv_count += 1
        self.total_exposure_usdc = max(0.0, self.total_exposure_usdc - combined_cost)
        self.total_recycled_usdc += round(payout_usdc, 2)
        self.total_recycled_by_strategy[inv.strategy_tag] = round(
            self.total_recycled_by_strategy.get(inv.strategy_tag, 0.0) + payout_usdc, 2
        )
        self.onchain_ops_count += 1
        print(
            f"  ♻️ [AUTO-MERGE/CONVERSION {inv.strategy_tag}] Fusionadas {matched:.1f} acciones en '{inv.question[:36]}' "
            f"-> Liberados ${payout_usdc:.2f} USDC (Ganancia Neta tras Gas -${gas_fee_usdc:.3f}: ${net_profit:+.3f} USDC)"
        )
