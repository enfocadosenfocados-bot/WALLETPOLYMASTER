import os

def _load_dotenv_fallback():
    """Carga variables de .env sin depender obligatoriamente de python-dotenv."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_dotenv_fallback()

class BotConfig:
    # Endpoints Oficiales Gratuitos de Polymarket
    CLOB_HOST: str = "https://clob.polymarket.com"
    GAMMA_EVENTS_URL: str = "https://gamma-api.polymarket.com/events"
    WS_MARKET_URL: str = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
    CHAIN_ID: int = 137  # Polygon Mainnet

    # Contratos Oficiales en Polygon para Auto-Merge, Auto-Split y Auto-Conversion (Liberación Instantánea de Margen)
    USDC_E_ADDRESS: str = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    CTF_ADDRESS: str = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
    NEG_RISK_ADAPTER_ADDRESS: str = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"

    # Modo de Ejecución (False = Paper Trading en vivo sobre WebSocket real; True = Dinero real)
    LIVE_TRADING: bool = os.getenv("LIVE_TRADING", "false").lower() == "true"

    # Modo de Asignación de Capital:
    # - "LOW_RISK_4_NETHERLANDS": Portafolio Maestro de Bajo Riesgo ($1,000 USDC) en las 4 estrategias
    #                             institucionales más seguras: S5 (e46m3), S8 (chongchong37/tin54321),
    #                             S4 (SunlineTicker), S3 (calculate10) con fricción realista total (FIFO, gas, slippage, rebates).
    # - "LIVE_6_CHAMPIONS_1K"   : Portafolio Maestro de $1,000 USDC concentrado en las 6 Estrategias Ganadoras de Arbitraje.
    # - "TOURNAMENT_10K_EQUAL"  : Modo Torneo ($10,000 USDC totales = $1,000 USDC aislados por cada una de las 10 estrategias).
    # - "SMART_10_ROTATION"     : Modo Real $1,000 USDC repartidos dinámicamente entre las estrategias activas.
    PORTFOLIO_MODE: str = os.getenv("PORTFOLIO_MODE", "LOW_RISK_4_NETHERLANDS")

    # Credenciales Wallet & CLOB
    PRIVATE_KEY: str = os.getenv("PRIVATE_KEY", "")
    SIGNATURE_TYPE: int = int(os.getenv("SIGNATURE_TYPE", "0"))
    FUNDER_ADDRESS: str = os.getenv("FUNDER_ADDRESS", "")
    POLY_API_KEY: str = os.getenv("POLY_API_KEY", "")
    POLY_API_SECRET: str = os.getenv("POLY_API_SECRET", "")
    POLY_API_PASSPHRASE: str = os.getenv("POLY_API_PASSPHRASE", "")
    POLYGON_RPC_URL: str = os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com")
    ODDS_API_KEY: str = os.getenv("ODDS_API_KEY", "")

    # =========================================================================
    # MOTOR DE GESTIÓN DE MARGEN ($1,000 REAL / 4 BAJO RIESGO O 6 CAMPEONAS)
    # =========================================================================
    _IS_TOURNAMENT: bool = (PORTFOLIO_MODE == "TOURNAMENT_10K_EQUAL")
    _IS_CHAMPIONS_6: bool = (PORTFOLIO_MODE == "LIVE_6_CHAMPIONS_1K")
    _IS_LOW_RISK_4: bool = (PORTFOLIO_MODE == "LOW_RISK_4_NETHERLANDS")

    TOTAL_BANKROLL_USDC: float = (
        10000.0 if _IS_TOURNAMENT else float(os.getenv("TOTAL_BANKROLL_USDC", "1000.0"))
    )
    # Reserva intocable ($120 USDC = 12%) exclusiva para cerrar Segundas Patas (Dutch-Book / Hedge / Conversion)
    HEDGE_RESERVE_USDC: float = (
        1200.0 if _IS_TOURNAMENT else float(os.getenv("HEDGE_RESERVE_USDC", "120.0"))
    )
    # Exposición máxima sumando órdenes abiertas + inventario ejecutado ($8,800 en Torneo / $880 en Real)
    MAX_TOTAL_EXPOSURE_USDC: float = TOTAL_BANKROLL_USDC - HEDGE_RESERVE_USDC
    MAX_EXPOSURE_PER_MARKET_USDC: float = float(os.getenv("MAX_EXPOSURE_PER_MARKET_USDC", "60.0"))

    # Cupo aislado por estrategia en Modo Torneo ($1,000 totales = $880 apertura + $120 reserva Hedge propia)
    TOURNAMENT_STRATEGY_TOTAL_USDC: float = 1000.0
    TOURNAMENT_STRATEGY_ENTRY_CAP_USDC: float = 880.0
    TOURNAMENT_STRATEGY_HEDGE_RESERVE_USDC: float = 120.0

    # Tamaño base de orden adaptado a una cuenta de $1,000 USDC
    ORDER_SIZE_USDC: float = float(os.getenv("ORDER_SIZE_USDC", "14.0"))
    _BANKROLL_SCALE: float = 1.0 if _IS_TOURNAMENT else max(0.1, TOTAL_BANKROLL_USDC / 1000.0)

    # Tamaño por orden calibrado:
    # - En LOW_RISK_4_NETHERLANDS: S5=$12 | S8=$15 | S3=$14 | S4=$12 (Las otras 6 apagadas a 0.0)
    STRATEGY_ORDER_SIZE_USDC = (
        {
            "S5_NEGRISK_CONV_MERGE": round(12.0 * _BANKROLL_SCALE, 2),     # e46m3 ticket mediano
            "S8_NICHE_PROPS_CORNERS": round(15.0 * _BANKROLL_SCALE, 2),    # chongchong37 / tin54321
            "S3_POSTONLY_4LEG_MM": round(14.0 * _BANKROLL_SCALE, 2),       # calculate10
            "S4_NEGRISK_ARB": round(12.0 * _BANKROLL_SCALE, 2),            # SunlineTicker
            "S1_VIGFREE_MAKER": 0.0,
            "S2_LIVE_DUTCHBOOK": 0.0,
            "S6_LONGSHOT_SELL_MAKER": 0.0,
            "S7_SPREAD_MIDDLING": 0.0,
            "S9_NCAAF_NFL_DEEP_ARB": 0.0,
            "S10_TENNIS_PENNY_DUST": 0.0,
        }
        if _IS_LOW_RISK_4
        else (
            {
                "S1_VIGFREE_MAKER": round(15.0 * _BANKROLL_SCALE, 2),          # #2 Base ($200 cupo)
                "S2_LIVE_DUTCHBOOK": round(12.0 * _BANKROLL_SCALE, 2),         # #4 Turbo ($140 cupo)
                "S3_POSTONLY_4LEG_MM": 0.0,
                "S4_NEGRISK_ARB": 0.0,
                "S5_NEGRISK_CONV_MERGE": 0.0,
                "S6_LONGSHOT_SELL_MAKER": 0.0,
                "S7_SPREAD_MIDDLING": round(14.0 * _BANKROLL_SCALE, 2),        # #3 Base ($180 cupo)
                "S8_NICHE_PROPS_CORNERS": round(15.0 * _BANKROLL_SCALE, 2),    # #1 Base ($220 cupo)
                "S9_NCAAF_NFL_DEEP_ARB": round(12.0 * _BANKROLL_SCALE, 2),     # #5 Turbo ($110 cupo)
                "S10_TENNIS_PENNY_DUST": round(max(2.5, 2.5 * _BANKROLL_SCALE), 2),  # #6 Micro ($30 cupo)
            }
            if _IS_CHAMPIONS_6
            else {
                "S1_VIGFREE_MAKER": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),
                "S2_LIVE_DUTCHBOOK": round(20.0 if _IS_TOURNAMENT else 14.0 * _BANKROLL_SCALE, 2),
                "S3_POSTONLY_4LEG_MM": round(22.0 if _IS_TOURNAMENT else 15.0 * _BANKROLL_SCALE, 2),
                "S4_NEGRISK_ARB": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),
                "S5_NEGRISK_CONV_MERGE": round(18.0 if _IS_TOURNAMENT else 11.0 * _BANKROLL_SCALE, 2),
                "S6_LONGSHOT_SELL_MAKER": round(16.0 if _IS_TOURNAMENT else 10.0 * _BANKROLL_SCALE, 2),
                "S7_SPREAD_MIDDLING": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),
                "S8_NICHE_PROPS_CORNERS": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),
                "S9_NCAAF_NFL_DEEP_ARB": round(20.0 if _IS_TOURNAMENT else 14.0 * _BANKROLL_SCALE, 2),
                "S10_TENNIS_PENNY_DUST": round(5.0 if _IS_TOURNAMENT else max(2.5, 2.5 * _BANKROLL_SCALE), 2),
            }
        )
    )

    # Cuota máxima de margen de apertura:
    # - En LOW_RISK_4_NETHERLANDS: S5=$280 | S8=$240 | S3=$200 | S4=$160 = $880 USDC (+ $120 Reserva = $1,000 USDC)
    STRATEGY_MAX_BUDGET_USDC = (
        {
            "S5_NEGRISK_CONV_MERGE": round(280.0 * _BANKROLL_SCALE, 2),
            "S8_NICHE_PROPS_CORNERS": round(240.0 * _BANKROLL_SCALE, 2),
            "S3_POSTONLY_4LEG_MM": round(200.0 * _BANKROLL_SCALE, 2),
            "S4_NEGRISK_ARB": round(160.0 * _BANKROLL_SCALE, 2),
            "S1_VIGFREE_MAKER": 0.0,
            "S2_LIVE_DUTCHBOOK": 0.0,
            "S6_LONGSHOT_SELL_MAKER": 0.0,
            "S7_SPREAD_MIDDLING": 0.0,
            "S9_NCAAF_NFL_DEEP_ARB": 0.0,
            "S10_TENNIS_PENNY_DUST": 0.0,
        }
        if _IS_LOW_RISK_4
        else (
            {
                "S8_NICHE_PROPS_CORNERS": round(220.0 * _BANKROLL_SCALE, 2),
                "S1_VIGFREE_MAKER": round(200.0 * _BANKROLL_SCALE, 2),
                "S7_SPREAD_MIDDLING": round(180.0 * _BANKROLL_SCALE, 2),
                "S2_LIVE_DUTCHBOOK": round(140.0 * _BANKROLL_SCALE, 2),
                "S9_NCAAF_NFL_DEEP_ARB": round(110.0 * _BANKROLL_SCALE, 2),
                "S10_TENNIS_PENNY_DUST": round(30.0 * _BANKROLL_SCALE, 2),
                "S3_POSTONLY_4LEG_MM": 0.0,
                "S4_NEGRISK_ARB": 0.0,
                "S5_NEGRISK_CONV_MERGE": 0.0,
                "S6_LONGSHOT_SELL_MAKER": 0.0,
            }
            if _IS_CHAMPIONS_6
            else (
                {
                    "S1_VIGFREE_MAKER": 880.0,
                    "S2_LIVE_DUTCHBOOK": 880.0,
                    "S3_POSTONLY_4LEG_MM": 880.0,
                    "S4_NEGRISK_ARB": 880.0,
                    "S5_NEGRISK_CONV_MERGE": 880.0,
                    "S6_LONGSHOT_SELL_MAKER": 880.0,
                    "S7_SPREAD_MIDDLING": 880.0,
                    "S8_NICHE_PROPS_CORNERS": 880.0,
                    "S9_NCAAF_NFL_DEEP_ARB": 880.0,
                    "S10_TENNIS_PENNY_DUST": 880.0,
                }
                if _IS_TOURNAMENT
                else {
                    "S1_VIGFREE_MAKER": round(90.0 * _BANKROLL_SCALE, 2),
                    "S2_LIVE_DUTCHBOOK": round(100.0 * _BANKROLL_SCALE, 2),
                    "S3_POSTONLY_4LEG_MM": round(120.0 * _BANKROLL_SCALE, 2),
                    "S4_NEGRISK_ARB": round(80.0 * _BANKROLL_SCALE, 2),
                    "S5_NEGRISK_CONV_MERGE": round(130.0 * _BANKROLL_SCALE, 2),
                    "S6_LONGSHOT_SELL_MAKER": round(80.0 * _BANKROLL_SCALE, 2),
                    "S7_SPREAD_MIDDLING": round(90.0 * _BANKROLL_SCALE, 2),
                    "S8_NICHE_PROPS_CORNERS": round(90.0 * _BANKROLL_SCALE, 2),
                    "S9_NCAAF_NFL_DEEP_ARB": round(80.0 * _BANKROLL_SCALE, 2),
                    "S10_TENNIS_PENNY_DUST": round(20.0 * _BANKROLL_SCALE, 2),
                }
            )
        )
    )

    # =========================================================================
    # CIRCUIT BREAKER / HARD STOP-LOSS GLOBAL A NIVEL PORTAFOLIO
    CIRCUIT_BREAKER_ENABLED: bool = os.getenv("CIRCUIT_BREAKER_ENABLED", "true").lower() == "true"
    GLOBAL_STOP_LOSS_USDC: float = float(os.getenv("GLOBAL_STOP_LOSS_USDC", "45.0"))  # Stop loss global (si la pérdida acumulada supera este monto en USDC, detiene el bot y cancela todo)

    # MOTOR DE FRICCIÓN REALISTA DE PRODUCCIÓN (COLAS FIFO, SLIPPAGE, SPREAD Y GAS)
    # =========================================================================
    REALISTIC_FRICTION_ENABLED: bool = os.getenv("REALISTIC_FRICTION_ENABLED", "true").lower() == "true"
    # Tasa realista de Maker Rebate efectivo (0.045% = 4.5 bps promedio ponderado en deportes)
    REALISTIC_MAKER_REBATE_RATE: float = float(os.getenv("REALISTIC_MAKER_REBATE_RATE", "0.00045"))
    # Costo real de Gas en Polygon (POL) por cada fusión on-chain mergePositions (~$0.012 USD)
    POLYGON_MERGE_GAS_USDC: float = float(os.getenv("POLYGON_MERGE_GAS_USDC", "0.012"))
    # Probabilidad de llenado en cola FIFO cuando el precio apenas toca nuestro límite exacto (sin atravesarlo):
    QUEUE_TOUCH_FILL_PROB = {
        "S5_NEGRISK_CONV_MERGE": 0.85,  # NegRisk colas largas y bonos piso e46m3 -> alta prioridad de llenado
        "S8_NICHE_PROPS_CORNERS": 0.78,  # Libros de nicho / totales defensivos chongchong37 sin HFT -> alta prioridad de cola
        "S4_NEGRISK_ARB": 0.72,          # Techos multi-activo BTC/Fed SunlineTicker -> prioridad media-alta
        "S3_POSTONLY_4LEG_MM": 0.65,     # Spread tight post-only calculate10 -> prioridad moderada
        "S1_VIGFREE_MAKER": 0.75,        # Pre-partido con horas de anticipación -> alta prioridad
        "S7_SPREAD_MIDDLING": 0.70,      # Líneas alternativas de spread -> prioridad media-alta
        "S2_LIVE_DUTCHBOOK": 0.62,       # Partidos en vivo -> competencia moderada en el libro
        "S9_NCAAF_NFL_DEEP_ARB": 0.60,   # Fútbol americano en vivo -> competencia moderada
        "S10_TENNIS_PENNY_DUST": 0.35,   # Redes a $0.008 -> cola FIFO competida
    }
    # Protección de "Pata Coja" (Legging Stop-Loss / Scratch Exit):
    # Si tenemos 1 sola pata abierta sin emparejar por más de LEGGING_MAX_UNHEDGED_SEC y el Bid cae más de
    # LEGGING_STOP_LOSS_DROP_CENTS (o expira el tiempo máximo), cerramos cruzando el Bid (asumiendo Spread + Slippage Taker)
    LEGGING_MAX_UNHEDGED_SEC: int = int(os.getenv("LEGGING_MAX_UNHEDGED_SEC", "1800"))      # 30 min máx sin cubrir en vivo
    LEGGING_PREMATCH_UNHEDGED_SEC: int = int(os.getenv("LEGGING_PREMATCH_UNHEDGED_SEC", "5400"))  # 90 min en pre-partido
    LEGGING_STOP_LOSS_DROP_CENTS: float = float(os.getenv("LEGGING_STOP_LOSS_DROP_CENTS", "0.14"))  # Stop-loss si cae 14c sin cubrir
    TAKER_EMERGENCY_SLIPPAGE_BPS: float = float(os.getenv("TAKER_EMERGENCY_SLIPPAGE_BPS", "0.005")) # 50 bps slippage + fee al cruzar

    # =========================================================================
    # PARÁMETROS CUANTITATIVOS DE LAS ESTRATEGIAS (ACTIVACIÓN POR MODO)
    # =========================================================================

    # S1: Pre-Match Vig-Free Spreads & Totals (hi774c / HomeRunHazard)
    S1_ENABLED: bool = os.getenv("S1_ENABLED", "false" if (_IS_CHAMPIONS_6 or _IS_LOW_RISK_4) else "true").lower() == "true"
    S1_MIN_VOL_24H: float = 500.0
    S1_BID_MIN: float = 0.440
    S1_BID_MAX: float = 0.495
    S1_ASK_MIN: float = 0.495
    S1_ASK_MAX: float = 0.560
    S1_MAX_COMBINED_COST: float = 0.990

    # S2: In-Play Gamma Scalping / Dutch-Book (PEYZ-BIGGEST-FAN / RN1)
    S2_ENABLED: bool = os.getenv("S2_ENABLED", "false" if _IS_LOW_RISK_4 else "true").lower() == "true"
    S2_MIN_VOL_24H: float = 4000.0
    S2_PRICE_MIN: float = 0.18
    S2_PRICE_MAX: float = 0.82
    S2_TARGET_DUTCH_BOOK_SUM: float = 0.945

    # S3: 4-Leg Post-Only HFT Spread Harvester (calculate10)
    S3_ENABLED: bool = os.getenv("S3_ENABLED", "true" if _IS_LOW_RISK_4 else ("false" if _IS_CHAMPIONS_6 else "true")).lower() == "true"
    S3_MIN_VOL_24H: float = 10000.0
    S3_MIN_SPREAD: float = 0.020
    S3_MAX_SPREAD: float = 0.090
    S3_IMBALANCE_CANCEL_RATIO: float = 0.78

    # S4: Anti-Hype & Matriz Negative-Risk / Techos (SunlineTicker / BreakTheBank)
    S4_ENABLED: bool = os.getenv("S4_ENABLED", "true" if _IS_LOW_RISK_4 else ("false" if _IS_CHAMPIONS_6 else "true")).lower() == "true"
    S4_MIN_VOL_24H: float = 5000.0
    S4_NEGRISK_MAX_BID_SUM: float = 0.985

    # S5: Motor NegRisk CONVERSION + MERGE + Bonos Piso (e46m3 - 98.2% Win Intervals)
    S5_ENABLED: bool = os.getenv("S5_ENABLED", "true" if _IS_LOW_RISK_4 else ("false" if _IS_CHAMPIONS_6 else "true")).lower() == "true"
    S5_MIN_VOL_24H: float = 1500.0
    S5_TAIL_NO_MAX_ASK: float = 0.065     # Compra acciones 'No' / Cola baratas para CONVERSION + MERGE
    S5_FLOOR_BOND_MIN_BID: float = 0.955  # Bonos de piso de alta probabilidad (ej. BTC daily floor / Clima)
    S5_FLOOR_BOND_MAX_ASK: float = 0.991

    # S6: Cosechador Maker en Venta de Longshots vía SPLIT/CONVERSION
    S6_ENABLED: bool = os.getenv("S6_ENABLED", "false" if (_IS_CHAMPIONS_6 or _IS_LOW_RISK_4) else "true").lower() == "true"
    S6_MIN_VOL_24H: float = 2000.0
    S6_LONGSHOT_MIN_PRICE: float = 0.040
    S6_LONGSHOT_MAX_PRICE: float = 0.260

    # S7: Escalera de Hándicaps Alternativos / Spread Middling
    S7_ENABLED: bool = os.getenv("S7_ENABLED", "false" if _IS_LOW_RISK_4 else "true").lower() == "true"
    S7_MIN_VOL_24H: float = 300.0
    S7_TARGET_MIDDLE_SUM: float = 0.915

    # S8: Props de Nicho y Totales Defensivos O/U (chongchong37 / tin54321 / omnibus-076daa)
    S8_ENABLED: bool = os.getenv("S8_ENABLED", "true").lower() == "true"
    S8_MIN_VOL_24H: float = 150.0
    S8_TARGET_COMBINED_COST: float = 0.965

    # S9: Dutch-Book Profundo 0% Fee en Fútbol Americano NCAAF/NFL
    S9_ENABLED: bool = os.getenv("S9_ENABLED", "false" if _IS_LOW_RISK_4 else "true").lower() == "true"
    S9_MIN_VOL_24H: float = 1000.0
    S9_DEEP_ARB_SUM_TARGET: float = 0.860

    # S10: Redes de Arrastre en Tenis
    S10_ENABLED: bool = os.getenv("S10_ENABLED", "false" if _IS_LOW_RISK_4 else "true").lower() == "true"
    S10_MIN_VOL_24H: float = 50.0
    S10_STINK_BID_PRICE: float = 0.008     # Red de arrastre ultra-barata para atrapar ventas de pánico en Tenis
    S11_ENABLED: bool = False
    S12_ENABLED: bool = False
    S13_ENABLED: bool = False
    S14_ENABLED: bool = False
    S15_ENABLED: bool = False
    S16_ENABLED: bool = False

    # =========================================================================
    # PARÁMETROS DE OPERACIÓN 24/7 MULTI-DÍA (AUTO-ROTACIÓN Y RECICLAJE)
    # =========================================================================
    # Intervalo de re-escaneo autónomo de Gamma API para incorporar nuevos partidos y purgar cerrados (segundos)
    MARKET_SCAN_INTERVAL_SEC: int = int(os.getenv("MARKET_SCAN_INTERVAL_SEC", "180"))
    # En Modo 6 Campeonas permitimos hasta 4 mercados simultáneos por estrategia (21-24 mercados activos)
    MAX_MARKETS_PER_STRATEGY: int = int(
        os.getenv("MAX_MARKETS_PER_STRATEGY", "6" if _IS_TOURNAMENT else "4")
    )
    # Tiempo máximo (segundos) que una orden de apertura sin llenarse puede estar lejos del precio antes de recotizar
    STALE_ENTRY_ORDER_TIMEOUT_SEC: int = int(os.getenv("STALE_ENTRY_ORDER_TIMEOUT_SEC", "900"))
    # Desviación de precio (centavos) para recotizar una orden de entrada que quedó obsoleta
    REQUOTE_PRICE_DRIFT_THRESHOLD: float = float(os.getenv("REQUOTE_PRICE_DRIFT_THRESHOLD", "0.06"))

