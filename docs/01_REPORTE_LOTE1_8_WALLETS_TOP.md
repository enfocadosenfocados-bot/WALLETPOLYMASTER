# 📊 Análisis Forense & Scraping de Wallets de Alto Rendimiento en Polymarket

Este informe documenta la extracción, ingeniería inversa y análisis cuantitativo de las **mejores wallets de Polymarket**: aquellas que combinan un **crecimiento acelerado**, **alta consistencia temporal** y una **elevada frecuencia de trades** (evitando cuentas con un único golpe de suerte).

---

## 🛠️ Metodología de Ingeniería Inversa (REA & Obscura)

Siguiendo el flujo de **REA (*Reverse Engineer Anything*)** y técnicas de inspección de headless browser (**Obscura**):
1. Se inspeccionó la carga dinámica de Next.js App Router en `polymarket.com/leaderboard` capturando el estado deshidratado de TanStack Query (`self.__next_f`).
2. Se extrajeron y validaron las APIs subyacentes sin restricciones de Cloudflare:
   - **Leaderboard Global:** `https://data-api.polymarket.com/v1/leaderboard?window={1d|7d|30d}&orderBy={pnl|vol}`
   - **Métricas Detalladas de Usuario:** `https://data-api.polymarket.com/v2/user-stats?user={proxyWallet}`
   - **Curva Temporal de PnL de Alta Fidelidad:** `https://data-api.polymarket.com/v2/user-pnl?user={proxyWallet}&interval=1w&fidelity=3h`
   - **Portafolio y Posiciones Activas:** `https://data-api.polymarket.com/v2/positions?user={proxyWallet}&status=OPEN`

---

## 🏆 Ranking de las Mejores Wallets (Crecimiento Acelerado, Alto Volumen y Frecuencia)

| # | Trader / Usuario | Wallet Proxy | PnL 7D / Run-Rate | PnL Total | Trades Totales | Volumen Negociado | Consistencia (Win Intervals) |
|---|---|---|---|---|---|---|---|
| **1** | [**BreakTheBank**](https://polymarket.com/profile/0xf0318c32136c2db7fec88b84869aee6a1106c80c) | `0xf031...c80c` | **+$2,897,252** *(30D: +$4.77M)* | **+$7,487,460** | **271,612** | $292,114,113 | **78.4%** (Curva casi ininterrumpida) |
| **2** | [**Diabolical-Prize**](https://polymarket.com/profile/0x7c37b52eb226bcb9411375ec48b0169663fb6aeb) | `0x7c37...6aeb` | **+$1,789,423** *(1D: +$1.78M)* | **+$1,600,946** | **29,064** | $78,182,461 | **54.2%** (Disparo vertical masivo) |
| **3** | [**HomeRunHazard**](https://polymarket.com/profile/0x5268527977f700f9bf9b6d5cd843859e4e70135d) | `0x5268...135d` | **+$196,235** *(1D: +$87.5k)* | **+$2,943,015** | **710,585** | $428,367,764 | **60.0%** (Sólido y muy consistente) |
| **4** | [**PEYZ-BIGGEST-FAN**](https://polymarket.com/profile/0xdaef2be2a19ad331737d06545f85615b094554e9) | `0xdaef...54e9` | **+$301,980** *(1D: +$40.0k)* | **+$729,235** | **41,018** | $26,078,453 | **57.1%** (Bajo drawdown: solo $33k) |
| **5** | [**RN1**](https://polymarket.com/profile/0x2005d16a84ceefa912d4e380cd32e7ff827875ea) | `0x2005...75ea` | **+$251,968** *(1D: +$20.8k)* | **+$14,725,810** | **4,953,277** | $1,376,363,993 | **50.9%** (Market maker algorítmico #1) |
| **6** | [**Nooserac**](https://polymarket.com/profile/0xf68a281980f8c13828e84e147e3822381d6e5b1b) | `0xf68a...5b1b` | **+$107,721** *(1D: +$44.0k)* | **+$1,316,856** | **310,981** | $190,898,549 | **52.7%** (Estrategia balanceada) |
| **7** | [**hi774c**](https://polymarket.com/profile/0x21f333307ac6d2e65ac82f014b3dd2b64cbc35e3) | `0x21f3...35e3` | **+$58,433** *(1D: +$25.8k)* | **+$161,425** | **59,023** | $36,722,163 | **62.5%** (Ratio de acierto sobresaliente) |
| **8** | [**calculate10**](https://polymarket.com/profile/0xb35f674af4603c9602dfbf39564087e94897cf4c) | `0xb35f...cf4c` | **+$41,647** *(1D: +$49.4k)* | **+$229,289** | **67,966** | $19,525,597 | **49.1%** (Especialista en Esports) |

---

## 🔍 Análisis Individual de las Mejores Wallets

### 1. `BreakTheBank` (`0xf0318c32136c2db7fec88b84869aee6a1106c80c`)
* **Perfil:** Algoritmo de arbitraje estadístico y provisión de liquidez en eventos de alto impacto.
* **Crecimiento 7D:** Pasó de \$4.91M a **\$7.80M** en tiempo real (más de \$2.89M netos en 7 días).
* **Frecuencia:** **271,612 ejecuciones**, promediando decenas de trades por hora.
* **Consistencia:** 78.4% de los intervalos de 3 horas cerraron con PnL positivo neto.

### 2. `Diabolical-Prize` (`0x7c37b52eb226bcb9411375ec48b0169663fb6aeb`)
* **Perfil:** Trader agresivo de momentum y eventos deportivos/esports.
* **Crecimiento:** Encabezó el ranking diario y semanal con un salto extraordinario de **+$1.78M** en 24h.
* **Frecuencia:** **29,064 trades**, volumen acumulado de \$78M.
* **Posiciones Actuales:** Esports (VCT Valorant) y futuros de NFL championship.

### 3. `HomeRunHazard` (`0x5268527977f700f9bf9b6d5cd843859e4e70135d`)
* **Perfil:** Bot sistemático enfocado en spreads de deportes y over/under.
* **Consistencia:** 60.0% de períodos positivos; control de riesgo estricto (máximo drawdown de \$114k sobre casi \$3M de PnL).
* **Frecuencia:** **710,585 trades** ejecutados con \$428M en volumen.

### 4. `PEYZ-BIGGEST-FAN` (`0xdaef2be2a19ad331737d06545f85615b094554e9`)
* **Perfil:** Crecimiento acelerado con control de volatilidad de élite.
* **Crecimiento 7D:** **+$301,980** en los últimos 7 días con un drawdown máximo de apenas **\$33,239**.
* **Trades:** **41,018 trades**, operando política y mercados geopolíticos estructurados.

### 5. `hi774c` (`0x21f333307ac6d2e65ac82f014b3dd2b64cbc35e3`)
* **Perfil:** Trader de alta precisión matemática con un **62.5% de intervalos ganadores**.
* **Trades:** **59,023 trades** con un drawdown de solo \$25k.

---

## 📡 Cómo Monitorear o Automatizar el Copy-Trading

Para seguir estas wallets en tiempo real mediante script, los endpoints directos son:

```python
import requests

# Monitorear operaciones en tiempo real de una wallet:
wallet = "0xf0318c32136c2db7fec88b84869aee6a1106c80c"
trades = requests.get(f"https://data-api.polymarket.com/trades?user={wallet}&limit=20").json()

# Obtener posiciones abiertas actualizadas:
positions = requests.get(f"https://data-api.polymarket.com/v2/positions?user={wallet}&status=OPEN").json()
```
