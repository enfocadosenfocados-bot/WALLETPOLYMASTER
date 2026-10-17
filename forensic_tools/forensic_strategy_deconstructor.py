import urllib.request
import json
import time
import statistics
from collections import defaultdict, Counter

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

TARGET_WALLETS = [
    ("BreakTheBank", "0xf0318c32136c2db7fec88b84869aee6a1106c80c"),
    ("Diabolical-Prize", "0x7c37b52eb226bcb9411375ec48b0169663fb6aeb"),
    ("HomeRunHazard", "0x5268527977f700f9bf9b6d5cd843859e4e70135d"),
    ("PEYZ-BIGGEST-FAN", "0xdaef2be2a19ad331737d06545f85615b094554e9"),
    ("RN1", "0x2005d16a84ceefa912d4e380cd32e7ff827875ea"),
    ("Nooserac", "0xf68a281980f8c13828e84e147e3822381d6e5b1b"),
    ("hi774c", "0x21f333307ac6d2e65ac82f014b3dd2b64cbc35e3"),
    ("calculate10", "0xb35f674af4603c9602dfbf39564087e94897cf4c"),
]

def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if i == retries - 1:
                return None
            time.sleep(0.4)

def classify_market(title, slug, event_slug):
    s = f"{title} {slug} {event_slug}".lower()
    if any(k in s for k in ['lol-', 'lol:', 'league of legends', 'dota', 'valorant', 'cs2', 'counter-strike', 'esports']):
        sub = 'Esports: LoL/Dota/Val/CS2'
    elif any(k in s for k in ['nfl', 'nba', 'mlb', 'nhl', 'ncaa', 'cfb', 'cbb', 'spread:', 'o/u', 'over', 'under']):
        if 'spread:' in s:
            sub = 'US Sports: Spreads'
        elif 'o/u' in s or 'over/under' in s:
            sub = 'US Sports: Totals (O/U)'
        else:
            sub = 'US Sports: Moneyline / Futures'
    elif any(k in s for k in ['epl', 'ucl', 'fc ', 'vs.', 'draw', 'fifa', 'fifwc', 'la liga', 'serie a', 'bundesliga', 'soccer']):
        if 'draw' in s:
            sub = 'Soccer: Draw Markets'
        else:
            sub = 'Soccer: Match Winner / Futures'
    elif any(k in s for k in ['atp', 'wta', 'tennis', 'open']):
        sub = 'Tennis'
    elif any(k in s for k in ['senate', 'house', 'election', 'president', 'governor', 'republican', 'democratic', 'trump', 'vance', 'netanyahu', 'iran', 'israel', 'ukraine', 'russia', 'ceasefire', 'prime minister', 'weed']):
        sub = 'Politics & Geopolitics'
    elif any(k in s for k in ['bitcoin', 'btc', 'eth', 'solana', 'crypto', 'fed ', 'interest rate']):
        sub = 'Crypto & Macro'
    else:
        sub = 'Other / Props'
    return sub

def analyze_wallet(name, wallet):
    print(f"Deep forensic analysis for {name} ({wallet})...")
    
    # 1. User stats
    stats_raw = fetch_json(f"https://data-api.polymarket.com/v2/user-stats?user={wallet}") or {}
    stats_data = stats_raw.get('data', {}) or {}
    all_time = stats_data.get('all_time_pnl', {}) or {}
    
    # 2. Fetch 1000 recent activity items (2 pages of 500)
    act_page1 = fetch_json(f"https://data-api.polymarket.com/v2/activity?user={wallet}&limit=500") or {}
    activities = act_page1.get('data', []) or []
    next_cursor = (act_page1.get('pagination') or {}).get('next_cursor')
    if next_cursor:
        act_page2 = fetch_json(f"https://data-api.polymarket.com/v2/activity?user={wallet}&limit=500&cursor={next_cursor}") or {}
        activities.extend(act_page2.get('data', []) or [])
        
    # 3. Open positions (top 100 by current value)
    open_pos_raw = fetch_json(f"https://data-api.polymarket.com/v2/positions?user={wallet}&status=OPEN&limit=100&sort_by=CURRENT_VALUE&sort_direction=DESC") or {}
    open_positions = open_pos_raw.get('data', []) or []
    
    # 4. Closed positions: Top 50 biggest wins & Top 50 biggest losses
    closed_wins_raw = fetch_json(f"https://data-api.polymarket.com/v2/positions?user={wallet}&status=CLOSED&limit=50&sort_by=REALIZED_PNL&sort_direction=DESC") or {}
    closed_wins = closed_wins_raw.get('data', []) or []
    
    closed_losses_raw = fetch_json(f"https://data-api.polymarket.com/v2/positions?user={wallet}&status=CLOSED&limit=50&sort_by=REALIZED_PNL&sort_direction=ASC") or {}
    closed_losses = closed_losses_raw.get('data', []) or []
    
    # --- FORENSIC CALCULATIONS ---
    act_types = Counter(a.get('type') for a in activities)
    trades = [a for a in activities if a.get('type') == 'TRADE']
    
    sides = Counter(t.get('side') for t in trades)
    outcomes = Counter(t.get('outcome') for t in trades)
    
    # Price band analysis
    price_bands = Counter()
    prices = []
    usdc_sizes = []
    categories = Counter()
    category_usdc = defaultdict(float)
    
    # Group trades by condition_id to detect dual-side trading / arbitrage / hedging
    by_condition = defaultdict(list)
    by_token = defaultdict(list)
    tx_hashes = Counter()
    
    for t in trades:
        p = float(t.get('price') or 0)
        u = float(t.get('usdc_size') or 0)
        prices.append(p)
        usdc_sizes.append(u)
        if p < 0.10:
            price_bands['01_Penny_Longshot (<0.10)'] += 1
        elif p < 0.35:
            price_bands['02_Underdog (0.10-0.35)'] += 1
        elif p <= 0.65:
            price_bands['03_CoinFlip_Mid (0.35-0.65)'] += 1
        elif p <= 0.90:
            price_bands['04_Favorite (0.65-0.90)'] += 1
        else:
            price_bands['05_HeavyFav_Bond (>0.90)'] += 1
            
        cat = classify_market(t.get('title', ''), t.get('slug', ''), t.get('event_slug', ''))
        categories[cat] += 1
        category_usdc[cat] += u
        
        cid = t.get('condition_id')
        if cid:
            by_condition[cid].append(t)
        tid = t.get('token_id')
        if tid:
            by_token[tid].append(t)
        tx = t.get('transaction_hash')
        if tx:
            tx_hashes[tx] += 1

    # Analyze dual-outcome trading on the same condition_id
    dual_outcome_conditions = 0
    arb_sum_lt_1_conditions = 0
    same_token_buy_and_sell = 0
    dual_examples = []
    
    for cid, c_trades in by_condition.items():
        idx_set = set(x.get('outcome_index') for x in c_trades if x.get('outcome_index') is not None)
        if len(idx_set) > 1:
            dual_outcome_conditions += 1
            # Compute VWAP buy price for outcome 0 and outcome 1
            buys_0 = [x for x in c_trades if x.get('outcome_index') == 0 and x.get('side') == 'BUY']
            buys_1 = [x for x in c_trades if x.get('outcome_index') == 1 and x.get('side') == 'BUY']
            if buys_0 and buys_1:
                sz0 = sum(float(x.get('size', 0)) for x in buys_0)
                sz1 = sum(float(x.get('size', 0)) for x in buys_1)
                vwap0 = sum(float(x.get('usdc_size', 0)) for x in buys_0) / sz0 if sz0 > 0 else 0
                vwap1 = sum(float(x.get('usdc_size', 0)) for x in buys_1) / sz1 if sz1 > 0 else 0
                if 0 < vwap0 + vwap1 < 1.0:
                    arb_sum_lt_1_conditions += 1
                if len(dual_examples) < 5:
                    dual_examples.append({
                        'title': c_trades[0].get('title'),
                        'vwap0': round(vwap0, 4),
                        'vwap1': round(vwap1, 4),
                        'sum_vwap': round(vwap0 + vwap1, 4),
                        'size0': round(sz0, 1),
                        'size1': round(sz1, 1)
                    })

    for tid, t_trades in by_token.items():
        s_set = set(x.get('side') for x in t_trades)
        if 'BUY' in s_set and 'SELL' in s_set:
            same_token_buy_and_sell += 1

    # Timing / Cadence analysis
    timestamps = sorted([int(t.get('timestamp', 0)) for t in trades if t.get('timestamp')], reverse=True)
    deltas = [timestamps[i] - timestamps[i+1] for i in range(len(timestamps)-1)]
    same_sec_ratio = sum(1 for d in deltas if d == 0) / len(deltas) if deltas else 0
    under_5s_ratio = sum(1 for d in deltas if d <= 5) / len(deltas) if deltas else 0
    median_delta = statistics.median(deltas) if deltas else 0

    # Open positions analysis: check if holding opposite sides simultaneously in open positions
    open_by_cond = defaultdict(list)
    open_by_event = defaultdict(list)
    total_open_val = 0.0
    total_open_cost = 0.0
    total_open_fees = 0.0
    neg_risk_open = 0
    for p in open_positions:
        open_by_cond[p.get('condition_id')].append(p)
        open_by_event[p.get('event_id')].append(p)
        total_open_val += float(p.get('current_value') or 0)
        total_open_cost += float(p.get('entry_cost_usdc') or 0)
        total_open_fees += float(p.get('entry_fees_usdc') or 0)
        if p.get('negative_risk'):
            neg_risk_open += 1

    hedged_open_conditions = sum(1 for cid, plist in open_by_cond.items() if len(plist) > 1)
    multi_leg_open_events = sum(1 for eid, plist in open_by_event.items() if len(plist) > 1)

    # Holding time on closed wins & losses
    hold_durations_hours = []
    for p in closed_wins + closed_losses:
        t0 = p.get('first_entry_at')
        t1 = p.get('last_event_at')
        if t0 and t1 and t1 >= t0:
            hold_durations_hours.append((t1 - t0) / 3600.0)

    def summarize_pos(p):
        t0 = p.get('first_entry_at') or 0
        t1 = p.get('last_event_at') or 0
        hold_h = round((t1 - t0) / 3600.0, 2) if (t0 and t1 and t1 >= t0) else None
        return {
            'title': p.get('title'),
            'outcome': p.get('outcome'),
            'avg_price': round(float(p.get('avg_price') or 0), 4),
            'current_price': round(float(p.get('current_price') or 0), 4),
            'total_size': round(float(p.get('total_size') or 0), 1),
            'current_size': round(float(p.get('current_size') or 0), 1),
            'current_value': round(float(p.get('current_value') or 0), 2),
            'entry_cost_usdc': round(float(p.get('entry_cost_usdc') or 0), 2),
            'entry_fees_usdc': round(float(p.get('entry_fees_usdc') or 0), 2),
            'realized_pnl': round(float(p.get('realized_pnl') or 0), 2),
            'unrealized_pnl': round(float(p.get('unrealized_pnl') or 0), 2),
            'total_pnl': round(float(p.get('total_pnl') or 0), 2),
            'negative_risk': p.get('negative_risk'),
            'hold_hours': hold_h
        }

    return {
        'name': name,
        'wallet': wallet,
        'stats_summary': {
            'join_date': stats_data.get('join_date'),
            'trades_markets': stats_data.get('trades'),
            'trade_count_fills': all_time.get('trade_count'),
            'biggest_win': stats_data.get('biggest_win'),
            'volume_shares': all_time.get('volume'),
            'volume_usdc': all_time.get('volume_usdc'),
            'economic_pnl': all_time.get('economic_pnl'),
            'realized_market_pnl': all_time.get('realized_market_pnl'),
            'realized_combo_pnl': all_time.get('realized_combo_pnl'),
            'unrealized_pnl': all_time.get('unrealized_pnl'),
            'maker_rebate': all_time.get('maker_rebate'),
            'taker_rebate': all_time.get('taker_rebate'),
            'reward_income': all_time.get('reward_income'),
            'yield_income': all_time.get('yield_income'),
            'fees_paid': all_time.get('fees_paid'),
        },
        'activity_sample_size': len(activities),
        'activity_types': dict(act_types),
        'trade_sides': dict(sides),
        'top_outcomes': dict(outcomes.most_common(8)),
        'price_bands': dict(sorted(price_bands.items())),
        'avg_trade_price': round(statistics.mean(prices), 4) if prices else 0,
        'median_trade_price': round(statistics.median(prices), 4) if prices else 0,
        'avg_usdc_size': round(statistics.mean(usdc_sizes), 2) if usdc_sizes else 0,
        'median_usdc_size': round(statistics.median(usdc_sizes), 2) if usdc_sizes else 0,
        'max_usdc_size_sample': round(max(usdc_sizes), 2) if usdc_sizes else 0,
        'categories_by_count': dict(categories.most_common()),
        'categories_by_usdc': {k: round(v, 2) for k, v in sorted(category_usdc.items(), key=lambda x: x[1], reverse=True)},
        'hedging_and_arb': {
            'unique_conditions_in_sample': len(by_condition),
            'dual_outcome_conditions': dual_outcome_conditions,
            'dual_outcome_pct': round(dual_outcome_conditions / len(by_condition) * 100, 1) if by_condition else 0,
            'arb_sum_lt_1_conditions': arb_sum_lt_1_conditions,
            'unique_tokens_in_sample': len(by_token),
            'same_token_buy_and_sell': same_token_buy_and_sell,
            'same_token_flip_pct': round(same_token_buy_and_sell / len(by_token) * 100, 1) if by_token else 0,
            'dual_examples': dual_examples,
        },
        'timing_microstructure': {
            'same_second_trades_pct': round(same_sec_ratio * 100, 1),
            'under_5s_trades_pct': round(under_5s_ratio * 100, 1),
            'median_seconds_between_trades': median_delta,
            'multi_fill_tx_pct': round(sum(1 for c in tx_hashes.values() if c > 1) / len(tx_hashes) * 100, 1) if tx_hashes else 0,
        },
        'open_portfolio_profile': {
            'open_positions_fetched': len(open_positions),
            'total_open_value_usdc': round(total_open_val, 2),
            'total_open_cost_usdc': round(total_open_cost, 2),
            'total_open_entry_fees_usdc': round(total_open_fees, 2),
            'effective_open_fee_rate_bps': round(total_open_fees / total_open_cost * 10000, 2) if total_open_cost > 0 else 0,
            'neg_risk_open_count': neg_risk_open,
            'hedged_open_conditions': hedged_open_conditions,
            'multi_leg_open_events': multi_leg_open_events,
            'top_open_positions': [summarize_pos(p) for p in open_positions[:8]],
        },
        'closed_portfolio_profile': {
            'median_hold_hours': round(statistics.median(hold_durations_hours), 2) if hold_durations_hours else 0,
            'avg_hold_hours': round(statistics.mean(hold_durations_hours), 2) if hold_durations_hours else 0,
            'top_closed_wins': [summarize_pos(p) for p in closed_wins[:6]],
            'top_closed_losses': [summarize_pos(p) for p in closed_losses[:5]],
        }
    }

def main():
    results = []
    for name, wallet in TARGET_WALLETS:
        res = analyze_wallet(name, wallet)
        results.append(res)
        time.sleep(0.3)
    with open('C:/Users/enfoc/.gemini/antigravity/scratch/forensic_strategies_output.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print("Forensic strategy analysis saved to forensic_strategies_output.json!")

if __name__ == '__main__':
    main()
