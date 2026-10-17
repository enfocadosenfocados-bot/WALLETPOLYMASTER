import urllib.request
import json
from datetime import datetime, timezone

HEADERS = {'User-Agent': 'Mozilla/5.0'}

def fetch_active_events(limit=100):
    url = f"https://gamma-api.polymarket.com/events?active=true&closed=false&limit={limit}&order=volume24hr&ascending=false"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=12) as r:
        return json.loads(r.read().decode('utf-8'))

def run_autonomous_selector():
    events = fetch_active_events(100)
    print(f"Scanned {len(events)} top active events on Polymarket...\n")

    strategy_1_spreads_totals = []   # HomeRunHazard / hi774c Pre-Match Vig-Free Maker
    strategy_2_live_gamma = []       # PEYZ-BIGGEST-FAN / RN1 Live In-Play Dutch-Book
    strategy_3_postonly_mm = []      # calculate10 4-Leg Post-Only Spread Harvester
    strategy_4_negrisk_arb_lp = []   # BreakTheBank / Nooserac NegRisk & LP Rewards

    for ev in events:
        ev_title = ev.get('title', '')
        is_live = bool(ev.get('live'))
        is_ended = bool(ev.get('ended'))
        if is_ended:
            continue
        sport = ev.get('sport') or ''
        mkts = ev.get('markets') or []

        # Check Strategy 4: Multi-outcome Negative Risk sum check on the event
        active_mkts = [m for m in mkts if m.get('active') and not m.get('closed') and m.get('acceptingOrders')]
        if ev.get('negRisk') and len(active_mkts) >= 3:
            # Check sum of bestAsk for YES across all outcomes
            asks = []
            bids = []
            for m in active_mkts:
                ba = float(m.get('bestAsk') or 0)
                bb = float(m.get('bestBid') or 0)
                if ba > 0:
                    asks.append(ba)
                if bb > 0:
                    bids.append(bb)
            if len(asks) == len(active_mkts):
                sum_asks = sum(asks)
                sum_bids = sum(bids)
                strategy_4_negrisk_arb_lp.append({
                    'event': ev_title,
                    'outcomes_count': len(active_mkts),
                    'sum_yes_asks': round(sum_asks, 4),
                    'sum_yes_bids': round(sum_bids, 4),
                    'vol24h': round(float(ev.get('volume24hr') or 0), 0)
                })

        for m in active_mkts:
            q = m.get('question', '')
            smt = (m.get('sportsMarketType') or '').lower()
            vol24 = float(m.get('volume24hr') or 0)
            bid = float(m.get('bestBid') or 0)
            ask = float(m.get('bestAsk') or 0)
            spread = float(m.get('spread') or (ask - bid if ask > bid > 0 else 0))
            rew_min = float(m.get('rewardsMinSize') or 0)
            rew_spread = float(m.get('rewardsMaxSpread') or 0)
            
            if bid <= 0 or ask <= 0 or ask <= bid:
                continue
            mid = (bid + ask) / 2.0

            # 1. Strategy 1: Pre-Match 50/50 Spreads & Totals (HomeRunHazard + hi774c)
            is_spread_or_total = smt in ['spreads', 'totals'] or 'spread:' in q.lower() or 'o/u' in q.lower()
            if not is_live and is_spread_or_total and 0.44 <= bid <= 0.495 and 0.495 <= ask <= 0.56 and vol24 >= 500:
                # Implied cost if we get filled as Maker on Side A at bid and Side B at (1 - ask)
                # Note: Side B bestBid = 1.0 - ask
                side_b_maker_bid = round(1.0 - ask, 4)
                combined_maker_cost = round(bid + side_b_maker_bid, 4)
                locked_arb_pct = round((1.0 - combined_maker_cost) * 100, 2)
                strategy_1_spreads_totals.append({
                    'question': q,
                    'type': smt or 'spread/total',
                    'bestBid_A': bid,
                    'bestAsk_A': ask,
                    'bestBid_B': side_b_maker_bid,
                    'combined_maker_cost': combined_maker_cost,
                    'locked_arb_pct': locked_arb_pct,
                    'vol24h': round(vol24, 0)
                })

            # 2. Strategy 2: Live In-Play High-Gamma Dutch-Book (PEYZ-BIGGEST-FAN / RN1)
            if is_live and 0.20 <= mid <= 0.80 and vol24 >= 5000:
                strategy_2_live_gamma.append({
                    'question': q,
                    'sport': sport or 'esports/live',
                    'score': ev.get('score') or 'LIVE',
                    'mid_price': round(mid, 3),
                    'bid': bid,
                    'ask': ask,
                    'spread_cents': round(spread * 100, 1),
                    'target_legB_for_6pct_arb': round(0.94 - bid, 3),
                    'vol24h': round(vol24, 0)
                })

            # 3. Strategy 3: Post-Only 4-Leg HFT Market Maker (calculate10)
            if 0.02 <= spread <= 0.08 and 0.15 <= mid <= 0.85 and vol24 >= 10000:
                edge_score = round((spread * 100) * (vol24 / 10000.0), 1)
                strategy_3_postonly_mm.append({
                    'question': q,
                    'live': is_live,
                    'bid': bid,
                    'ask': ask,
                    'spread_cents': round(spread * 100, 1),
                    'vol24h': round(vol24, 0),
                    'rewards_min_size': rew_min,
                    'mm_score': edge_score
                })

    print("=== ENGINE 1: PRE-MATCH SPREADS & TOTALS (HomeRunHazard / hi774c Vig-Free Maker) ===")
    strategy_1_spreads_totals.sort(key=lambda x: (x['vol24h'], x['locked_arb_pct']), reverse=True)
    for x in strategy_1_spreads_totals[:8]:
        print(f"  [PRE-MATCH] {x['question'][:48]:48s} | BidA=${x['bestBid_A']:.3f} | BidB=${x['bestBid_B']:.3f} | SumCost=${x['combined_maker_cost']:.3f} (Arb: +{x['locked_arb_pct']}%) | Vol24h=${x['vol24h']:,.0f}")

    print("\n=== ENGINE 2: LIVE IN-PLAY GAMMA SCALPING / DUTCH-BOOK (PEYZ-BIGGEST-FAN / RN1) ===")
    strategy_2_live_gamma.sort(key=lambda x: x['vol24h'], reverse=True)
    for x in strategy_2_live_gamma[:8]:
        print(f"  [LIVE {str(x['score'])[:7]:7s}] {x['question'][:45]:45s} | Bid=${x['bid']:.3f} Ask=${x['ask']:.3f} | Target LegB <= ${x['target_legB_for_6pct_arb']:.3f} | Vol24h=${x['vol24h']:,.0f}")

    print("\n=== ENGINE 3: 4-LEG POST-ONLY SPREAD HARVESTER (calculate10) ===")
    strategy_3_postonly_mm.sort(key=lambda x: x['mm_score'], reverse=True)
    for x in strategy_3_postonly_mm[:8]:
        print(f"  [MM SCORE {x['mm_score']:6.1f}] {x['question'][:45]:45s} | Bid=${x['bid']:.3f} Ask=${x['ask']:.3f} (Spread: {x['spread_cents']}c) | Live={x['live']} | Vol24h=${x['vol24h']:,.0f}")

    print("\n=== ENGINE 4: MULTI-OUTCOME NEGRISK MATRIX (BreakTheBank / Nooserac) ===")
    strategy_4_negrisk_arb_lp.sort(key=lambda x: abs(1.0 - x['sum_yes_asks']), reverse=True)
    for x in strategy_4_negrisk_arb_lp[:8]:
        print(f"  [NEGRISK {x['outcomes_count']:2d} legs] {x['event'][:45]:45s} | SumYesBids=${x['sum_yes_bids']:.4f} | SumYesAsks=${x['sum_yes_asks']:.4f} | Vol24h=${x['vol24h']:,.0f}")

if __name__ == '__main__':
    run_autonomous_selector()
