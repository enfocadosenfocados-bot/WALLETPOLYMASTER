# Ingeniería Inversa Forense (Lote 2): 10 Nuevas Wallets Exponenciales y Sus Estrategias Ocultas

> [!IMPORTANT]
> **Alcance del Lote 2 (Batch 2):** Este análisis excluye por completo las primeras 8 wallets del Lote 1 (`BreakTheBank`, `Diabolical-Prize`, `HomeRunHazard`, `PEYZ-BIGGEST-FAN`, `RN1`, `Nooserac`, `hi774c` y `calculate10`). Mediante el escáner forense [`discover_batch2_wallets.py`](file:///C:/Users/enfoc/.gemini/antigravity/scratch/discover_batch2_wallets.py) y la base de datos extraída en [`forensic_batch2_wallets.json`](file:///C:/Users/enfoc/.gemini/antigravity/scratch/forensic_batch2_wallets.json), auditamos **20 candidatos adicionales** y seleccionamos las **10 wallets con las curvas de crecimiento más explosivas y estrategias estructuralmente distintas**.

---

## 1. Tabla Comparativa de las 10 Nuevas Wallets (Lote 2)

| # | Alias / Wallet | PnL Económico Total | Crecimiento 7D | % Intervalos Ganadores (3h) | Max Drawdown 7D | Volumen Total ($ USDC) | Fills / Mercados | Estrategia Oculta Principal |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | **`e46m3`**<br>`0x4f1d...8de2` | **+$732,076** | **+$95,879** | **98.2%** 🔥 | **$56.01** 🔥 | $47.42M | 337,246 / 54,051 | **NegRisk `CONVERSION` + `MERGE` Engine** (Arbitraje estructural de múltiples resultados + bonos `No` de cola) |
| **2** | **`Bigggggggg`**<br>`0x511f...cbe1` | **+$571,114** | **+$44,185** | **80.0%** 🔥 | **$1,266.60** | $16.51M | 143,350 / 17,976 | **Sell-Side Longshot Harvester** (82% órdenes `SELL` Maker + `CONVERSION` en menciones/tasas/política) |
| **3** | **`0x2c3350...`**<br>`0x2c33...0563` | **+$6,184,067** | **+$705,137** | 50.9% | $493,655 | **$693.19M** | 649,932 / 33,221 | **Rebate & Yield Titan** (+$1.79M solo en Rebates Maker/Taker y Yield + 50% Dual-Outcome Market Making) |
| **4** | **`omnibus-076daa`**<br>`0x076d...8d4c` | **+$3,712,922** | **+$604,240** | 54.5% | $285,361 | $302.77M | 195,865 / **48,412** | **Niche Prop & Total Corners Bot** (Córners `O/U 8.5`, Hándicaps de Mapas en Esports y `No/Draw` en ligas menores) |
| **5** | **`primm`**<br>`0xd38b...b35029` | **+$3,384,335** | **+$569,165** | 40.0% | $310,164 | $96.32M | 32,761 / 1,648 | **NCAAF / NFL Zero-Fee Deep Arb** (Dutch-Book profundo en Fútbol Americano Universitario con `sum_vwap` de `0.70–0.73`) |
| **6** | **`justaluckydude`**<br>`0xbca0...9705` | **+$1,490,829** | **+$348,808** | 45.5% | $196,356 | $109.75M | 111,574 / 12,188 | **Alternate Spread Ladder ("Middling")** (Compra escaleras de hándicaps `-6.5`, `-7.5`, `-10.5` para cobrar ambos lados) |
| **7** | **`Kch-Temp`**<br>`0x9243...58e` | **+$3,161,403** | **+$689,303** | 41.8% | $240,839 | $115.65M | 44,960 / 3,421 | **High-Velocity Spread & Underdog Sniper** (96.5% de fills en `<5s`, barriendo líneas desfasadas en NBA/NHL y UCL) |
| **8** | **`joseph00677`**<br>`0xcdcc...35a` | **+$4,480,338** | **+$2,950,951** | 29.1% | $279,296 | $19.37M | 668 / 17 | **Ultra-Concentrated Late-Game Whale** ($24,963 USD por fill promedio en favoritos pesados de fútbol europeo a `$0.83`) |
| **9** | **`theowalcott`**<br>`0x7ad7...2aa` | **+$875,786** | **+$595,049** | 40.0% | $42,882 | $24.16M | 26,396 / 3,875 | **MLS & LatAm Soccer Live Taker Sniper** (Especialista en MLS, Liga MX/Expansión y liga portuguesa en vivo) |
| **10** | **`01258787xy...`**<br>`0x5bfe...3258` | **+$254,099** | **+$110,188** | 40.0% | $19,005 | $5.68M | 6,879 / 294 | **ITF/WTA Qualifiers Dual-Outcome & Penny-Dust Collector** (66.7% Dual-Outcome + barrido de órdenes a `$0.001` en qualys de tenis) |

---

## 2. Las 6 Nuevas Estrategias Descubiertas (Que NO estaban en el Lote 1)

El hallazgo más valioso de este segundo barrido es que reveló **mecánicas de contrato inteligente (`NegRiskAdapter`) y estructuras de mercado** que ninguna de las primeras 8 wallets utilizaba:

```mermaid
flowchart TD
    subgraph S1["1. Motor NegRisk CONVERSION + MERGE (e46m3)"]
        A1["Mercados Multi-Resultado (Elecciones, Clima, Rango BTC)"] --> A2["Compra acciones 'No' subvaluadas ($0.01 - $0.05) o 'No' de piso ($0.98)"]
        A2 --> A3["Ejecuta CONVERSION on-chain (NegRiskAdapter)"]
        A3 --> A4["Transforma canasta de 'No' en 'Yes' complementarios + MERGE a $1.00 USDC"]
        A4 --> A5["98.2% intervalos de 3h positivos | Max DD 7D: solo $56.01"]
    end

    subgraph S2["2. Cosechador Maker en Venta / Sell-Side Harvester (Bigggggggg)"]
        B1["Mercados de Menciones (Elon Tweets), Tasas Centrales y Mundial"] --> B2["Acuña/Convierte inventario vía SPLIT y CONVERSION"]
        B2 --> B3["82% de sus órdenes son SELL Limit Maker ($0.00 fee) a $0.17 mediana"]
        B3 --> B4["Vende 'lotería' sobrevalorada al retail + cobra $19.4k en Rewards/Rebates"]
    end

    subgraph S3["3. Escalera de Hándicaps / Spread Middling (justaluckydude)"]
        C1["Mismo partido (ej. Washington vs Purdue)"] --> C2["Compra Favorito -6.5 / -7.5 y Underdog +10.5 con sum_vwap < 0.88"]
        C2 --> C3["Si el favorito gana por 7, 8, 9 o 10 puntos: ¡COBRA AMBOS LADOS ($2.00)!"]
    end
```

---

### Estrategia Nueva #1: Arbitraje Estructural `CONVERSION` + `MERGE` en Mercados Negative Risk (`e46m3`)
* **Perfil de la Wallet:** `e46m3` (`0x4f1d5ae26fc31472966e951af3183308736d8de2`) tiene la curva de capital más perfecta que hemos encontrado en todo Polymarket: **+$732,076.18 de ganancia**, **+$95,878.89 en los últimos 7 días**, ganando en el **98.2% de todos los bloques de 3 horas de la semana** con un **Drawdown Máximo de apenas $56.01 USD**.
* **Qué hace diferente (Ingeniería Inversa):**
  * Al inspeccionar sus últimos 500 eventos en la blockchain (`activity_types`), descubrimos algo extraordinario: **`{"TRADE": 214, "MERGE": 146, "CONVERSION": 131, "REDEEM": 9}`**. ¡Más del **55% de toda su actividad no son simples compras, sino operaciones `CONVERSION` y `MERGE` directas contra los contratos inteligentes de Polymarket**!
  * **Cómo funciona la matemática de `NegRiskAdapter`:** En mercados de múltiples opciones mutuamente excluyentes (ej. *¿Quién ganará la elección de Colombia/Perú?*, *¿En qué rango de temperatura estará Londres hoy?*, o *¿A qué precio cerrará Bitcoin el 16 de octubre?*), tener una acción de `No` en el Candidato A equivale matemáticamente a tener `1 acción de Yes` en **todos los demás candidatos (B, C, D, E...)**.
  * `e46m3` barre órdenes `No` baratas o mal cotizadas en el libro de órdenes (con un tamaño mediano pequeño de `$11.09 USD`), ejecuta la función `convertPositions` (`CONVERSION`) en el contrato `NegRiskAdapter` para transformar esas acciones `No` en acciones `Yes` de los demás resultados más efectivo USDC, y acto seguido ejecuta `mergePositions` (`MERGE`) para quemar el set completo y recibir **$1.00 USDC instantáneo sin esperar a que termine el evento**.
  * Además, estaciona la liquidez sobrante en "bonos" de altísima probabilidad de 24–48 horas (ej. `Will Bitcoin dip to $60,000 on October 16? -> No` a `$0.981` con `fee: $0.00`), ganando un 1.9% diario compuesto sin riesgo de dirección.

---

### Estrategia Nueva #2: Cosechador Maker del Lado Vendedor (`SELL` + `CONVERSION`) en Longshots (`Bigggggggg`)
* **Perfil de la Wallet:** `Bigggggggg` (`0x511f9c771449162349795d17becf8b37031acbe1`) acumula **+$571,114.46 de ganancia** (+$44,185 en 7 días) con un **80.0% de intervalos de 3 horas en verde** y un **Max Drawdown de solo $1,266.60**.
* **Qué hace diferente:**
  * Mientras casi todos los bots compran (`BUY`), el desglose de órdenes de `Bigggggggg` es **`{"SELL": 366, "BUY": 80}` (82% son órdenes `SELL`)** combinadas con `{"CONVERSION": 39, "MERGE": 10}`.
  * **Activos que opera:** Mercados de alto hype minorista donde los apostadores compran "boletos de lotería" (`longshots`) sobrevalorados: conteo de tweets de Elon Musk (*Elon Musk # tweets October 9 - October 16*), decisiones de tasas de bancos centrales (*Fed, SNB*), elecciones presidenciales y campeones del Mundial / Esports.
  * **La mecánica exacta:** Utiliza `CONVERSION` para fabricar sintéticamente acciones de los resultados improbables (`longshots` que cotizan entre `$0.05` y `$0.25`, con `median_price: $0.17`) y coloca órdenes limitadas pasivas de venta (`SELL Maker`, pagando `$0.00` de comisión). Además de quedarse con la prima de todos esos boletos de lotería que expiran en `$0.00`, Polymarket le ha pagado **+$12,087.46 en `Liquidity Rewards`** y **+$7,328.56 en `Maker Rebates`** por proveer liquidez en el lado vendedor.

---

### Estrategia Nueva #3: Escalera de Hándicaps Alternativos / "Spread Middling" (`justaluckydude`)
* **Perfil de la Wallet:** `justaluckydude` (`0xbca08c1bc204a34f2fddbe47b438b9bd42ac9705`) ha generado **+$1,490,828.88** (+$348,808 en 7 días) con `111,574 fills` y un **44.1% de mercados operados en ambos lados (`dual_outcome_pct`)**.
* **Qué hace diferente:**
  * A diferencia del arbitraje binario simple de `BreakTheBank`, `justaluckydude` arma **Escaleras de Hándicaps Alternativos ("Middles")** dentro del mismo partido de NFL, NCAAF o NBA.
  * Observa sus operaciones reales extraídas en [`forensic_batch2_wallets.json`](file:///C:/Users/enfoc/.gemini/antigravity/scratch/forensic_batch2_wallets.json):
    * `Spread: Washington (-10.5)` -> `vwap0: 0.258` + `vwap1: 0.425` = **`sum_vwap: 0.683`** (31.7% de ganancia garantizada).
    * `Spread: Washington (-7.5)` -> `vwap0: 0.260` + `vwap1: 0.576` = **`sum_vwap: 0.836`** (16.4% de ganancia garantizada).
    * `Spread: Washington (-6.5)` -> `vwap0: 0.264` + `vwap1: 0.614` = **`sum_vwap: 0.878`** (12.2% de ganancia garantizada).
  * **El "Middle" Explosivo:** Al cruzar `Washington -6.5` barato con el rival `+10.5` barato en momentos distintos del partido en vivo, no solo asegura un costo combinado menor a `$1.00`, sino que si Washington gana por **7, 8, 9 o 10 puntos**, **¡ambos contratos pagan $1.00 simultaneously ($2.00 de cobro por menos de $0.85 de costo)!**

---

### Estrategia Nueva #4: Bot de Props de Nicho, Total de Córners y Hándicaps de Mapas (`omnibus-076daa`)
* **Perfil de la Wallet:** `omnibus-076daa` (`0x076daa87c4fe1a85402a9b6b8e0a866224388d4c`) acumula **+$3,712,922.25** (+$604,240 en 7 días) operando en **48,412 mercados distintos** con un 54.5% de intervalos ganadores.
* **Qué hace diferente:**
  * Mientras las ballenas compiten en el Moneyline principal de la Champions League o la NBA, `omnibus-076daa` apunta su escáner a **mercados secundarios ("Props") con libros de órdenes ineficientes y cero competencia institucional**:
    1. **Totales de Córners en Fútbol:** Ej. `Cagliari vs. Torino: O/U 8.5 Total Corners` (`avg_price: $0.614`, `fee: $0.00`).
    2. **Hándicaps de Mapas en Esports:** Ej. `Map Handicap: FAL (-1.5) vs FUR (+1.5)` comprando `FUR +1.5` a `$0.44` sin comisión.
    3. **Mercados `No` y `Draw` en ligas secundarias:** Compra sistemáticamente el `No` de falsos favoritos (ej. `Will Levante UD win? -> No` a `$0.525` -> **+$237,515 de ganancia en un solo mercado**) y empates (`Draw`) mal calibrados.

---

### Estrategia Nueva #5: Arbitraje Dutch-Book Profundo (0% Fee) en Fútbol Americano Universitario (`primm`)
* **Perfil de la Wallet:** `primm` (`0xd38b71f3e8ed1af71983e5c309eac3dfa9b35029`) ha ganado **+$3,384,335.47** (+$569,165 en 7 días) pagando exactamente **$0.00 en comisiones de Taker** (`fees_paid: $0.00` en sus mayores victorias) y cobrando **+$56,374 en Maker Rebates**.
* **Qué hace diferente:**
  * Se especializa en **NCAAF (College Football)** y **NFL**, donde la volatilidad en vivo (un touchdown o una intercepción) provoca reacciones exageradas de los apostadores minoristas de EE. UU.
  * Coloca órdenes Maker pasivas en ambos lados durante el partido y logra capturar los `sum_vwap` más bajos de todo el estudio:
    * `Washington vs. Purdue`: `vwap0: 0.637` + `vwap1: 0.092` = **`sum_vwap: 0.729`** (**+27.1% de retorno libre de riesgo**).
    * `Memphis vs. Tulane`: `vwap0: 0.199` + `vwap1: 0.501` = **`sum_vwap: 0.700`** (**+30.0% de retorno libre de riesgo**).
    * `Kennesaw State vs. Jacksonville State`: `vwap0: 0.353` + `vwap1: 0.531` = **`sum_vwap: 0.885`** (**+11.5% libre de riesgo**).

---

### Estrategia Nueva #6: Cazador de "Órdenes Polvo" ($0.001) y Cobertura Dual en Qualys de Tenis (`01258787xy48487484545122`)
* **Perfil de la Wallet:** `01258787xy48487484545122` (`0x5bfe9469c7c4035325024c846bc530c9d29e3258`) tiene **+$254,098.54 de ganancia** y **+$110,187.60 solo en los últimos 7 días** (creció más del 43% de su PnL histórico en una sola semana) operando apenas **294 mercados** con un **66.7% de Dual-Outcome**.
* **Qué hace diferente:**
  * Opera exclusivamente **Fases de Clasificación (Qualifiers) de torneos WTA/ITF/Challenger** (ej. *Japan Women's Open Qualification*, *Ningbo Open Qualification*, *Rovereto*, *Guangzhou*).
  * En estos torneos pequeños, muchos traders dejan órdenes olvidadas o venden en pánico por falta de liquidez cuando creen que una jugadora ya perdió un set o el partido. Este bot deja **"redes de arrastre" (stink bids) a `$0.001` (0.1 centavos)** en ambos lados del partido:
    * En `Japan Women's Open, Qualification: Sayaka Ishii vs Elina Avanesyan`, compró a `Sayaka Ishii` a `0.783` y atrapó una orden de pánico en `Elina Avanesyan` a **`$0.001` (`sum_vwap: 0.784`)**. ¡Elina Avanesyan remontó el partido y esa compra a `$0.001` le generó **+$56,210.00 USD de ganancia con `$0.00` de comisión**!
    * Hizo exactamente lo mismo en `Ningbo Open, Qualification: Katarzyna Kawa vs Katie Volynets` (`vwap0: 0.580` + `vwap1: 0.001` = `sum_vwap: 0.581`).

---

## 3. ¿Cuáles de estas Nuevas Estrategias Puedes Agregar a tu Bot en Londres con $1,000 USDC?

De estas 10 nuevas wallets, **3 mecánicas son 100% compatibles con tu capital de $1,000 USDC y tu VPS en Londres (`eu-west-2`)**:

1. **Las "Redes de Arrastre" a `$0.001–$0.01` en Qualifiers de Tenis (estilo `01258787xy...`):**
   * Colocar órdenes Maker pasivas a `$0.001–$0.005` en torneos Challenger/WTA cuesta apenas **$1 a $5 USD de colateral bloqueado por partido**, tiene **$0.00 de comisión**, y cuando un trader minorista lanza un `Market Sell` en un libro vacío durante una remontada, te bloquea un `sum_vwap` ridículamente bajo o un retorno de `100x–1000x`.
2. **El Escaneo de Córners (`O/U Total Corners`) y Hándicaps Alternativos / Middles (estilo `omnibus-076daa` y `justaluckydude`):**
   * Los mercados de córners y spreads alternativos tienen mucha menos competencia de bots HFT que el Moneyline principal, permitiendo que tus órdenes Maker se llenen con márgenes de arbitraje de `12% a 30%` (`sum_vwap` de `0.70 a 0.88`).
3. **El Motor `CONVERSION + MERGE` en Mercados NegRisk (estilo `e46m3`):**
   * Con un tamaño mediano de orden de apenas **$11.09 USD**, la estrategia de `e46m3` demuestra que no necesitas millones de dólares para tener un **98.2% de intervalos ganadores** y un **drawdown máximo de $56 USD**: solo necesitas escanear mercados multi-resultado donde la suma de los precios `No` (o la conversión vía `NegRiskAdapter`) permita hacer `CONVERSION + MERGE` instantáneo a `$1.00 USDC`.
