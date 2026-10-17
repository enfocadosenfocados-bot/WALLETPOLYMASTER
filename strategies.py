"""
Máquinas de Estado de las 10 Estrategias Cuantitativas Autónomas (Lote 1 + Lote 2):
LOTE 1:
  1. S1_VIGFREE_MAKER        (hi774c / HomeRunHazard: Spreads & Totales 50/50 Vig-Free + Cierre Dual)
  2. S2_LIVE_DUTCHBOOK       (PEYZ-BIGGEST-FAN / RN1: Gamma Scalping en Vivo VWAP_A + VWAP_B <= $0.945)
  3. S3_POSTONLY_4LEG_MM     (calculate10: Market Making HFT Post-Only de 4 Patas + Filtro de Desbalance)
  4. S4_NEGRISK_ARB          (BreakTheBank / Nooserac: Absorción Pasiva Anti-Favorito en Eventos NegRisk)
LOTE 2 (NUEVAS):
  5. S5_NEGRISK_CONV_MERGE   (e46m3: Motor NegRisk CONVERSION + MERGE + Bonos Piso, 98.2% Win Rate)
  6. S6_LONGSHOT_SELL_MAKER  (Bigggggggg: Cosechador Maker en Venta de Longshots $0.04-$0.26 vía Split/Conv)
  7. S7_SPREAD_MIDDLING      (justaluckydude: Escalera de Hándicaps Alternativos / Spread Middling para cobrar $2.00)
  8. S8_NICHE_PROPS_CORNERS  (omnibus-076daa: Props de Nicho, Total de Córners O/U y Hándicaps de Mapas)
  9. S9_NCAAF_NFL_DEEP_ARB   (primm: Dutch-Book Profundo 0% Fee en Fútbol Americano NCAAF/NFL)
 10. S10_TENNIS_PENNY_DUST   (01258787xy...: Redes de Arrastre $0.002-$0.015 y Dual-Outcome en Tenis)
"""
from typing import Dict, List
from config import BotConfig
from market_scanner import SelectedMarket
from execution_engine import ExecutionEngine, OrderRecord

class MultiStrategyCoordinator:
    def __init__(self, config: BotConfig, engine: ExecutionEngine):
        self.cfg = config
        self.engine = engine
        self.tracked_markets_by_token: Dict[str, SelectedMarket] = {}
        self.live_book_state: Dict[str, Dict[str, float]] = {}
        self.rolling_ema_mid: Dict[str, float] = {}

    def register_selected_markets(self, bucketed_markets: Dict[str, List[SelectedMarket]]) -> List[str]:
        """Registra los mercados de las 10 estrategias y despliega las órdenes iniciales dentro del presupuesto de $1,000 USDC."""
        all_token_ids: List[str] = []
        for strategy_tag, mlist in bucketed_markets.items():
            for sm in mlist:
                self.engine.register_market_inventory(
                    condition_id=sm.condition_id,
                    question=sm.question,
                    strategy_tag=sm.strategy_tag,
                    token_a=sm.token_a,
                    token_b=sm.token_b,
                    outcome_a=sm.outcome_a,
                    outcome_b=sm.outcome_b,
                )
                self.tracked_markets_by_token[sm.token_a] = sm
                self.tracked_markets_by_token[sm.token_b] = sm
                all_token_ids.extend([sm.token_a, sm.token_b])

                self.live_book_state[sm.token_a] = {"bid": sm.best_bid_a, "ask": sm.best_ask_a}
                self.live_book_state[sm.token_b] = {"bid": sm.best_bid_b, "ask": sm.best_ask_b}
                self.rolling_ema_mid[sm.token_a] = (sm.best_bid_a + sm.best_ask_a) / 2.0
                self.rolling_ema_mid[sm.token_b] = (sm.best_bid_b + sm.best_ask_b) / 2.0

                self._seed_initial_strategy_orders(sm)

        return list(dict.fromkeys(all_token_ids))

    def _seed_initial_strategy_orders(self, sm: SelectedMarket):
        """Despliega las órdenes límite pasivas iniciales (postOnly=True) para las 10 estrategias."""
        tag = sm.strategy_tag

        # --- S1: Pre-Match Spreads & Totals (hi774c / HomeRunHazard) ---
        if tag == "S1_VIGFREE_MAKER":
            target_bid_a = min(sm.best_bid_a, 0.490)
            target_bid_b = min(sm.best_bid_b, round(self.cfg.S1_MAX_COMBINED_COST - target_bid_a, 3))
            self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", target_bid_a, sm.best_bid_a, sm.best_ask_a)
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", target_bid_b, sm.best_bid_b, sm.best_ask_b)

        # --- S2: In-Play Gamma Scalping / Dutch-Book (PEYZ-BIGGEST-FAN / RN1) ---
        elif tag == "S2_LIVE_DUTCHBOOK":
            dip_entry_a = round(max(0.05, sm.best_bid_a - 0.02), 3)
            self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", dip_entry_a, sm.best_bid_a, sm.best_ask_a)

        # --- S3: 4-Leg Post-Only HFT Market Maker (calculate10) ---
        elif tag == "S3_POSTONLY_4LEG_MM":
            inside_bid_a = round(sm.best_bid_a + sm.tick_size, 3)
            inside_ask_a = round(sm.best_ask_a - sm.tick_size, 3)
            if inside_bid_a < inside_ask_a:
                self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", inside_bid_a, sm.best_bid_a, sm.best_ask_a)
                synth_bid_b = round(1.0 - inside_ask_a, 3)
                self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", synth_bid_b, sm.best_bid_b, sm.best_ask_b)

        # --- S4: Anti-Hype & Matriz Negative-Risk (BreakTheBank / Nooserac) ---
        elif tag == "S4_NEGRISK_ARB":
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", sm.best_bid_b, sm.best_bid_b, sm.best_ask_b)

        # --- S5 (NUEVA - e46m3): Motor NegRisk CONVERSION + MERGE + Floor Bonds ---
        elif tag == "S5_NEGRISK_CONV_MERGE":
            mode = sm.metadata.get("mode", "NEGRISK_CONVERSION_MERGE")
            if mode == "NEGRISK_CONVERSION_MERGE":
                # Compramos la pata de cola subvaluada y la pata complementaria para activar CONVERSION + MERGE
                entry_a = round(min(sm.best_bid_a + sm.tick_size, sm.best_ask_a - sm.tick_size), 3)
                if entry_a <= 0:
                    entry_a = sm.best_bid_a
                target_b = round(min(sm.best_bid_b, 0.990 - entry_a), 3)
                self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", entry_a, sm.best_bid_a, sm.best_ask_a)
                self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", target_b, sm.best_bid_b, sm.best_ask_b)
            else:
                # Bono de piso de alta probabilidad ($0.955 - $0.990) con $0.00 fee Maker
                if sm.best_bid_a >= self.cfg.S5_FLOOR_BOND_MIN_BID:
                    self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", sm.best_bid_a, sm.best_bid_a, sm.best_ask_a)
                else:
                    self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", sm.best_bid_b, sm.best_bid_b, sm.best_ask_b)

        # --- S6 (NUEVA - Bigggggggg): Cosechador Maker en Venta de Longshots ($0.04-$0.26) ---
        elif tag == "S6_LONGSHOT_SELL_MAKER":
            # En Polymarket CLOB, vender como Maker el Longshot Yes a Ask_A tras hacer SPLIT/CONVERSION
            # equivale exactamente a cotizar BUY Post-Only en el token 'No' (token_b) a (1.00 - Ask_A + 1 tick),
            # cosechando la decadencia de la "lotería" retail con $0.00 de comisión + Maker Rebates.
            synth_sell_longshot_px = round(min(sm.best_bid_b + sm.tick_size, sm.best_ask_b - sm.tick_size), 3)
            if synth_sell_longshot_px <= 0:
                synth_sell_longshot_px = sm.best_bid_b
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", synth_sell_longshot_px, sm.best_bid_b, sm.best_ask_b)

        # --- S7 (NUEVA - justaluckydude): Escalera de Hándicaps Alternativos / Spread Middling ---
        elif tag == "S7_SPREAD_MIDDLING":
            # Cotizamos ambos lados de la ventana de Spread buscando un costo combinado <= 0.915
            # Si el resultado cae en el "Middle" (ej. ventaja de 7 a 10 pts), ¡ambas patas pagan $1.00 ($2.00 total)!
            leg_a_px = round(min(sm.best_bid_a, 0.465), 3)
            leg_b_px = round(min(sm.best_bid_b, self.cfg.S7_TARGET_MIDDLE_SUM - leg_a_px), 3)
            self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", leg_a_px, sm.best_bid_a, sm.best_ask_a)
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", leg_b_px, sm.best_bid_b, sm.best_ask_b)

        # --- S8 (NUEVA - omnibus-076daa): Props de Nicho, Total de Córners y Hándicaps de Mapas ---
        elif tag == "S8_NICHE_PROPS_CORNERS":
            # Libros secundarios sin competencia HFT: nos posicionamos en ambos lados con margen amplio
            bid_a_target = round(min(sm.best_bid_a, 0.480), 3)
            bid_b_target = round(min(sm.best_bid_b, self.cfg.S8_TARGET_COMBINED_COST - bid_a_target), 3)
            self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", bid_a_target, sm.best_bid_a, sm.best_ask_a)
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", bid_b_target, sm.best_bid_b, sm.best_ask_b)

        # --- S9 (NUEVA - primm): Dutch-Book Profundo 0% Fee en Fútbol Americano (NCAAF/NFL) ---
        elif tag == "S9_NCAAF_NFL_DEEP_ARB":
            # Entra en el lado subvaluado y deja la trampa profunda (sum_vwap <= 0.86) para capturar touchdowns
            entry_a = round(max(0.10, sm.best_bid_a - 0.01), 3)
            deep_b = round(max(0.08, self.cfg.S9_DEEP_ARB_SUM_TARGET - entry_a), 3)
            self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", entry_a, sm.best_bid_a, sm.best_ask_a)
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", deep_b, sm.best_bid_b, sm.best_ask_b)

        # --- S10 (NUEVA - 01258787xy...): Redes de Arrastre ($0.002-$0.015) y Dual-Outcome en Tenis ---
        elif tag == "S10_TENNIS_PENNY_DUST":
            # Coloca redes de arrastre ultra-baratas ($2.50 USDC por orden) en ambos lados del partido de Tenis
            # para atrapar ventas de mercado en pánico durante remontadas de sets.
            stink_px = self.cfg.S10_STINK_BID_PRICE
            self._place_if_absent(sm, sm.token_a, sm.outcome_a, "BUY", stink_px, sm.best_bid_a, sm.best_ask_a)
            self._place_if_absent(sm, sm.token_b, sm.outcome_b, "BUY", stink_px, sm.best_bid_b, sm.best_ask_b)

    def _place_if_absent(
        self, sm: SelectedMarket, token_id: str, outcome_label: str,
        side: str, price: float, best_bid: float, best_ask: float, is_hedge_leg: bool = False
    ):
        if not self.engine.has_open_order(token_id, side):
            self.engine.place_limit_order(
                condition_id=sm.condition_id,
                token_id=token_id,
                question=sm.question,
                outcome_label=outcome_label,
                strategy_tag=sm.strategy_tag,
                side=side,
                price=price,
                usdc_amount=None,  # Usa automáticamente STRATEGY_ORDER_SIZE_USDC[strategy_tag]
                post_only=True,
                best_bid=best_bid,
                best_ask=best_ask,
                is_hedge_leg=is_hedge_leg,
            )

    def on_ws_tick(
        self, token_id: str, best_bid: float, best_ask: float,
        bid_depth_shares: float = 0.0, ask_depth_shares: float = 0.0,
        last_trade_price: float = 0.0
    ):
        sm = self.tracked_markets_by_token.get(token_id)
        if not sm:
            return

        if best_bid > 0 and best_ask > 0:
            self.live_book_state[token_id] = {"bid": best_bid, "ask": best_ask}
            mid = (best_bid + best_ask) / 2.0
            prev_ema = self.rolling_ema_mid.get(token_id, mid)
            self.rolling_ema_mid[token_id] = round(0.85 * prev_ema + 0.15 * mid, 4)

        # 1. Protección de Selección Adversa HFT (Estrategia 3 - calculate10):
        if sm.strategy_tag == "S3_POSTONLY_4LEG_MM" and (bid_depth_shares + ask_depth_shares) > 100:
            imbalance = ask_depth_shares / (bid_depth_shares + ask_depth_shares)
            if imbalance >= self.cfg.S3_IMBALANCE_CANCEL_RATIO:
                self.engine.cancel_orders_for_token(token_id, reason="L2 Orderbook Imbalance")
                return

        # 2. Verificar fills en tiempo real
        fills = self.engine.on_market_tick_simulate_fills(
            token_id=token_id,
            live_best_bid=best_bid,
            live_best_ask=best_ask,
            last_trade_price=last_trade_price if last_trade_price > 0 else None,
        )

        # 3. Reacción instantánea tras un Fill (usando la Reserva de Cobertura is_hedge_leg=True)
        for fill in fills:
            self._on_order_filled(sm, fill)

    def _on_order_filled(self, sm: SelectedMarket, fill: OrderRecord):
        inv = self.engine.inventories.get(sm.condition_id)
        if not inv:
            return

        print(
            f"  ⚡ [FILL {fill.strategy_tag}] {fill.side} {fill.size_shares:.1f} sh de '{fill.outcome_label}' "
            f"en '{sm.question[:38]}' @ ${fill.price:.3f} | "
            f"Margen Libre=${self.engine.get_free_margin_usdc():,.2f} | Rebate=${inv.maker_rebates_earned:+.3f}"
        )

        # Cierre automático de Segunda Pata (Dutch-Book / Middling / Niche Props / NegRisk)
        # Usa is_hedge_leg=True para tener acceso garantizado a los $120 USDC de Reserva de Cobertura
        if fill.side == "BUY" and sm.strategy_tag in (
            "S1_VIGFREE_MAKER",
            "S2_LIVE_DUTCHBOOK",
            "S5_NEGRISK_CONV_MERGE",
            "S7_SPREAD_MIDDLING",
            "S8_NICHE_PROPS_CORNERS",
            "S9_NCAAF_NFL_DEEP_ARB",
        ):
            target_sum = {
                "S1_VIGFREE_MAKER": self.cfg.S1_MAX_COMBINED_COST,
                "S2_LIVE_DUTCHBOOK": self.cfg.S2_TARGET_DUTCH_BOOK_SUM,
                "S5_NEGRISK_CONV_MERGE": 0.990,
                "S7_SPREAD_MIDDLING": self.cfg.S7_TARGET_MIDDLE_SUM,
                "S8_NICHE_PROPS_CORNERS": self.cfg.S8_TARGET_COMBINED_COST,
                "S9_NCAAF_NFL_DEEP_ARB": self.cfg.S9_DEEP_ARB_SUM_TARGET,
            }.get(sm.strategy_tag, 0.950)

            if fill.token_id == sm.token_a and inv.shares_a > inv.shares_b:
                target_b = round(max(0.01, target_sum - inv.vwap_a), 3)
                b_state = self.live_book_state.get(sm.token_b, {"bid": sm.best_bid_b, "ask": sm.best_ask_b})
                self.engine.place_limit_order(
                    condition_id=sm.condition_id,
                    token_id=sm.token_b,
                    question=sm.question,
                    outcome_label=sm.outcome_b,
                    strategy_tag=sm.strategy_tag,
                    side="BUY",
                    price=target_b,
                    usdc_amount=round(fill.size_shares * target_b, 2),
                    post_only=True,
                    best_bid=b_state["bid"],
                    best_ask=b_state["ask"],
                    is_hedge_leg=True,  # Acceso prioritario a la Reserva de Cobertura ($120 USDC)
                )
            elif fill.token_id == sm.token_b and inv.shares_b > inv.shares_a:
                target_a = round(max(0.01, target_sum - inv.vwap_b), 3)
                a_state = self.live_book_state.get(sm.token_a, {"bid": sm.best_bid_a, "ask": sm.best_ask_a})
                self.engine.place_limit_order(
                    condition_id=sm.condition_id,
                    token_id=sm.token_a,
                    question=sm.question,
                    outcome_label=sm.outcome_a,
                    strategy_tag=sm.strategy_tag,
                    side="BUY",
                    price=target_a,
                    usdc_amount=round(fill.size_shares * target_a, 2),
                    post_only=True,
                    best_bid=a_state["bid"],
                    best_ask=a_state["ask"],
                    is_hedge_leg=True,
                )

        # Rotación rápida de Spread para S3 (calculate10), S6 (Bigggggggg) y S10 (01258787xy...)
        elif fill.side == "BUY" and sm.strategy_tag in ("S3_POSTONLY_4LEG_MM", "S6_LONGSHOT_SELL_MAKER", "S10_TENNIS_PENNY_DUST"):
            profit_ticks = 0.05 if sm.strategy_tag == "S10_TENNIS_PENNY_DUST" else max(0.02, sm.spread_a)
            exit_ask = round(min(0.99, fill.price + profit_ticks), 3)
            t_state = self.live_book_state.get(fill.token_id, {"bid": fill.price, "ask": exit_ask})
            self.engine.place_limit_order(
                condition_id=sm.condition_id,
                token_id=fill.token_id,
                question=sm.question,
                outcome_label=fill.outcome_label,
                strategy_tag=sm.strategy_tag,
                side="SELL",
                price=exit_ask,
                usdc_amount=round(fill.size_shares * exit_ask, 2),
                post_only=True,
                best_bid=t_state["bid"],
                best_ask=t_state["ask"],
                is_hedge_leg=True,
            )
