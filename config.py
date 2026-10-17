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
    # - "TOURNAMENT_10K_EQUAL": Modo Torneo ($10,000 USDC totales = $1,000 USDC aislados por cada una de las 10 estrategias:
    #                           $880 apertura + $120 reserva propia por estrategia, con tamaño de orden realista).
    # - "SMART_10_ROTATION"   : Modo Real $1,000 USDC repartidos dinámicamente entre las estrategias activas.
    # - "CORE_CONCENTRATED"   : Concentra el 100% del capital en las 5 estrategias de menor Drawdown y mayor rotación.
    PORTFOLIO_MODE: str = os.getenv("PORTFOLIO_MODE", "TOURNAMENT_10K_EQUAL")

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
    # MOTOR DE GESTIÓN DE MARGEN ($1,000 REAL O $10,000 EN TORNEO 10x$1,000)
    # =========================================================================
    _IS_TOURNAMENT: bool = (PORTFOLIO_MODE == "TOURNAMENT_10K_EQUAL")

    # Si está en modo TOURNAMENT_10K_EQUAL, el Bankroll total del Torneo es $10,000 USDC ($1,000 por estrategia)
    TOTAL_BANKROLL_USDC: float = (
        10000.0 if _IS_TOURNAMENT else float(os.getenv("TOTAL_BANKROLL_USDC", "1000.0"))
    )
    # Reserva intocable (12%) exclusiva para cerrar Segundas Patas (Dutch-Book / Hedge / Conversion)
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

    # Tamaño base de orden adaptado a una cuenta de $1,000 USDC ($12 USDC por orden normal)
    ORDER_SIZE_USDC: float = float(os.getenv("ORDER_SIZE_USDC", "12.0"))
    # En Modo Torneo mantenemos el tamaño de orden realista de una cuenta de $1,000 USDC (_BANKROLL_SCALE = 1.0)
    # para no distorsionar los fills con órdenes gigantes irreales, permitiendo evaluar más mercados en paralelo.
    _BANKROLL_SCALE: float = 1.0 if _IS_TOURNAMENT else max(0.1, TOTAL_BANKROLL_USDC / 1000.0)

    # Tamaño por orden para cada una de las 10 estrategias
    STRATEGY_ORDER_SIZE_USDC = {
        "S1_VIGFREE_MAKER": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),          # hi774c / HomeRunHazard
        "S2_LIVE_DUTCHBOOK": round(20.0 if _IS_TOURNAMENT else 14.0 * _BANKROLL_SCALE, 2),         # PEYZ-BIGGEST-FAN / RN1
        "S3_POSTONLY_4LEG_MM": round(22.0 if _IS_TOURNAMENT else 15.0 * _BANKROLL_SCALE, 2),       # calculate10
        "S4_NEGRISK_ARB": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),            # BreakTheBank / Nooserac
        "S5_NEGRISK_CONV_MERGE": round(18.0 if _IS_TOURNAMENT else 11.0 * _BANKROLL_SCALE, 2),     # e46m3
        "S6_LONGSHOT_SELL_MAKER": round(16.0 if _IS_TOURNAMENT else 10.0 * _BANKROLL_SCALE, 2),    # Bigggggggg
        "S7_SPREAD_MIDDLING": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),        # justaluckydude
        "S8_NICHE_PROPS_CORNERS": round(18.0 if _IS_TOURNAMENT else 12.0 * _BANKROLL_SCALE, 2),    # omnibus-076daa
        "S9_NCAAF_NFL_DEEP_ARB": round(20.0 if _IS_TOURNAMENT else 14.0 * _BANKROLL_SCALE, 2),     # primm
        "S10_TENNIS_PENNY_DUST": round(5.0 if _IS_TOURNAMENT else max(2.5, 2.5 * _BANKROLL_SCALE), 2),  # 01258787xy
    }

    # Cuota máxima de margen de apertura que puede bloquear cada estrategia:
    # - En TOURNAMENT_10K_EQUAL: Todas las 10 estrategias tienen exactamente $880.00 USDC de apertura (+ $120.00 de Reserva = $1,000.00 c/u)
    # - En SMART_10_ROTATION   : Cuotas ponderadas que suman $880.00 USDC (+ $120.00 Reserva = $1,000.00 total)
    STRATEGY_MAX_BUDGET_USDC = (
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

    # =========================================================================
    # PARÁMETROS CUANTITATIVOS DE LAS 10 ESTRATEGIAS AUTÓNOMAS (LOTE 1 + LOTE 2)
    # =========================================================================

    # S1: Pre-Match Vig-Free Spreads & Totals (hi774c / HomeRunHazard)
    S1_ENABLED: bool = os.getenv("S1_ENABLED", "true").lower() == "true"
    S1_MIN_VOL_24H: float = 500.0
    S1_BID_MIN: float = 0.440
    S1_BID_MAX: float = 0.495
    S1_ASK_MIN: float = 0.495
    S1_ASK_MAX: float = 0.560
    S1_MAX_COMBINED_COST: float = 0.990

    # S2: In-Play Gamma Scalping / Dutch-Book (PEYZ-BIGGEST-FAN / RN1)
    S2_ENABLED: bool = os.getenv("S2_ENABLED", "true").lower() == "true"
    S2_MIN_VOL_24H: float = 4000.0
    S2_PRICE_MIN: float = 0.18
    S2_PRICE_MAX: float = 0.82
    S2_TARGET_DUTCH_BOOK_SUM: float = 0.945

    # S3: 4-Leg Post-Only HFT Spread Harvester (calculate10)
    S3_ENABLED: bool = os.getenv("S3_ENABLED", "true").lower() == "true"
    S3_MIN_VOL_24H: float = 10000.0
    S3_MIN_SPREAD: float = 0.020
    S3_MAX_SPREAD: float = 0.090
    S3_IMBALANCE_CANCEL_RATIO: float = 0.78

    # S4: Anti-Hype & Matriz Negative-Risk (BreakTheBank / Nooserac)
    S4_ENABLED: bool = os.getenv("S4_ENABLED", "true").lower() == "true"
    S4_MIN_VOL_24H: float = 10000.0
    S4_NEGRISK_MAX_BID_SUM: float = 0.985

    # S5 (NUEVA - Lote 2): Motor NegRisk CONVERSION + MERGE + Bonos Piso (e46m3 - 98.2% Win Intervals)
    S5_ENABLED: bool = os.getenv("S5_ENABLED", "true").lower() == "true"
    S5_MIN_VOL_24H: float = 1500.0
    S5_TAIL_NO_MAX_ASK: float = 0.065     # Compra acciones 'No' / Cola baratas para CONVERSION + MERGE
    S5_FLOOR_BOND_MIN_BID: float = 0.955  # Bonos de piso de alta probabilidad (ej. BTC daily floor / Clima)
    S5_FLOOR_BOND_MAX_ASK: float = 0.991

    # S6 (NUEVA - Lote 2): Cosechador Maker en Venta de Longshots vía SPLIT/CONVERSION (Bigggggggg - 80% Win)
    S6_ENABLED: bool = os.getenv("S6_ENABLED", "true").lower() == "true"
    S6_MIN_VOL_24H: float = 2000.0
    S6_LONGSHOT_MIN_PRICE: float = 0.040
    S6_LONGSHOT_MAX_PRICE: float = 0.260  # Rango de lotería retail (mediana de Bigggggggg: $0.17)

    # S7 (NUEVA - Lote 2): Escalera de Hándicaps Alternativos / Spread Middling (justaluckydude)
    S7_ENABLED: bool = os.getenv("S7_ENABLED", "true").lower() == "true"
    S7_MIN_VOL_24H: float = 300.0
    S7_TARGET_MIDDLE_SUM: float = 0.915   # Costo combinado objetivo entre dos líneas de spread del mismo juego

    # S8 (NUEVA - Lote 2): Props de Nicho, Total de Córners (O/U Corners) y Map Handicaps (omnibus-076daa)
    S8_ENABLED: bool = os.getenv("S8_ENABLED", "true").lower() == "true"
    S8_MIN_VOL_24H: float = 150.0
    S8_TARGET_COMBINED_COST: float = 0.965

    # S9 (NUEVA - Lote 2): Dutch-Book Profundo 0% Fee en Fútbol Americano NCAAF/NFL (primm)
    S9_ENABLED: bool = os.getenv("S9_ENABLED", "true").lower() == "true"
    S9_MIN_VOL_24H: float = 1000.0
    S9_DEEP_ARB_SUM_TARGET: float = 0.860  # Apunta a cierres profundos (0.72 - 0.86) durante volatilidad

    # S10 (NUEVA - Lote 2): Redes de Arrastre ($0.002-$0.015) y Dual-Outcome en Tenis (01258787xy...)
    S10_ENABLED: bool = os.getenv("S10_ENABLED", "true").lower() == "true"
    S10_MIN_VOL_24H: float = 50.0
    S10_STINK_BID_PRICE: float = 0.008     # Red de arrastre ultra-barata para atrapar ventas de pánico en Tenis

    # =========================================================================
    # PARÁMETROS DE OPERACIÓN 24/7 MULTI-DÍA (AUTO-ROTACIÓN Y RECICLAJE)
    # =========================================================================
    # Intervalo de re-escaneo autónomo de Gamma API para incorporar nuevos partidos y purgar cerrados (segundos)
    MARKET_SCAN_INTERVAL_SEC: int = int(os.getenv("MARKET_SCAN_INTERVAL_SEC", "180"))
    # En Modo Torneo permitimos hasta 6 mercados simultáneos por estrategia para desplegar sus $1,000 USDC
    MAX_MARKETS_PER_STRATEGY: int = int(
        os.getenv("MAX_MARKETS_PER_STRATEGY", "6" if _IS_TOURNAMENT else "3")
    )
    # Tiempo máximo (segundos) que una orden de apertura sin llenarse puede estar lejos del precio antes de recotizar
    STALE_ENTRY_ORDER_TIMEOUT_SEC: int = int(os.getenv("STALE_ENTRY_ORDER_TIMEOUT_SEC", "900"))
    # Desviación de precio (centavos) para recotizar una orden de entrada que quedó obsoleta
    REQUOTE_PRICE_DRIFT_THRESHOLD: float = float(os.getenv("REQUOTE_PRICE_DRIFT_THRESHOLD", "0.06"))

