import urllib.request
import json
import time
import math
from typing import List, Dict, Any

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def fetch_json(url: str, retries: int = 3, delay: float = 0.5) -> Any:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(delay)

def get_leaderboards() -> Dict[str, List[Dict[str, Any]]]:
    endpoints = {
        '1d_pnl': 'https://data-api.polymarket.com/v1/leaderboard?window=1d&limit=50&orderBy=pnl',
        '1d_vol': 'https://data-api.polymarket.com/v1/leaderboard?window=1d&limit=50&orderBy=vol',
        '7d_pnl': 'https://data-api.polymarket.com/v1/leaderboard?window=7d&limit=50&orderBy=pnl',
        '7d_vol': 'https://data-api.polymarket.com/v1/leaderboard?window=7d&limit=50&orderBy=vol',
        '30d_pnl': 'https://data-api.polymarket.com/v1/leaderboard?window=30d&limit=50&orderBy=pnl',
        '30d_vol': 'https://data-api.polymarket.com/v1/leaderboard?window=30d&limit=50&orderBy=vol',
    }
    
    data = {}
    for name, url in endpoints.items():
        print(f"Fetching leaderboard {name}...")
        res = fetch_json(url)
        data[name] = res or []
        time.sleep(0.2)
    return data

def analyze():
    leaderboards = get_leaderboards()
    
    wallet_map = {}
    for lb_name, rows in leaderboards.items():
        for row in rows:
            w = row.get('proxyWallet', '').lower()
            if not w:
                continue
            if w not in wallet_map:
                wallet_map[w] = {
                    'proxyWallet': w,
                    'userName': row.get('userName') or row.get('xUsername') or w[:10],
                    'verified': row.get('verifiedBadge', False),
                    'appearances': [],
                    'pnl_1d': 0.0,
                    'vol_1d': 0.0,
                    'pnl_7d': 0.0,
                    'vol_7d': 0.0,
                    'pnl_30d': 0.0,
                    'vol_30d': 0.0,
                }
            wallet_map[w]['appearances'].append(lb_name)
            pnl = float(row.get('pnl') or 0.0)
            vol = float(row.get('vol') or 0.0)
            if '1d' in lb_name:
                wallet_map[w]['pnl_1d'] = max(wallet_map[w]['pnl_1d'], pnl)
                wallet_map[w]['vol_1d'] = max(wallet_map[w]['vol_1d'], vol)
            if '7d' in lb_name:
                wallet_map[w]['pnl_7d'] = max(wallet_map[w]['pnl_7d'], pnl)
                wallet_map[w]['vol_7d'] = max(wallet_map[w]['vol_7d'], vol)
            if '30d' in lb_name:
                wallet_map[w]['pnl_30d'] = max(wallet_map[w]['pnl_30d'], pnl)
                wallet_map[w]['vol_30d'] = max(wallet_map[w]['vol_30d'], vol)

    print(f"Total unique wallets across leaderboards: {len(wallet_map)}")
    
    # Filter candidates with positive PnL and active volume
    candidates = [
        w for w in wallet_map.values()
        if (w['pnl_7d'] > 1000 or w['pnl_30d'] > 5000 or w['pnl_1d'] > 500)
    ]
    
    # Sort candidates by a preliminary score: combination of 7d pnl, 30d pnl, and activity
    candidates.sort(key=lambda x: (x['pnl_7d'] + x['pnl_1d'] * 2 + x['pnl_30d'] * 0.5), reverse=True)
    top_candidates = candidates[:35]
    
    print(f"Analyzing deep metrics for top {len(top_candidates)} candidate wallets...")
    
    enriched = []
    for idx, c in enumerate(top_candidates):
        w = c['proxyWallet']
        print(f"[{idx+1}/{len(top_candidates)}] Deep inspection for {c['userName']} ({w[:8]}...)...")
        
        # 1. Fetch user-stats
        stats_url = f"https://data-api.polymarket.com/v2/user-stats?user={w}"
        stats_res = fetch_json(stats_url)
        stats_data = (stats_res or {}).get('data', {})
        all_time = stats_data.get('all_time_pnl', {}) or {}
        
        trade_count = all_time.get('trade_count', 0) or stats_data.get('trades', 0)
        total_pnl = all_time.get('economic_pnl', 0) or all_time.get('realized_pnl', 0) or 0
        total_volume = all_time.get('volume', 0) or all_time.get('volume_usdc', 0) or 0
        biggest_win = stats_data.get('biggest_win', 0) or 0
        join_date = stats_data.get('join_date', 0) or 0
        
        # 2. Fetch 1w PnL curve for consistency & acceleration
        pnl_url = f"https://data-api.polymarket.com/v2/user-pnl?user={w}&interval=1w&fidelity=3h"
        pnl_res = fetch_json(pnl_url)
        pnl_points = ((pnl_res or {}).get('data', {}) or {}).get('points', []) or []
        
        # Calculate consistency and acceleration metrics
        consistency_score = 0.0
        pnl_growth_7d = 0.0
        max_drawdown = 0.0
        up_intervals = 0
        total_intervals = 0
        
        if len(pnl_points) >= 2:
            start_pnl = pnl_points[0].get('economic_pnl', 0) or pnl_points[0].get('realized_pnl', 0) or 0
            end_pnl = pnl_points[-1].get('economic_pnl', 0) or pnl_points[-1].get('realized_pnl', 0) or 0
            pnl_growth_7d = end_pnl - start_pnl
            
            # Check drawdowns and consistency across 3h intervals
            peak = -1e12
            for i in range(1, len(pnl_points)):
                prev = pnl_points[i-1].get('economic_pnl', 0) or pnl_points[i-1].get('realized_pnl', 0) or 0
                curr = pnl_points[i].get('economic_pnl', 0) or pnl_points[i].get('realized_pnl', 0) or 0
                diff = curr - prev
                if diff > 0:
                    up_intervals += 1
                total_intervals += 1
                
                if curr > peak:
                    peak = curr
                dd = peak - curr
                if dd > max_drawdown:
                    max_drawdown = dd
            
            if total_intervals > 0:
                win_interval_ratio = up_intervals / total_intervals
            else:
                win_interval_ratio = 0
        else:
            win_interval_ratio = 0
            pnl_growth_7d = c['pnl_7d']
        
        # 3. Fetch active positions
        pos_url = f"https://data-api.polymarket.com/v2/positions?user={w}&status=OPEN&limit=5&sort_by=CURRENT_VALUE&sort_direction=DESC"
        pos_res = fetch_json(pos_url)
        positions = pos_res if isinstance(pos_res, list) else ((pos_res.get('data', []) if isinstance(pos_res, dict) else []))
        pos_summaries = []
        if isinstance(positions, list):
            for p in positions[:4]:
                if isinstance(p, dict):
                    title = p.get('title') or p.get('market', {}).get('question') or p.get('conditionId', '')[:10]
                    outcome = p.get('outcome', '')
                    val = p.get('currentValue') or p.get('size', 0)
                    pos_summaries.append(f"{title} ({outcome}): ${val:,.0f}" if isinstance(val, (int, float)) else f"{title} ({outcome})")
        
        # Calculate acceleration score:
        # High trades (>50), positive 7d growth, high interval win ratio, low drawdown relative to profit
        enriched.append({
            'userName': c['userName'],
            'proxyWallet': w,
            'url': f"https://polymarket.com/profile/{w}",
            'pnl_1d': c['pnl_1d'],
            'pnl_7d': c['pnl_7d'],
            'pnl_30d': c['pnl_30d'],
            'pnl_growth_7d_curve': pnl_growth_7d,
            'total_pnl': total_pnl,
            'total_volume': total_volume,
            'trade_count': trade_count,
            'trades_stat': stats_data.get('trades', 0),
            'biggest_win': biggest_win,
            'win_interval_ratio': win_interval_ratio,
            'max_drawdown': max_drawdown,
            'positions': pos_summaries,
            'points_count': len(pnl_points)
        })
        time.sleep(0.15)
        
    # Write enriched output to json
    with open('C:/Users/enfoc/.gemini/antigravity/scratch/polymarket_wallets_analyzed.json', 'w', encoding='utf-8') as f:
        json.dump(enriched, f, indent=2)
        
    print("Enrichment complete! Saved to polymarket_wallets_analyzed.json")

if __name__ == '__main__':
    analyze()
