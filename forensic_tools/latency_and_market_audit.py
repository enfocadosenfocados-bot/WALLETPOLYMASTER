import urllib.request
import json
import statistics
from collections import defaultdict

with open('C:/Users/enfoc/.gemini/antigravity/scratch/forensic_strategies_output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=== 1. LATENCY, FEE & HOLD PROFILE COMPARISON ===")
for w in data:
    name = w['name']
    tm = w['timing_microstructure']
    op = w['open_portfolio_profile']
    cp = w['closed_portfolio_profile']
    ha = w['hedging_and_arb']
    
    open_holds = [p['hold_hours'] for p in op['top_open_positions'] if p['hold_hours'] is not None]
    med_open_hold = statistics.median(open_holds) if open_holds else 0
    
    print(
        f"{name:18s} | MedDelta={tm['median_seconds_between_trades']:5.1f}s "
        f"| <5s={tm['under_5s_trades_pct']:4.1f}% "
        f"| OpenFee={op['effective_open_fee_rate_bps']:6.2f}bps "
        f"| DualSide={ha['dual_outcome_pct']:4.1f}% "
        f"| MedOpenHold={med_open_hold:6.1f}h "
        f"| MedClosedHold={cp['median_hold_hours']:5.1f}h"
    )

print("\n=== 2. EMPIRICAL COPY-TRADE SLIPPAGE / PRICE DRIFT ANALYSIS ===")
# For each wallet, fetch last 500 trades and check price movement within the same token_id over 10s, 60s, 300s
headers = {'User-Agent': 'Mozilla/5.0'}
for w in data:
    name = w['name']
    wallet = w['wallet']
    url = f"https://data-api.polymarket.com/v2/activity?user={wallet}&limit=500"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as r:
        acts = [a for a in json.loads(r.read().decode()).get('data', []) if a.get('type') == 'TRADE']
    
    # Sort chronologically (oldest first)
    acts.sort(key=lambda x: int(x.get('timestamp', 0)))
    by_token = defaultdict(list)
    for a in acts:
        by_token[a.get('token_id')].append(a)
        
    drifts_60s = []
    burst_lengths = []
    for tid, tlist in by_token.items():
        if len(tlist) < 2:
            continue
        p_first = float(tlist[0].get('price', 0))
        p_last = float(tlist[-1].get('price', 0))
        dt_total = int(tlist[-1].get('timestamp', 0)) - int(tlist[0].get('timestamp', 0))
        burst_lengths.append(dt_total)
        # Find price change from first fill to fills > 30s later
        for x in tlist[1:]:
            dt = int(x.get('timestamp', 0)) - int(tlist[0].get('timestamp', 0))
            if 10 <= dt <= 120:
                drifts_60s.append(float(x.get('price', 0)) - p_first)
                break
                
    med_window = statistics.median(burst_lengths) if burst_lengths else 0
    avg_drift = statistics.mean(drifts_60s) if drifts_60s else 0
    print(f"{name:18s} | Median Accumulation Window per Token: {med_window:6.0f}s ({med_window/60:.1f} min) | Avg Self-Price Impact (10-120s): {avg_drift:+.4f}")
