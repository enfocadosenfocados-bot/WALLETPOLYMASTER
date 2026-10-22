"""
Motor Autónomo de Descubrimiento, Clasificación y Selección de Mercados (Sin Copiar Wallets)
Escanea Gamma API y asigna cada mercado activo a las 10 estrategias cuantitativas (Lote 1 + Lote 2).
"""
import urllib.request
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from config import BotConfig

@dataclass
class SelectedMarket:
    condition_id: str
    question: str
    slug: str
    strategy_tag: str
    token_a: str
    token_b: str
    outcome_a: str
    outcome_b: str
    best_bid_a: float
    best_ask_a: float
    best_bid_b: float
    best_ask_b: float
    spread_a: float
    vol_24h: float
    tick_size: float
    min_order_size: float
    is_live: bool
    neg_risk: bool
    score_metric: float
    metadata: Dict = field(default_factory=dict)

class AutonomousMarketScanner:
    def __init__(self, config: BotConfig):
        self.cfg = config
        self.headers = {"User-Agent": "Mozilla/5.0"}

    def fetch_active_events(self, limit: int = 150) -> List[Dict]:
        url = (
            f"{self.cfg.GAMMA_EVENTS_URL}?active=true&closed=false"
            f"&limit={limit}&order=volume24hr&ascending=false"
        )
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                if attempt == 2:
                    print(f"⚠️ [GAMMA API WARNING] Fallo temporal al consultar eventos ({e}). Se reintentará en el próximo ciclo.")
                    return []
        return []

    def scan_and_select_all(self, max_per_strategy: int = 3) -> Dict[str, List[SelectedMarket]]:
        events = self.fetch_active_events(150)
        buckets: Dict[str, List[SelectedMarket]] = {
            "S1_VIGFREE_MAKER": [],
            "S2_LIVE_DUTCHBOOK": [],
            "S3_POSTONLY_4LEG_MM": [],
            "S4_NEGRISK_ARB": [],
            "S5_NEGRISK_CONV_MERGE": [],
            "S6_LONGSHOT_SELL_MAKER": [],
            "S7_SPREAD_MIDDLING": [],
            "S8_NICHE_PROPS_CORNERS": [],
            "S9_NCAAF_NFL_DEEP_ARB": [],
            "S10_TENNIS_PENNY_DUST": [],
        }

        # Si el usuario activa el modo concentrado ("CORE_CONCENTRATED"), priorizamos las 5 de menor DD y mayor rotación
        core_only = (self.cfg.PORTFOLIO_MODE == "CORE_CONCENTRATED")

        for ev in events:
            if ev.get("ended"):
                continue
            is_live = bool(ev.get("live"))
            ev_title = ev.get("title", "")
            ev_title_low = ev_title.lower()
            ev_vol = float(ev.get("volume24hr") or 0)
            is_neg_risk = bool(ev.get("negRisk"))
            mkts = ev.get("markets") or []
            active_mkts = [
                m for m in mkts
                if m.get("active") and not m.get("closed") and m.get("acceptingOrders")
            ]
            if not active_mkts:
                continue

            # =========================================================================
            # ESTRATEGIAS DE EVENTOS MULTI-RESULTADO (S4, S5, S6, S7)
            # =========================================================================
            if is_neg_risk and len(active_mkts) >= 3:
                bids_sum = sum(float(m.get("bestBid") or 0) for m in active_mkts)
                asks_sum = sum(float(m.get("bestAsk") or 0) for m in active_mkts)

                # --- S4: Matriz Negative-Risk Anti-Favorito (BreakTheBank / Nooserac) ---
                if not core_only and self.cfg.S4_ENABLED and 0.50 < bids_sum <= self.cfg.S4_NEGRISK_MAX_BID_SUM and ev_vol >= self.cfg.S4_MIN_VOL_24H:
                    top_m = max(active_mkts, key=lambda x: float(x.get("bestBid") or 0))
                    sm = self._build_selected_market(
                        top_m,
                        strategy_tag="S4_NEGRISK_ARB",
                        is_live=is_live,
                        score_metric=round((1.0 - bids_sum) * 100, 2),
                        extra_meta={"event": ev_title[:28], "legs": len(active_mkts), "sum_bids": round(bids_sum, 3)}
                    )
                    if sm:
                        buckets["S4_NEGRISK_ARB"].append(sm)

                # --- S5 (NUEVA - e46m3): Motor NegRisk CONVERSION + MERGE (98.2% Win Rate) ---
                # Busca patas con precios extremos (colas baratas o bonos piso >=0.955) dentro de un evento NegRisk
                # donde la suma de precios permite CONVERSION + MERGE instantáneo a $1.00 USDC
                if self.cfg.S5_ENABLED and ev_vol >= self.cfg.S5_MIN_VOL_24H:
                    # En un evento NegRisk de N resultados, la suma teórica de Yes es 1.00.
                    # Si la suma de los Bids es menor a 0.992, comprar acciones 'No' / convertir genera arbitraje MERGE.
                    tail_candidates = [
                        m for m in active_mkts
                        if 0.005 <= float(m.get("bestBid") or 0) <= self.cfg.S5_TAIL_NO_MAX_ASK
                        and float(m.get("bestAsk") or 1.0) <= self.cfg.S5_TAIL_NO_MAX_ASK + 0.02
                    ]
                    if tail_candidates and bids_sum <= 1.01:
                        best_tail = max(tail_candidates, key=lambda x: float(x.get("volume24hr") or 0))
                        conv_edge_bps = round(max(0.005, 1.0 - bids_sum) * 10000, 1)
                        sm = self._build_selected_market(
                            best_tail,
                            strategy_tag="S5_NEGRISK_CONV_MERGE",
                            is_live=is_live,
                            score_metric=ev_vol * (1.0 + conv_edge_bps / 100.0),
                            extra_meta={
                                "mode": "NEGRISK_CONVERSION_MERGE",
                                "legs": len(active_mkts),
                                "sum_yes_bids": round(bids_sum, 3),
                                "est_edge_bps": conv_edge_bps,
                            }
                        )
                        if sm:
                            buckets["S5_NEGRISK_CONV_MERGE"].append(sm)

                # --- S6 (NUEVA - Bigggggggg): Cosechador Maker en Venta de Longshots (SPLIT/CONV + SELL) ---
                # Busca opciones "lotería" ($0.04 a $0.26) en menciones, tweets, política, tasas o torneos
                if not core_only and self.cfg.S6_ENABLED and ev_vol >= self.cfg.S6_MIN_VOL_24H:
                    longshot_mkts = [
                        m for m in active_mkts
                        if self.cfg.S6_LONGSHOT_MIN_PRICE <= float(m.get("bestBid") or 0) <= self.cfg.S6_LONGSHOT_MAX_PRICE
                        and (float(m.get("bestAsk") or 0) - float(m.get("bestBid") or 0)) >= 0.01
                    ]
                    if longshot_mkts:
                        target_ls = max(longshot_mkts, key=lambda x: float(x.get("volume24hr") or 0))
                        ask_px = float(target_ls.get("bestAsk") or 0.17)
                        sm = self._build_selected_market(
                            target_ls,
                            strategy_tag="S6_LONGSHOT_SELL_MAKER",
                            is_live=is_live,
                            score_metric=float(target_ls.get("volume24hr") or 1000.0) * ask_px,
                            extra_meta={
                                "mode": "SPLIT_CONV_THEN_SELL_MAKER",
                                "sell_target_px": round(ask_px, 3),
                                "no_implied_px": round(1.0 - ask_px, 3),
                            }
                        )
                        if sm:
                            buckets["S6_LONGSHOT_SELL_MAKER"].append(sm)

            # --- S7 (NUEVA - justaluckydude): Escalera de Hándicaps Alternativos ("Spread Middling") ---
            # Busca eventos deportivos que tengan múltiples líneas de Spread o Totales para armar un "Middle"
            spread_mkts = [
                m for m in active_mkts
                if ("spread:" in (m.get("question") or "").lower() or (m.get("sportsMarketType") or "").lower() == "spreads")
                and float(m.get("bestBid") or 0) > 0.15
                and float(m.get("bestAsk") or 1.0) < 0.85
            ]
            if not core_only and self.cfg.S7_ENABLED and len(spread_mkts) >= 2:
                spread_mkts.sort(key=lambda x: float(x.get("volume24hr") or 0), reverse=True)
                m_primary = spread_mkts[0]
                m_alt = spread_mkts[1]
                bid1 = float(m_primary.get("bestBid") or 0.45)
                bid2_opp = round(1.0 - float(m_alt.get("bestAsk") or 0.55), 3)
                middle_sum = round(min(0.92, bid1 + bid2_opp - 0.04), 3)
                sm = self._build_selected_market(
                    m_primary,
                    strategy_tag="S7_SPREAD_MIDDLING",
                    is_live=is_live,
                    score_metric=ev_vol + 5000.0,
                    extra_meta={
                        "alt_spread_q": (m_alt.get("question") or "")[:30],
                        "target_middle_sum": middle_sum,
                        "double_payout_window": "YES ($2.00 max)",
                    }
                )
                if sm:
                    buckets["S7_SPREAD_MIDDLING"].append(sm)

            # =========================================================================
            # ESCANEO INDIVIDUAL POR MERCADO (S1, S2, S3, S5-Floor, S8, S9, S10)
            # =========================================================================
            for m in active_mkts:
                q = m.get("question", "")
                q_low = q.lower()
                smt = (m.get("sportsMarketType") or "").lower()
                vol24 = float(m.get("volume24hr") or 0)
                bid_a = float(m.get("bestBid") or 0)
                ask_a = float(m.get("bestAsk") or 0)
                if bid_a <= 0 or ask_a <= 0 or ask_a <= bid_a or ask_a >= 1.0:
                    continue

                spread_a = round(ask_a - bid_a, 4)
                mid_a = (bid_a + ask_a) / 2.0
                bid_b = round(1.0 - ask_a, 4)
                ask_b = round(1.0 - bid_a, 4)
                combined_maker_cost = round(bid_a + bid_b, 4)

                # --- S5 Complemento (e46m3 Floor Bonds): Bonos de piso de alta probabilidad ($0.955 - $0.990) ---
                if (
                    self.cfg.S5_ENABLED
                    and (self.cfg.S5_FLOOR_BOND_MIN_BID <= bid_a <= self.cfg.S5_FLOOR_BOND_MAX_ASK or self.cfg.S5_FLOOR_BOND_MIN_BID <= bid_b <= self.cfg.S5_FLOOR_BOND_MAX_ASK)
                    and vol24 >= self.cfg.S5_MIN_VOL_24H
                    and len(buckets["S5_NEGRISK_CONV_MERGE"]) < max_per_strategy * 2
                ):
                    bond_px = bid_a if bid_a >= self.cfg.S5_FLOOR_BOND_MIN_BID else bid_b
                    yield_bps = round((1.0 - bond_px) * 10000, 1)
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S5_NEGRISK_CONV_MERGE",
                        is_live=is_live,
                        score_metric=vol24 * (yield_bps / 100.0),
                        extra_meta={"mode": "HIGH_PROB_FLOOR_BOND", "bond_entry": bond_px, "yield_bps": yield_bps}
                    )
                    if sm:
                        buckets["S5_NEGRISK_CONV_MERGE"].append(sm)

                # --- S8 (NUEVA - omnibus-076daa): Props de Nicho, Total de Córners y Hándicaps de Mapas ---
                is_niche_prop = (
                    "corner" in q_low
                    or "map handicap" in q_low
                    or "map 1" in q_low
                    or "map 2" in q_low
                    or "both teams to score" in q_low
                    or "draw" in q_low
                    or ("o/u" in q_low and ("2.5" in q_low or "1.5" in q_low or "3.5" in q_low or "8.5" in q_low or "9.5" in q_low or "10.5" in q_low))
                )
                if (
                    self.cfg.S8_ENABLED
                    and is_niche_prop
                    and 0.20 <= mid_a <= 0.80
                    and vol24 >= self.cfg.S8_MIN_VOL_24H
                ):
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S8_NICHE_PROPS_CORNERS",
                        is_live=is_live,
                        score_metric=vol24 * (1.0 + spread_a * 10.0),
                        extra_meta={"prop_type": "CORNERS_MAPS_NICHE", "target_sum": self.cfg.S8_TARGET_COMBINED_COST, "spread": spread_a}
                    )
                    if sm:
                        buckets["S8_NICHE_PROPS_CORNERS"].append(sm)

                # --- S9 (NUEVA - primm): Dutch-Book Profundo 0% Fee en Fútbol Americano (NCAAF/NFL) y US Sports ---
                is_us_football_or_major = any(
                    kw in q_low or kw in ev_title_low
                    for kw in [
                        "nfl", "ncaaf", "college football", "state", "bulldogs", "tigers", "eagles",
                        "ravens", "chiefs", "bills", "cowboys", "49ers", "packers", "lions", "texans",
                        "vs.", "spread:"
                    ]
                )
                if (
                    not core_only
                    and self.cfg.S9_ENABLED
                    and is_us_football_or_major
                    and 0.22 <= mid_a <= 0.78
                    and vol24 >= self.cfg.S9_MIN_VOL_24H
                ):
                    deep_target_b = round(self.cfg.S9_DEEP_ARB_SUM_TARGET - min(bid_a, 0.50), 3)
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S9_NCAAF_NFL_DEEP_ARB",
                        is_live=is_live,
                        score_metric=vol24,
                        extra_meta={"target_sum_vwap": self.cfg.S9_DEEP_ARB_SUM_TARGET, "deep_leg_b": deep_target_b, "fee": "$0.00 Maker"}
                    )
                    if sm:
                        buckets["S9_NCAAF_NFL_DEEP_ARB"].append(sm)

                # --- S10 (NUEVA - 01258787xy...): Redes de Arrastre ($0.002-$0.015) y Dual-Outcome en Tenis ---
                is_tennis_or_qual = any(
                    kw in q_low or kw in ev_title_low
                    for kw in ["open", "atp", "wta", "itf", "challenger", "qualification", "tennis", "set "]
                )
                if (
                    self.cfg.S10_ENABLED
                    and is_tennis_or_qual
                    and vol24 >= self.cfg.S10_MIN_VOL_24H
                ):
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S10_TENNIS_PENNY_DUST",
                        is_live=is_live,
                        score_metric=vol24 + 1000.0,
                        extra_meta={
                            "stink_bid_px": self.cfg.S10_STINK_BID_PRICE,
                            "collateral_locked": f"${self.cfg.STRATEGY_ORDER_SIZE_USDC['S10_TENNIS_PENNY_DUST']:.2f}",
                        }
                    )
                    if sm:
                        buckets["S10_TENNIS_PENNY_DUST"].append(sm)

                # --- S1: Pre-Match Spreads & Totals 50/50 Vig-Free Maker (hi774c / HomeRunHazard) ---
                is_spread_or_total = (
                    smt in ["spreads", "totals"]
                    or "spread:" in q_low
                    or "o/u" in q_low
                )
                if (
                    self.cfg.S1_ENABLED
                    and not is_live
                    and is_spread_or_total
                    and self.cfg.S1_BID_MIN <= bid_a <= self.cfg.S1_BID_MAX
                    and self.cfg.S1_ASK_MIN <= ask_a <= self.cfg.S1_ASK_MAX
                    and combined_maker_cost <= self.cfg.S1_MAX_COMBINED_COST
                    and vol24 >= self.cfg.S1_MIN_VOL_24H
                ):
                    edge_pct = round((1.0 - combined_maker_cost) * 100, 2)
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S1_VIGFREE_MAKER",
                        is_live=False,
                        score_metric=vol24 * (1.0 + edge_pct),
                        extra_meta={"combined_maker_cost": combined_maker_cost, "locked_arb_pct": edge_pct}
                    )
                    if sm:
                        buckets["S1_VIGFREE_MAKER"].append(sm)

                # --- S2: In-Play Gamma Scalping / Dutch-Book (PEYZ-BIGGEST-FAN / RN1) ---
                if (
                    not core_only
                    and self.cfg.S2_ENABLED
                    and is_live
                    and self.cfg.S2_PRICE_MIN <= mid_a <= self.cfg.S2_PRICE_MAX
                    and vol24 >= self.cfg.S2_MIN_VOL_24H
                ):
                    target_leg_b = round(self.cfg.S2_TARGET_DUTCH_BOOK_SUM - bid_a, 4)
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S2_LIVE_DUTCHBOOK",
                        is_live=True,
                        score_metric=vol24,
                        extra_meta={"score": ev.get("score") or "LIVE", "target_leg_b": target_leg_b}
                    )
                    if sm:
                        buckets["S2_LIVE_DUTCHBOOK"].append(sm)

                # --- S3: 4-Leg Post-Only HFT Spread Harvester (calculate10) ---
                if (
                    self.cfg.S3_ENABLED
                    and not is_tennis_or_qual
                    and self.cfg.S3_MIN_SPREAD <= spread_a <= self.cfg.S3_MAX_SPREAD
                    and 0.15 <= mid_a <= 0.85
                    and vol24 >= self.cfg.S3_MIN_VOL_24H
                ):
                    mm_score = round((spread_a * 100) * (vol24 / 10000.0), 2)
                    sm = self._build_selected_market(
                        m,
                        strategy_tag="S3_POSTONLY_4LEG_MM",
                        is_live=is_live,
                        score_metric=mm_score,
                        extra_meta={"spread_cents": round(spread_a * 100, 2), "rewards_min": float(m.get("rewardsMinSize") or 0)}
                    )
                    if sm:
                        buckets["S3_POSTONLY_4LEG_MM"].append(sm)

        # Deduplicación GLOBAL: cada condition_id solo puede pertenecer a UNA estrategia
        # Priorizamos primero las estrategias de nicho más específicas (S5, S6, S7, S8, S10, S4, S1, S9, S2, S3)
        priority_order = [
            "S5_NEGRISK_CONV_MERGE",
            "S6_LONGSHOT_SELL_MAKER",
            "S7_SPREAD_MIDDLING",
            "S8_NICHE_PROPS_CORNERS",
            "S10_TENNIS_PENNY_DUST",
            "S4_NEGRISK_ARB",
            "S1_VIGFREE_MAKER",
            "S9_NCAAF_NFL_DEEP_ARB",
            "S2_LIVE_DUTCHBOOK",
            "S3_POSTONLY_4LEG_MM",
        ]
        seen_global_cids = set()
        for tag in priority_order:
            buckets[tag].sort(key=lambda x: x.score_metric, reverse=True)
            deduped = []
            for item in buckets[tag]:
                if item.condition_id not in seen_global_cids:
                    seen_global_cids.add(item.condition_id)
                    deduped.append(item)
                if len(deduped) >= max_per_strategy:
                    break
            buckets[tag] = deduped

        return buckets

    def _build_selected_market(
        self, m: Dict, strategy_tag: str, is_live: bool, score_metric: float, extra_meta: Dict
    ) -> Optional[SelectedMarket]:
        try:
            tids = json.loads(m.get("clobTokenIds") or "[]")
            outcomes = json.loads(m.get("outcomes") or '["Yes", "No"]')
            if len(tids) < 2:
                return None
            bid_a = float(m.get("bestBid") or 0)
            ask_a = float(m.get("bestAsk") or 0)
            bid_b = round(1.0 - ask_a, 4)
            ask_b = round(1.0 - bid_a, 4)
            return SelectedMarket(
                condition_id=m.get("conditionId", ""),
                question=m.get("question", ""),
                slug=m.get("slug", ""),
                strategy_tag=strategy_tag,
                token_a=str(tids[0]),
                token_b=str(tids[1]),
                outcome_a=str(outcomes[0]) if len(outcomes) > 0 else "OutcomeA",
                outcome_b=str(outcomes[1]) if len(outcomes) > 1 else "OutcomeB",
                best_bid_a=bid_a,
                best_ask_a=ask_a,
                best_bid_b=bid_b,
                best_ask_b=ask_b,
                spread_a=round(ask_a - bid_a, 4),
                vol_24h=float(m.get("volume24hr") or 0),
                tick_size=float(m.get("orderPriceMinTickSize") or 0.01),
                min_order_size=float(m.get("orderMinSize") or 5.0),
                is_live=is_live,
                neg_risk=bool(m.get("negRisk")),
                score_metric=score_metric,
                metadata=extra_meta,
            )
        except Exception:
            return None
