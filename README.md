# 🤖 WALLETPOLYMASTER — Motor Autónomo de 10 Estrategias Cuantitativas para Polymarket (London VPS Edition)

Repositorio maestro que contiene:
1. **El Motor Autónomo de Trading en Tiempo Real (`bot.py`, `strategies.py`, `execution_engine.py`, `market_scanner.py`, `config.py`)** con **10 estrategias institucionales 100% automáticas** (sin copiar órdenes con retraso).
2. **El Gestor Dinámico de Margen para cuentas desde $1,000 USDC** con **Reserva Intocable de Cobertura ($120 USDC)** y **Auto-Reciclaje Instantáneo On-Chain (`MERGE` / `CONVERSION`)**.
3. **El Modo Auditor de Simulación en Vivo (`LIVE_TRADING=false`)** sobre el flujo real del WebSocket L2 de Polymarket (`wss://ws-subscriptions-clob.polymarket.com/ws/market`) que genera reportes automáticos en [`paper_trading_report.json`](./paper_trading_report.json) sin arriesgar un solo centavo.
4. **Todos los Reportes Forenses (`docs/`) y Herramientas de Scraping / Ingeniería Inversa (`forensic_tools/`)** de las **18 wallets más rentables y de crecimiento más explosivo** de Polymarket (Lote 1 + Lote 2).

---

## 📂 Estructura del Repositorio

```text
WALLETPOLYMASTER/
├── bot.py                        # Orquestador principal de las 10 estrategias + Tablero Auditor en vivo
├── config.py                     # Parámetros cuantitativos (S1 a S10) y presupuesto de margen ($1,000 USDC)
├── market_scanner.py             # Escáner autónomo Gamma API con deduplicación global de mercados
├── execution_engine.py           # Motor CLOB Post-Only Maker + Gestor de Margen + Auto-Merge On-Chain
├── strategies.py                 # Máquinas de estado en tiempo real para las 10 estrategias (Lote 1 + Lote 2)
├── setup_credentials.py          # Inicializador: prueba latencia Londres, aprueba contratos Polygon y crea API Keys L2
├── setup_vps_london.sh           # Instalador automático para VPS Ubuntu 24.04 en Londres (BBR, Chrony, systemd)
├── requirements.txt              # Librerías requeridas (websockets, py-clob-client, web3, python-dotenv)
├── .env.example                  # Plantilla de configuración (Modo Simulación / Modo Real / Modos de Portafolio)
├── paper_trading_report.json     # Reporte generado en tiempo real por el Tablero Auditor de Paper Trading
├── docs/                         # 5 Reportes completos de Ingeniería Inversa Forense y Arquitectura
│   ├── 01_REPORTE_LOTE1_8_WALLETS_TOP.md
│   ├── 02_INGENIERIA_INVERSA_ESTRATEGIAS_LOTE1.md
│   ├── 03_REPORTE_LOTE2_10_NUEVAS_WALLETS_EXPONENCIALES.md
│   ├── 04_GUIA_INFRAESTRUCTURA_VPS_LONDRES_Y_CAPITAL.md
│   └── 05_ARQUITECTURA_SISTEMA_AUTONOMO.md
└── forensic_tools/               # Scripts y bases de datos JSON del scraping forense (Lote 1 y Lote 2)
    ├── polymarket_analyzer.py
    ├── rank_wallets.py
    ├── forensic_strategy_deconstructor.py
    ├── discover_batch2_wallets.py
    ├── latency_and_market_audit.py
    ├── autonomous_market_selector.py
    ├── polymarket_wallets_analyzed.json
    ├── forensic_strategies_output.json
    └── forensic_batch2_wallets.json
```

---

## 🧠 Las 10 Estrategias Autónomas Integradas (`S1` a `S10`)

| Código | Estrategia | Wallets de Referencia (Ingeniería Inversa) | Mecánica Exacta que Ejecuta el Bot | Cupo Margen (de $1,000) | Orden Base |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **`S1_VIGFREE_MAKER`** | **Spreads & Totales 50/50 Vig-Free Pre-Partido** | `hi774c` (+$783k)<br>`HomeRunHazard` (+$1.39M) | Cotiza `BUY Post-Only` en ambos lados de Spreads/Totales pre-partido (`$0.47–$0.495`) buscando `Costo_A + Costo_B <= $0.990` con `$0.00` fee + Rebates. | **$90 USDC** | $12.00 |
| **`S2_LIVE_DUTCHBOOK`** | **In-Play Gamma Scalping / Dutch-Book en Vivo** | `PEYZ-BIGGEST-FAN` (+$1.32M)<br>`RN1` (+$1.87M) | Compra caídas rápidas en partidos en vivo y coloca de inmediato la trampa en el rival (`is_hedge_leg=True`) a `0.945 - VWAP_A` (+5.5% libre de riesgo). | **$100 USDC** | $14.00 |
| **`S3_POSTONLY_4LEG_MM`** | **Market Making HFT Post-Only de 4 Patas + Filtro L2** | `calculate10` (+$296k, 81.8% Win) | Cotiza 1 tick adentro de spreads de `2 a 9 centavos` con `postOnly=True` y cancela en `<2ms` si el desbalance del libro L2 supera el `78%`. | **$120 USDC** | $15.00 |
| **`S4_NEGRISK_ARB`** | **Absorción Pasiva Anti-Favorito en Eventos NegRisk** | `BreakTheBank` (+$2.75M)<br>`Nooserac` (+$577k) | En eventos multi-resultado con `sum(bids) <= 0.985`, compra pasivamente el lado `No` contra favoritos sobrevalorados por el hype. | **$80 USDC** | $12.00 |
| **`S5_NEGRISK_CONV_MERGE`** | **Motor On-Chain `CONVERSION + MERGE` + Bonos Piso** | `e46m3` (+$732k, **98.2% Win**, **$56 Max DD**) | Compra colas subvaluadas (`$0.005–$0.065`) y bonos de piso (`$0.955–$0.990`), y ejecuta `convertPositions` + `mergePositions` a `$1.00 USDC` al instante. | **$130 USDC** | $11.00 |
| **`S6_LONGSHOT_SELL_MAKER`** | **Cosechador Maker en Venta de Longshots ("Lotería")** | `Bigggggggg` (+$571k, **80.0% Win**, $1.2k DD) | Cosecha la decadencia de opciones improbables (`$0.04–$0.26` en tweets de Elon Musk, Fed, política) como Maker (`$0.00 fee` + Rewards/Rebates). | **$80 USDC** | $10.00 |
| **`S7_SPREAD_MIDDLING`** | **Escalera de Hándicaps Alternativos ("Spread Middling")** | `justaluckydude` (+$1.49M, 44.1% Dual) | Cruza líneas de spread alternativos del mismo partido (`sum_vwap <= 0.915`). Si el marcador cae en el medio, **cobra ambos lados ($2.00 total)**. | **$90 USDC** | $12.00 |
| **`S8_NICHE_PROPS_CORNERS`** | **Props de Nicho: Total de Córners y Map Handicaps** | `omnibus-076daa` (+$3.71M en 48,412 mkts) | Opera libros secundarios sin competencia de bots HFT (`O/U Total Corners` en fútbol, `Map Handicap -1.5/+1.5` en Esports). | **$90 USDC** | $12.00 |
| **`S9_NCAAF_NFL_DEEP_ARB`** | **Dutch-Book Profundo (0% Fee) en Fútbol Americano** | `primm` (+$3.38M, `sum_vwap` 0.70–0.86) | Aprovecha sobre-reacciones minoristas en touchdowns para cerrar ambos equipos con `sum_vwap <= 0.860` (+14% a +30% libre de riesgo). | **$80 USDC** | $14.00 |
| **`S10_TENNIS_PENNY_DUST`** | **Redes de Arrastre (`$0.002–$0.015`) en Tenis** | `01258787xy...` (+$254k, +$110k en 7D) | Coloca órdenes Maker ultra-baratas (`$2.50 USDC` por orden a `$0.008`) en ambos lados de partidos de Tenis para atrapar ventas de pánico en libros vacíos. | **$20 USDC** | $2.50 |

---

## 🛡️ Arquitectura de Margen para $1,000 USDC (Cómo Nunca Quedarse sin Liquidez)

1. **Cupo de Apertura ($880 USDC) + Reserva Intocable de Cobertura ($120 USDC):**
   * El motor nunca permite que las órdenes de apertura bloqueen más de **$880 USDC**.
   * Los **$120 USDC restantes (`HEDGE_RESERVE_USDC`)** están reservados exclusivamente para órdenes con `is_hedge_leg=True` (la Pata B que cierra el arbitraje cuando se llena la Pata A).
2. **Auto-Reciclaje Instantáneo On-Chain (`execute_instant_merge_or_conversion`):**
   * En cuanto el bot acumula `Outcome A + Outcome B` en un mismo `condition_id` con costo combinado `< $1.00`, ejecuta `mergePositions` en el contrato `ConditionalTokens` de Polygon para convertir las acciones en **$1.00 USDC en efectivo de inmediato**, liberando el margen en segundos sin esperar a que termine el evento.
3. **Dos Modos de Portafolio (`PORTFOLIO_MODE` en `.env`):**
   * `SMART_10_ROTATION` *(por defecto)*: Opera las 10 estrategias al mismo tiempo respetando el cupo de cada una para cubrir las 24 horas del día (Tenis y Fútbol Europeo en la mañana, NCAAF/NFL/NBA en la noche, Política/Tweets/NegRisk 24/7).
   * `CORE_CONCENTRATED`: Concentra el 100% de los $1,000 USDC (multiplicando ×1.8 el cupo por estrategia) únicamente en las **5 estrategias de menor Drawdown y mayor rotación** (`S5`, `S3`, `S8`, `S1` y `S10`).

---

## 🚀 PASO 1: Clonar y Probar en Vivo SIN RIESGO (Modo Paper Trading) en Cualquier PC

Puedes clonar este repositorio en cualquier computadora (Windows, Mac o Linux) y ponerlo a prueba en tiempo real contra el WebSocket verdadero de Polymarket **sin conectar ninguna wallet ni arriesgar dinero**:

```bash
git clone https://github.com/enfocadosenfocados-bot/WALLETPOLYMASTER.git
cd WALLETPOLYMASTER
pip install -r requirements.txt
```

### Ejecutar una prueba en vivo de 60 segundos o continua:
```bash
# Prueba rápida de 60 segundos con reporte final en consola y en paper_trading_report.json:
python bot.py --test-seconds 60

# O dejarlo corriendo continuamente en modo Paper Trading (actualiza el tablero cada 60s):
python bot.py
```

Cada 60 segundos (y al finalizar), el bot guarda automáticamente el desglose de órdenes, fills, margen usado, fusiones `Auto-Merge` y PnL neto de cada una de las 10 estrategias en [`paper_trading_report.json`](./paper_trading_report.json).

---

## 🌍 PASO 2: Despliegue en Producción 24/7 con Dinero Real en la VPS de Londres (`eu-west-2`)

### 1. Requisitos de Infraestructura y Costos Reales
* **VPS en Londres (`AWS Lightsail eu-west-2` o `Vultr London`):** Ubuntu 24.04 LTS, 2 vCPU / 2 GB RAM (**$5 a $10 USD/mes**). Te da **`1.2 ms a 2.5 ms` de latencia** directa al motor CLOB de Polymarket en Londres (`cloudflare-LHR`).
* **WebSocket L2 (`wss://ws-subscriptions-clob.polymarket.com/ws/market`) y Gamma API:** **$0.00 USD (100% gratuitos)**.
* **Comisiones del CLOB en Órdenes Maker (`postOnly=True`):** **$0.00 USD (0 bps)** + pago de **Maker Rebates** a tu favor.
* **Wallet Dedicada para el Bot (MetaMask / Rabby — `SIGNATURE_TYPE=0`):**
  * **$1,000 USDC.e** (Bridged USDC en la red Polygon: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`).
  * **$5 a $8 USD en `POL` (antes MATIC)** en la red Polygon para pagar el gas de aprobación de contratos y las fusiones automáticas `Auto-Merge` (~$0.003 USD por fusión).

### 2. Instalación Automática en la VPS de Londres
Conéctate por SSH a tu VPS de Londres y ejecuta:

```bash
git clone https://github.com/enfocadosenfocados-bot/WALLETPOLYMASTER.git
cd WALLETPOLYMASTER
bash setup_vps_london.sh
```
*(Este script instala `chrony` para sincronización de reloj sub-milisegundo, activa `TCP BBR`, amplía descriptores de red para WebSockets y crea el entorno virtual `.venv`).*

### 3. Configurar `.env` y Aprobar Contratos Oficiales en Polygon
1. Crea tu archivo `.env` a partir de la plantilla:
   ```bash
   cp .env.example .env
   nano .env
   ```
2. Pega tu `PRIVATE_KEY=0x...` de tu wallet dedicada del bot (mantén `LIVE_TRADING=false` mientras corres el inicializador).
3. Ejecuta el script inicializador todo-en-uno:
   ```bash
   source .venv/bin/activate
   python setup_credentials.py
   ```
   Este script verificará automáticamente:
   * Que tu VPS en Londres tenga `<3 ms` de latencia al CLOB (`-LHR`) y no tenga geobloqueo.
   * Tus saldos de `POL` y `USDC.e`.
   * Aprobará en la blockchain de Polygon los **3 contratos oficiales de Polymarket** (`CTF Exchange`, `NegRisk CTF Exchange` y `NegRisk Adapter` `0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296`).
   * Generará gratis tus credenciales L2 (`POLY_API_KEY`, `POLY_API_SECRET`, `POLY_API_PASSPHRASE`).
4. Copia esas 3 credenciales dentro de tu archivo `.env`.

### 4. Encender el Bot en Dinero Real 24/7
Cuando ya hayas verificado el desempeño en modo simulación (`LIVE_TRADING=false`) y quieras pasar a dinero real:
1. Abre `.env` y cambia:
   ```ini
   LIVE_TRADING=true
   ```
2. Inicia el servicio automático 24/7 (se reinicia solo si el servidor se actualiza):
   ```bash
   sudo systemctl enable polymarket-bot
   sudo systemctl start polymarket-bot
   sudo journalctl -u polymarket-bot -f
   ```
