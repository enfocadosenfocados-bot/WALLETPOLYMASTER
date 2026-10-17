import urllib.request
import json
import time
import statistics
from collections import defaultdict, Counter

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json'
}

ALREADY_ANALYZED = {
    "0xf0318c32136c2db7fec88b84869aee6a1106c80c",  # BreakTheBank
    "0x7c37b52eb226bcb9411375ec48b0169663fb6aeb",  # Diabolical-Prize
    "0x5268527977f700f9bf9b6d5cd843859e4e70135d",  # HomeRunHazard
    "0xdaef2be2a19ad331737d06545f85615b094554e9",  # PEYZ-BIGGEST-FAN
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea",  # RN1
    "0xf68a281980f8c13828e84e147e3822381d6e5b1b",  # Nooserac
    "0x21f333307ac6d2e65ac82f014b3dd2b64cbc35e3",  # hi774c
    "0xb35f674af4603c9602dfbf39564087e94897cf4c",  # calculate10
}

# Wallets from the 30D Profit Leaderboard DOM + our first 35-wallet scan
EXTRA_30D_PROFIT_LEADERS = [
    ("joseph00677", "0xcdcccd0f2d86e450d973da415ad2430e5cc7935a"),
    ("e46m3", "0x4f1d5ae26fc31472966e951af3183308736d8de2"),
    ("Kch-Temp", "0x924379a79c64b77ad5816ad362122a5f6228658e"),
    ("halvanicus", "0x63cf8544631c31e9fcea0b02141dd24d01d6e4d0"),
    ("UpTheBlues", "0x2a69660046d7acc4ab204d7cc5ba78b0776cd2f7"),
    ("mooseborzoii", "0x1f3a646ce5cbe2c70270e7a46161d89b7c7b895d"),
    ("omnibus-076daa", "0x076daa87c4fe1a85402a9b6b8e0a866224388d4c"),
    ("juice-fruit", "0x5fdd66ffd0325d4e8d1d86fbec50caa31770a747"),
    ("totoro3miyazaki", "0x0f6f76ced62a911bccef92f50faaff143854d977"),
    ("primm", "0xd38b71f3e8ed1af71983e5c309eac3dfa9b35029"),
    ("anoin123", "0x96489abcb9f583d6835c8ef95ffc923d05a86825"),
    ("Bigggggggg", "0x511f9c771449162349795d17becf8b37031acbe1"),
    ("theowalcott", "0x7ad71d79a3bb90d0a87a06500fa0fe11663842aa"),
]

def fetch_json(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=12) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(0.3)

def classify_market(title, slug, event_slug):
    s = f"{title} {slug} {event_slug}".lower()
    if any(k in s for k in ['bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'xrp', 'doge', 'crypto', 'up or down']):
        return 'Crypto & Short-Term Price'
    if any(k in s for k in ['temperature', 'weather', 'highest temperature', '°f', '°c', 'nyc', 'chicago', 'london']):
        return 'Weather & Temperature'
    if any(k in s for k in ['tweet', 'elon musk', 'truth social', 'say ', 'mention']):
        return 'Culture: Tweets & Mentions'
    if any(k in s for k in ['lol-', 'lol:', 'league of legends', 'dota', 'valorant', 'cs2', 'counter-strike', 'esports']):
        return 'Esports: LoL/Dota/Val/CS2'
    if any(k in s for k in ['nfl', 'nba', 'mlb', 'nhl', 'ncaa', 'cfb', 'cbb', 'spread:', 'o/u', 'over', 'under']):
        if 'spread:' in s:
            return 'US Sports: Spreads'
        elif 'o/u' in s or 'over/under' in s:
            return 'US Sports: Totals (O/U)'
        else:
            return 'US Sports: Moneyline / Futures'
    if any(k in s for k in ['epl', 'ucl', 'fc ', 'vs.', 'draw', 'fifa', 'fifwc', 'la liga', 'serie a', 'bundesliga', 'soccer']):
        if 'draw' in s:
            return 'Soccer: Draw Markets'
        else:
            return 'Soccer: Match Winner / Futures'
    if any(k in s for k in ['atp', 'wta', 'tennis', 'open']):
        return 'Tennis'
    if any(k in s for k in ['senate', 'house', 'election', 'president', 'governor', 'republican', 'democratic', 'trump', 'vance', 'netanyahu', 'iran', 'israel', 'ukraine', 'russia', 'ceasefire', 'prime minister', 'fed ', 'interest rate']):
        return 'Politics, Macro & Geopolitics'
    return 'Other / Props'

def deep_inspect_wallet(name, wallet):
    stats_raw = fetch_json(f"https://data-api.polymarket.com/v2/user-stats?user={wallet}") or {}
    stats_data = stats_raw.get('data', {}) or {}
    all_time = stats_data.get('all_time_pnl', {}) or {}

    trades_fills = int(all_time.get('trade_count') or stats_data.get('trades') or 0)
    econ_pnl = float(all_time.get('economic_pnl') or all_time.get('realized_pnl') or 0.0)
    if trades_fills < 100 or econ_pnl < 50000:
        return None

    # Fetch 7d PnL curve (3h fidelity)
    pnl_res = fetch_json(f"https://data-api.polymarket.com/v2/user-pnl?user={wallet}&interval=1w&fidelity=3h") or {}
    pts = ((pnl_res.get('data') or {}).get('points')) or []
    pnl_7d_growth = 0.0
    win_intervals = 0
    total_intervals = 0
    max_dd = 0.0
    if len(pts) >= 2:
        p0 = float(pts[0].get('economic_pnl') or pts[0].get('realized_pnl') or 0)
        p1 = float(pts[-1].get('economic_pnl') or pts[-1].get('realized_pnl') or 0)
        pnl_7d_growth = p1 - p0
        peak = -1e12
        for i in range(1, len(pts)):
            prev = float(pts[i-1].get('economic_pnl') or pts[i-1].get('realized_pnl') or 0)
            curr = float(pts[i].get('economic_pnl') or pts[i].get('realized_pnl') or 0)
            if curr - prev > 0:
                win_intervals += 1
            total_intervals += 1
            if curr > peak:
                peak = curr
            if peak - curr > max_dd:
                max_dd = peak - curr
    win_ratio = round(win_intervals / total_intervals * 100, 1) if total_intervals > 0 else 0.0

    # Fetch 500 recent activities
    act_raw = fetch_json(f"https://data-api.polymarket.com/v2/activity?user={wallet}&limit=500") or {}
    activities = act_raw.get('data') or []
    act_types = Counter(a.get('type') for a in activities)
    trades = [a for a in activities if a.get('type') == 'TRADE']
    sides = Counter(t.get('side') for t in trades)

    prices = [float(t.get('price') or 0) for t in trades]
    usdc_sizes = [float(t.get('usdc_size') or 0) for t in trades]
    categories = Counter()
    category_usdc = defaultdict(float)
    by_cond = defaultdict(list)
    by_token = defaultdict(list)

    for t in trades:
        cat = classify_market(t.get('title', ''), t.get('slug', ''), t.get('event_slug', ''))
        categories[cat] += 1
        category_usdc[cat] += float(t.get('usdc_size') or 0)
        if t.get('condition_id'):
            by_cond[t.get('condition_id')].append(t)
        if t.get('token_id'):
            by_token[t.get('token_id')].append(t)

    dual_conds = 0
    arb_lt_1 = 0
    dual_examples = []
    for cid, c_trades in by_cond.items():
        idxs = set(x.get('outcome_index') for x in c_trades if x.get('outcome_index') is not None)
        if len(idxs) > 1:
            dual_conds += 1
            b0 = [x for x in c_trades if x.get('outcome_index') == 0 and x.get('side') == 'BUY']
            b1 = [x for x in c_trades if x.get('outcome_index') == 1 and x.get('side') == 'BUY']
            if b0 and b1:
                s0 = sum(float(x.get('size', 0)) for x in b0)
                s1 = sum(float(x.get('size', 0)) for x in b1)
                v0 = sum(float(x.get('usdc_size', 0)) for x in b0) / s0 if s0 > 0 else 0
                v1 = sum(float(x.get('usdc_size', 0)) for x in b1) / s1 if s1 > 0 else 0
                if 0 < v0 + v1 < 1.0:
                    arb_lt_1 += 1
                if len(dual_examples) < 3:
                    dual_examples.append({
                        'title': c_trades[0].get('title'),
                        'vwap0': round(v0, 3),
                        'vwap1': round(v1, 3),
                        'sum_vwap': round(v0 + v1, 3)
                    })

    same_token_flips = sum(1 for tid, tl in by_token.items() if 'BUY' in {x.get('side') for x in tl} and 'SELL' in {x.get('side') for x in tl})

    timestamps = sorted([int(t.get('timestamp', 0)) for t in trades if t.get('timestamp')], reverse=True)
    deltas = [timestamps[i] - timestamps[i+1] for i in range(len(timestamps)-1)]
    under_5s_pct = round(sum(1 for d in deltas if d <= 5) / len(deltas) * 100, 1) if deltas else 0.0
    med_delta = statistics.median(deltas) if deltas else 0

    open_raw = fetch_json(f"https://data-api.polymarket.com/v2/positions?user={wallet}&status=OPEN&limit=10&sort_by=CURRENT_VALUE&sort_direction=DESC") or {}
    open_pos = open_raw.get('data') or []

    wins_raw = fetch_json(f"https://data-api.polymarket.com/v2/positions?user={wallet}&status=CLOSED&limit=5&sort_by=REALIZED_PNL&sort_direction=DESC") or {}
    closed_wins = wins_raw.get('data') or []

    return {
        'name': name,
        'wallet': wallet,
        'economic_pnl': round(econ_pnl, 2),
        'realized_market_pnl': round(float(all_time.get('realized_market_pnl') or 0), 2),
        'realized_combo_pnl': round(float(all_time.get('realized_combo_pnl') or 0), 2),
        'pnl_7d_growth': round(pnl_7d_growth, 2),
        'win_interval_pct': win_ratio,
        'max_dd_7d': round(max_dd, 2),
        'volume_usdc': round(float(all_time.get('volume_usdc') or 0), 2),
        'trade_count_fills': trades_fills,
        'trades_markets': stats_data.get('trades', 0),
        'maker_rebate': round(float(all_time.get('maker_rebate') or 0), 2),
        'taker_rebate': round(float(all_time.get('taker_rebate') or 0), 2),
        'reward_income': round(float(all_time.get('reward_income') or 0), 2),
        'yield_income': round(float(all_time.get('yield_income') or 0), 2),
        'fees_paid': round(float(all_time.get('fees_paid') or 0), 2),
        'activity_types': dict(act_types),
        'trade_sides': dict(sides),
        'avg_price': round(statistics.mean(prices), 3) if prices else 0,
        'median_price': round(statistics.median(prices), 3) if prices else 0,
        'avg_usdc': round(statistics.mean(usdc_sizes), 2) if usdc_sizes else 0,
        'median_usdc': round(statistics.median(usdc_sizes), 2) if usdc_sizes else 0,
        'categories_by_count': dict(categories.most_common(4)),
        'categories_by_usdc': {k: round(v, 0) for k, v in sorted(category_usdc.items(), key=lambda x: x[1], reverse=True)[:4]},
        'dual_outcome_pct': round(dual_conds / len(by_cond) * 100, 1) if by_cond else 0.0,
        'arb_lt_1_count': arb_lt_1,
        'same_token_flip_pct': round(same_token_flips / len(by_token) * 100, 1) if by_token else 0.0,
        'dual_examples': dual_examples,
        'under_5s_pct': under_5s_pct,
        'med_delta_s': med_delta,
        'top_open': [
            {
                'title': p.get('title'),
                'outcome': p.get('outcome'),
                'avg_price': round(float(p.get('avg_price') or 0), 3),
                'cur_price': round(float(p.get('current_price') or 0), 3),
                'val': round(float(p.get('current_value') or 0), 0),
                'fee': round(float(p.get('entry_fees_usdc') or 0), 2)
            } for p in open_pos[:4]
        ],
        'top_wins': [
            {
                'title': p.get('title'),
                'outcome': p.get('outcome'),
                'avg_price': round(float(p.get('avg_price') or 0), 3),
                'pnl': round(float(p.get('realized_pnl') or 0), 0),
                'fee': round(float(p.get('entry_fees_usdc') or 0), 2)
            } for p in closed_wins[:4]
        ]
    }

def main():
    with open('C:/Users/enfoc/.gemini/antigravity/scratch/polymarket_wallets_analyzed.json', 'r', encoding='utf-8') as f:
        first_batch = json.load(f)

    candidate_pool = {}
    for name, w in EXTRA_30D_PROFIT_LEADERS:
        if w.lower() not in ALREADY_ANALYZED:
            candidate_pool[w.lower()] = name

    for item in first_batch:
        w = item['proxyWallet'].lower()
        if w not in ALREADY_ANALYZED and w not in candidate_pool:
            if item.get('total_pnl', 0) > 100000 and max(item.get('trade_count', 0), item.get('trades_stat', 0)) >= 500:
                candidate_pool[w] = item['userName']

    print(f"Total new candidate wallets to inspect: {len(candidate_pool)}")
    results = []
    for idx, (wallet, name) in enumerate(candidate_pool.items(), 1):
        print(f"[{idx}/{len(candidate_pool)}] Inspecting {name} ({wallet[:10]}...)...")
        res = deep_inspect_wallet(name, wallet)
        if res:
            results.append(res)
        time.sleep(0.2)

    results.sort(key=lambda x: (x['pnl_7d_growth'] * 2 + x['economic_pnl']), reverse=True)
    with open('C:/Users/enfoc/.gemini/antigravity/scratch/forensic_batch2_wallets.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"Saved {len(results)} deep-inspected new wallets to forensic_batch2_wallets.json!")

if __name__ == '__main__':
    main()
