import json

with open('C:/Users/enfoc/.gemini/antigravity/scratch/polymarket_wallets_analyzed.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

scored = []
for w in data:
    trades = max(w.get('trade_count', 0), w.get('trades_stat', 0))
    pnl_7d = w.get('pnl_7d', 0)
    pnl_1d = w.get('pnl_1d', 0)
    pnl_30d = w.get('pnl_30d', 0)
    pnl_curve = w.get('pnl_growth_7d_curve', 0)
    total_pnl = w.get('total_pnl', 0)
    win_ratio = w.get('win_interval_ratio', 0)
    max_dd = w.get('max_drawdown', 0)
    
    if trades < 30:
        continue
    if pnl_7d <= 0 and pnl_curve <= 0 and pnl_1d <= 0 and pnl_30d <= 0:
        continue

    # Growth acceleration score
    # Prioritizes wallets with high trades and strong positive momentum
    trade_factor = 1.0 + min(trades, 10000) / 2000.0
    consistency_factor = 0.5 + win_ratio
    momentum = max(0, pnl_1d) * 2.5 + max(0, pnl_7d) * 1.5 + max(0, pnl_curve)
    
    score = momentum * trade_factor * consistency_factor
    scored.append((score, w))

scored.sort(key=lambda x: x[0], reverse=True)

print(f"=== TOP WALLETS (TOTAL MATCHED: {len(scored)}) ===")
for rank, (sc, w) in enumerate(scored[:15], 1):
    trades = max(w.get('trade_count', 0), w.get('trades_stat', 0))
    print(f"#{rank} {w['userName']}")
    print(f"   Wallet: {w['proxyWallet']}")
    print(f"   URL: {w['url']}")
    print(f"   1D PnL: ${w.get('pnl_1d', 0):,.2f} | 7D PnL: ${w.get('pnl_7d', 0):,.2f} | 30D PnL: ${w.get('pnl_30d', 0):,.2f}")
    print(f"   7D Curve PnL: ${w.get('pnl_growth_7d_curve', 0):,.2f} | Total PnL: ${w.get('total_pnl', 0):,.2f}")
    print(f"   Volume: ${w.get('total_volume', 0):,.2f} | Total Trades: {trades:,}")
    print(f"   Winning Intervals: {w.get('win_interval_ratio', 0)*100:.1f}% | Max Drawdown 7D: ${w.get('max_drawdown', 0):,.2f}")
    print(f"   Positions: {w.get('positions', [])[:2]}")
    print("-" * 75)
