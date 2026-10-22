import urllib.request
import json
import time
import statistics
from collections import defaultdict, Counter

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

# Wallets from Batch 1 and Batch 2 to EXCLUDE
ALREADY_ANALYZED = {
    # Batch 1 (8 wallets)
    "0xf0318c32136c2db7fec88b84869aee6a1106c80c".lower(),  # BreakTheBank
    "0x7c37b52eb226bcb9411375ec48b0169663fb6aeb".lower(),  # Diabolical-Prize
    "0x5268527977f700f9bf9b6d5cd843859e4e70135d".lower(),  # HomeRunHazard
    "0xdaef2be2a19ad331737d06545f85615b094554e9".lower(),  # PEYZ-BIGGEST-FAN
    "0x2005d16a84ceefa912d4e380cd32e7ff827875ea".lower(),  # RN1
    "0xf68a281980f8c13828e84e147e3822381d6e5b1b".lower(),  # Nooserac
    "0x21f333307ac6d2e65ac82f014b3dd2b64cbc35e3".lower(),  # hi774c
    "0xb35f674af4603c9602dfbf39564087e94897cf4c".lower(),  # calculate10

    # Batch 2 Top 10 (and inspected)
    "0x4f1d5ae26fc31472966e951af3183308736d8de2".lower(),  # e46m3
    "0x511f9c771449162349795d17becf8b37031acbe1".lower(),  # Bigggggggg
    "0x2c335066fe58fe9237c3d3dc7b275c2a034a0563".lower(),  # 0x2c3350...
    "0x076daa87c4fe1a85402a9b6b8e0a866224388d4c".lower(),  # omnibus-076daa
    "0xd38b71f3e8ed1af71983e5c309eac3dfa9b35029".lower(),  # primm
    "0xbca08c1bc204a34f2fddbe47b438b9bd42ac9705".lower(),  # justaluckydude
    "0x924379a79c64b77ad5816ad362122a5f6228658e".lower(),  # Kch-Temp
    "0xcdcccd0f2d86e450d973da415ad2430e5cc7935a".lower(),  # joseph00677
    "0x7ad71d79a3bb90d0a87a06500fa0fe11663842aa".lower(),  # theowalcott
    "0x5bfe9469c7c4035325024c846bc530c9d29e3258".lower(),  # 01258787xy48487484545122
}

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
    if any(k in s for k in ['bitcoin', 'btc', 'ethereum', 'eth', 'solana', 'sol', 'xrp', 'doge', 'crypto', 'up or down', 'above', 'dip']):
        return 'Crypto & Short-Term Price'
    if any(k in s for k in ['temperature', 'weather', 'highest temperature', '°f', '°c', 'nyc', 'chicago', 'london', 'rain', 'snow']):
        return 'Weather & Climate'
    if any(k in s for k in ['tweet', 'elon musk', 'truth social', 'say ', 'mention', 'post']):
        return 'Social Media & Tweets'
    if any(k in s for k in ['lol-', 'lol:', 'league of legends', 'dota', 'valorant', 'cs2', 'counter-strike', 'esports']):
        return 'Esports'
    if any(k in s for k in ['spread:', 'spread', 'points spread', 'handicap']):
        return 'US Sports: Spreads'
    if any(k in s for k in ['o/u', 'over/under', 'total points', 'total games', 'total goals', 'total corners']):
        return 'Sports: Totals / Props'
    if any(k in s for k in ['atp', 'wta', 'open', 'qualif', 'tennis', 'challenger', 'set 1', 'game ']):
        return 'Tennis'
    if any(k in s for k in ['premier league', 'la liga', 'serie a', 'bundesliga', 'champions league', 'copa', 'fc ', ' vs ']):
        return 'Global Soccer'
    if any(k in s for k in ['presidential', 'election', 'senate', 'governor', 'trump', 'kamala', 'biden', 'democrat', 'republican', 'prime minister', 'parliament']):
        return 'Politics & Elections'
    if any(k in s for k in ['fed', 'interest rate', 'bps', 'rate cut', 'inflation', 'cpi', 'gdp', 'recession', 'central bank', 'ecb', 'boj', 'snb']):
        return 'Macro Economics & Fed'
    if any(k in s for k in ['israel', 'iran', 'ukraine', 'russia', 'war', 'ceasefire', 'missile', 'nuclear', 'taiwan', 'china', 'gaza', 'hezbollah']):
        return 'Geopolitics & Conflict'
    return 'Other / General'

def deep_inspect_wallet(name, wallet):
    stats_raw = fetch_json(f"https://data-api.polymarket.com/v2/user-stats?user={wallet}") or {}
    stats_data = stats_raw.get('data', {}) or {}
    all_time = stats_data.get('all_time_pnl', {}) or {}

    # Fetch 7d PnL curve (3h fidelity)
    pnl_res = fetch_json(f"https://data-api.polymarket.com/v2/user-pnl?user={wallet}&interval=1w&fidelity=3h") or {}
    pts = ((pnl_res.get('data') or {}).get('points')) or []
    pnl_7d_growth = 0.0
    win_intervals = 0
    max_dd = 0.0
    peak = -1e9
    if pts:
        p0 = float(pts[0].get('economic_pnl') or pts[0].get('realized_pnl') or 0)
        p1 = float(pts[-1].get('economic_pnl') or pts[-1].get('realized_pnl') or 0)
        pnl_7d_growth = p1 - p0
        peak = p0
        for i in range(1, len(pts)):
            prev = float(pts[i-1].get('economic_pnl') or pts[i-1].get('realized_pnl') or 0)
            curr = float(pts[i].get('economic_pnl') or pts[i].get('realized_pnl') or 0)
            if curr >= prev:
                win_intervals += 1
            if curr > peak:
                peak = curr
            dd = peak - curr
            if dd > max_dd:
                max_dd = dd
        win_ratio = round((win_intervals / (len(pts)-1)) * 100, 1) if len(pts) > 1 else 0.0
    else:
        win_ratio = 0.0

    econ_pnl = (
        float(all_time.get('realized_market_pnl') or 0) +
        float(all_time.get('realized_combo_pnl') or 0) +
        float(all_time.get('maker_rebate') or 0) +
        float(all_time.get('taker_rebate') or 0) +
        float(all_time.get('reward_income') or 0) +
        float(all_time.get('yield_income') or 0) +
        float(all_time.get('fees_paid') or 0)
    )

    # Fetch 500 recent activities
    act_raw = fetch_json(f"https://data-api.polymarket.com/v2/activity?user={wallet}&limit=500") or {}
    activities = act_raw.get('data') or []
    act_types = Counter(a.get('type') for a in activities)

    trades = [a for a in activities if a.get('type') == 'TRADE']
    trades_fills = stats_data.get('trades', len(trades))
    sides = Counter(t.get('side') for t in trades)

    prices = []
    usdc_sizes = []
    categories = Counter()
    category_usdc = defaultdict(float)
    by_cond = defaultdict(list)
    by_token = defaultdict(list)

    for t in trades:
        px = float(t.get('price') or 0)
        sz = float(t.get('size') or 0)
        usdc = px * sz
        if px > 0:
            prices.append(px)
        if usdc > 0:
            usdc_sizes.append(usdc)
        cat = classify_market(t.get('title', ''), t.get('slug', ''), t.get('eventSlug', ''))
        categories[cat] += 1
        category_usdc[cat] += usdc

        cid = t.get('conditionId')
        tid = t.get('tokenId')
        if cid:
            by_cond[cid].append(t)
        if tid:
            by_token[tid].append(t)

    dual_conds = 0
    arb_lt_1 = 0
    dual_examples = []
    for cid, tlist in by_cond.items():
        tids = {x.get('tokenId') for x in tlist if x.get('tokenId')}
        if len(tids) >= 2:
            dual_conds += 1
            by_t = defaultdict(list)
            for x in tlist:
                by_t[x.get('tokenId')].append(x)
            v0 = sum(float(x.get('price') or 0)*float(x.get('size') or 0) for x in list(by_t.values())[0]) / max(sum(float(x.get('size') or 0) for x in list(by_t.values())[0]), 0.001)
            v1 = sum(float(x.get('price') or 0)*float(x.get('size') or 0) for x in list(by_t.values())[1]) / max(sum(float(x.get('size') or 0) for x in list(by_t.values())[1]), 0.001)
            if v0 + v1 < 1.0:
                arb_lt_1 += 1
                if len(dual_examples) < 3:
                    dual_examples.append({
                        'title': tlist[0].get('title'),
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
    with open('C:/Users/enfoc/.gemini/antigravity/scratch/batch3_raw_candidates.json', 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    # Filter top candidates
    # We want candidates with distinct profiles:
    # 1. High 1d/7d PnL (> $35,000)
    # 2. Or very high volume (> $200,000)
    filtered = []
    for c in candidates:
        w = c['wallet'].lower()
        if w in ALREADY_ANALYZED:
            continue
        filtered.append(c)

    print(f"Total filtered candidate wallets to inspect: {len(filtered)}")
    # Take top 22 candidates
    targets = filtered[:22]
    
    results = []
    for idx, c in enumerate(targets, 1):
        wallet = c['wallet']
        name = c['name']
        print(f"[{idx}/{len(targets)}] Deep inspecting {name} ({wallet[:10]}...)...")
        res = deep_inspect_wallet(name, wallet)
        if res:
            results.append(res)
        time.sleep(0.3)

    # Sort results by 7d growth and economic pnl
    results.sort(key=lambda x: (x['pnl_7d_growth'] * 1.5 + x['economic_pnl']), reverse=True)
    
    output_path = 'C:/Users/enfoc/.gemini/antigravity/scratch/forensic_batch3_wallets.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    print(f"\nSuccessfully saved {len(results)} deep-inspected Batch 3 wallets to {output_path}!")

if __name__ == '__main__':
    main()
