"""
Orquestador Principal del Bot Autónomo de 10 Estrategias para Polymarket (VPS Londres)
- Escanea automáticamente los mercados activos sin copiar wallets (AutonomousMarketScanner)
- Opera las 10 estrategias cuantitativas (Lote 1: S1-S4 + Lote 2: S5-S10)
- Gestiona dinámicamente un Bankroll de $1,000 USDC con Cuotas por Estrategia, Reserva de Cobertura ($120 USDC)
  y Auto-Reciclaje Instantáneo (MERGE / CONVERSION) para no quedarse jamás sin margen.
- Incluye Auditoría de Paper Trading en Tiempo Real (guarda resultados por estrategia en paper_trading_report.json).
"""
import argparse
import asyncio
import json
import os
import sys
import time
import websockets

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from config import BotConfig
from market_scanner import AutonomousMarketScanner
from execution_engine import ExecutionEngine
from strategies import MultiStrategyCoordinator

def print_banner(cfg: BotConfig):
    mode_str = "🔴 LIVE TRADING (DINERO REAL CLOB)" if cfg.LIVE_TRADING else "🟢 PAPER REALISTA EN VIVO (CON COLAS FIFO + SLIPPAGE + SPREAD + GAS)"
    is_tourney = (cfg.PORTFOLIO_MODE == "TOURNAMENT_10K_EQUAL")
    is_champ6 = (cfg.PORTFOLIO_MODE == "LIVE_6_CHAMPIONS_1K")
    is_lowrisk4 = (cfg.PORTFOLIO_MODE == "LOW_RISK_4_NETHERLANDS")
    print("=" * 124)
    if is_lowrisk4:
        print(" 🛡️ POLYMARKET 4-STRATEGY LOW-RISK MASTER ENGINE ($1,000 USDC: S5, S8, S3, S4 | NETHERLANDS/AMSTERDAM VPS EDITION)")
    elif is_champ6:
        print(" 🏆 POLYMARKET 6-CHAMPIONS PRODUCTION ENGINE ($1,000 USDC: $880 EN LAS 6 GANADORAS + $120 RESERVA + FRICCIÓN REAL)")
    elif is_tourney:
        print(" 🏆 POLYMARKET STRATEGY TOURNAMENT ARENA ($10,000 USDC = $1,000 AISLADOS POR CADA UNA DE LAS 10 ESTRATEGIAS)")
    else:
        print(" 🤖 POLYMARKET AUTONOMOUS ENGINE + DYNAMIC $1,000 USDC MARGIN MANAGER")
    print(f" Modo Ejecución  : {mode_str}")
    print(
        f" Modo Portafolio : {cfg.PORTFOLIO_MODE} | "
        f"Fricción Realista: {'ACTIVA (Colas FIFO + Stop Pata Coja + Gas Polygon)' if cfg.REALISTIC_FRICTION_ENABLED else 'DESACTIVADA'}"
    )
    print(
        f" Bankroll Total  : ${cfg.TOTAL_BANKROLL_USDC:,.2f} USDC | "
        f"Cupo Apertura: ${cfg.MAX_TOTAL_EXPOSURE_USDC:,.2f} USDC | "
        f"Reserva Cobertura (Pata B): ${cfg.HEDGE_RESERVE_USDC:,.2f} USDC"
    )
    print("=" * 124)

def print_selected_portfolio_summary(buckets, engine: ExecutionEngine, cfg: BotConfig):
    is_tourney = (cfg.PORTFOLIO_MODE == "TOURNAMENT_10K_EQUAL")
    title = (
        "\n📊 RESUMEN DEL PORTAFOLIO DE BAJO RIESGO ($1,000.00 USDC EN LAS 4 ESTRATEGIAS MÁS SEGURAS + FRICCIÓN REAL):"
        if cfg.PORTFOLIO_MODE == "LOW_RISK_4_NETHERLANDS"
        else (
            "\n📊 RESUMEN DEL PORTAFOLIO MAESTRO ($1,000.00 USDC EN LAS 6 ESTRATEGIAS CAMPEONAS + FRICCIÓN REAL):"
            if cfg.PORTFOLIO_MODE == "LIVE_6_CHAMPIONS_1K"
            else f"\n📊 RESUMEN DE ESTRATEGIAS Y ASIGNACIÓN DE MARGEN (SOBRE ${cfg.TOTAL_BANKROLL_USDC:,.2f} USDC):"
        )
    )
    print(title)
    for tag, mlist in buckets.items():
        budget = cfg.STRATEGY_MAX_BUDGET_USDC.get(tag, 0.0)
        if budget <= 0:
            continue
        committed = engine.get_strategy_committed_usdc(tag)
        order_sz = cfg.STRATEGY_ORDER_SIZE_USDC.get(tag, cfg.ORDER_SIZE_USDC)
        reserve_note = " + $120.00 Reserva" if is_tourney else ""
        print(
            f"\n  [{tag}] ({len(mlist)} mercados | Orden=${order_sz:.2f} | "
            f"Margen Usado=${committed:.2f} / Cupo Apertura=${budget:.2f} USDC{reserve_note}):"
        )
        for sm in mlist:
            meta_str = ", ".join(f"{k}={v}" for k, v in sm.metadata.items())
            print(
                f"    • {sm.question[:48]:48s} | "
                f"BidA=${sm.best_bid_a:.3f} AskA=${sm.best_ask_a:.3f} | "
                f"BidB=${sm.best_bid_b:.3f} | Vol24h=${sm.vol_24h:,.0f} | {meta_str}"
            )
    print("\n" + "-" * 124)
    print(
        f"📝 Órdenes Post-Only Activas : {len(engine.open_orders)} órdenes | "
        f"Margen Bloqueado en Libro: ${engine.get_open_order_margin_usdc():,.2f} USDC | "
        f"Margen Libre Apertura: ${engine.get_free_margin_usdc():,.2f} USDC (+ ${cfg.HEDGE_RESERVE_USDC:,.2f} Reserva)"
    )
    print("-" * 124)

def save_and_print_strategy_scorecard(
    engine: ExecutionEngine, cfg: BotConfig, ws_ticks: int, elapsed: float, rotation_cycles: int = 0
):
    """Imprime el tablero de las 6 Estrategias Campeonas con todos los costos de fricción real y guarda reporte + historial."""
    hours_run = elapsed / 3600.0
    is_tourney = (cfg.PORTFOLIO_MODE == "TOURNAMENT_10K_EQUAL")
    is_champ6 = (cfg.PORTFOLIO_MODE == "LIVE_6_CHAMPIONS_1K")
    header_title = (
        f" 🏆 TABLERO CALIBRADO DE LAS 6 CAMPEONAS ($1,000 USDC CON SPREADS + SLIPPAGE + COLAS FIFO + GAS) "
        if is_champ6
        else f" 📈 TABLERO AUDITOR 24/7 DE ESTRATEGIAS "
    )
    print("\n" + "=" * 128)
    print(f"{header_title}({elapsed:.0f}s / {hours_run:.2f}h | {ws_ticks:,} eventos L2 | {rotation_cycles} rotaciones)")
    print("-" * 128)
    print(
        f"  {'ESTRATEGIA':24s} | {'ORD':3s} | {'FILLS':5s} | {'COLA_X':6s} | {'MERGES':6s} | {'MARGEN / CUPO':15s} | "
        f"{'ARB/MERGE':10s} | {'SPREAD/SLIP':11s} | {'FRICCIÓN':9s} | {'PNL NETO':10s} | {'ROI %':7s}"
    )
    print("-" * 128)

    all_tags = list(cfg.STRATEGY_MAX_BUDGET_USDC.keys())
    report_rows = {}
    ranking_list = []

    for tag in all_tags:
        budget_cfg = cfg.STRATEGY_MAX_BUDGET_USDC.get(tag, 0.0)
        if budget_cfg <= 0 and is_champ6:
            continue
        open_cnt = sum(1 for o in engine.open_orders.values() if o.strategy_tag == tag and o.status == "OPEN")
        invs = [inv for inv in engine.inventories.values() if inv.strategy_tag == tag]
        fill_cnt = sum(i.fills_count for i in invs)
        q_missed = sum(i.queue_missed_count for i in invs)
        leg_exits = sum(i.legging_exits_count for i in invs)
        merge_cnt = sum(i.merge_conv_count for i in invs)
        committed = engine.get_strategy_committed_usdc(tag)
        peak_committed = max(committed, engine.peak_strategy_committed_usdc.get(tag, 0.0))
        recycled_strat = engine.total_recycled_by_strategy.get(tag, 0.0)
        alloc_cap = 1000.0 if is_tourney else budget_cfg

        arb_merge_pnl = round(sum(i.locked_dutch_book_profit + i.realized_merge_conv_pnl for i in invs), 4)
        spread_pnl = round(sum(i.realized_spread_pnl for i in invs), 4)
        rebates = round(sum(i.maker_rebates_earned for i in invs), 4)
        friction_cost = round(sum(i.friction_costs_usdc for i in invs), 4)
        strat_net_pnl = round(arb_merge_pnl + spread_pnl + rebates, 4)

        roi_on_allocation_pct = round((strat_net_pnl / alloc_cap) * 100.0, 2) if alloc_cap > 0 else 0.0
        roi_on_deployed_pct = round((strat_net_pnl / peak_committed) * 100.0, 2) if peak_committed > 0 else 0.0

        margin_str = f"${committed:5.1f}/${alloc_cap:5.0f}"
        print(
            f"  {tag:24s} | {open_cnt:3d} | {fill_cnt:5d} | {q_missed:6d} | {merge_cnt:6d} | {margin_str:15s} | "
            f"${arb_merge_pnl:+9.4f} | ${spread_pnl:+10.4f} | -${friction_cost:7.4f} | ${strat_net_pnl:+9.4f} | {roi_on_allocation_pct:+6.2f}%"
        )
        report_rows[tag] = {
            "allocated_bankroll_usdc": alloc_cap,
            "open_orders": open_cnt,
            "fills": fill_cnt,
            "fifo_queue_missed": q_missed,
            "legging_stop_exits": leg_exits,
            "merges_completed": merge_cnt,
            "committed_margin_usdc": committed,
            "peak_committed_margin_usdc": peak_committed,
            "recycled_capital_usdc": recycled_strat,
            "arb_and_merge_pnl_usdc": arb_merge_pnl,
            "spread_and_legging_pnl_usdc": spread_pnl,
            "maker_rebates_usdc": rebates,
            "total_friction_costs_usdc": friction_cost,
            "net_pnl_usdc": strat_net_pnl,
            "roi_on_allocated_pct": roi_on_allocation_pct,
            "roi_on_deployed_margin_pct": roi_on_deployed_pct,
        }
        ranking_list.append((tag, strat_net_pnl, roi_on_allocation_pct, roi_on_deployed_pct, fill_cnt, merge_cnt))

    ranking_list.sort(key=lambda x: (x[1], x[4]), reverse=True)
    top_3_str = "  |  ".join(
        f"#{idx+1} {t}: ${pnl:+.4f} ({roi_alloc:+.2f}% s/cupo, {fl} fills, {mg} merges)"
        for idx, (t, pnl, roi_alloc, _, fl, mg) in enumerate(ranking_list[:3])
    )

    total_locked_arb = sum(inv.locked_dutch_book_profit for inv in engine.inventories.values())
    total_merge_pnl = sum(inv.realized_merge_conv_pnl for inv in engine.inventories.values())
    total_spread_pnl = sum(inv.realized_spread_pnl for inv in engine.inventories.values())
    total_rebates = sum(inv.maker_rebates_earned for inv in engine.inventories.values())
    total_net_pnl = round(total_locked_arb + total_merge_pnl + total_spread_pnl + total_rebates, 4)
    total_roi_pct = round((total_net_pnl / cfg.TOTAL_BANKROLL_USDC) * 100.0, 3) if cfg.TOTAL_BANKROLL_USDC > 0 else 0.0

    print("-" * 128)
    print(f"  🥇 LÍDERES EN VIVO (NETO REAL)  : {top_3_str}")
    print(f"  Órdenes Abiertas Totales        : {len(engine.open_orders)} órdenes (${engine.get_open_order_margin_usdc():,.2f} USDC bloqueados)")
    print(
        f"  Fills Reales vs Colas FIFO      : {engine.total_fills_count} fills ejecutados | "
        f"{engine.total_queue_missed_count} toques no llenados por prioridad de cola FIFO"
    )
    print(
        f"  Costos de Fricción Descontados  : -${engine.total_friction_costs_usdc:,.4f} USDC "
        f"(Gas Polygon en {engine.onchain_ops_count} merges + {engine.total_legging_exits_count} cierres de Pata Coja/Slippage)"
    )
    print(f"  Inventario Activo en Posiciones : ${engine.get_invested_inventory_usdc():,.2f} USDC")
    print(f"  Margen Libre Disponible         : ${engine.get_free_margin_usdc(include_hedge_reserve=True):,.2f} USDC (de ${cfg.TOTAL_BANKROLL_USDC:,.2f})")
    print(f"  Capital Reciclado (Auto-Merge)  : ${engine.total_recycled_usdc:,.2f} USDC ({engine.onchain_ops_count} fusiones a $1.00)")
    print(f"  PnL Neto Acumulado (Tras Costos): ${total_net_pnl:+.4f} USDC ({total_roi_pct:+.3f}% sobre ${cfg.TOTAL_BANKROLL_USDC:,.0f} USDC)")
    print("=" * 128)

    base_dir = os.path.dirname(__file__)
    report_path = os.path.join(base_dir, "paper_trading_report.json")
    history_path = os.path.join(base_dir, "paper_trading_history.jsonl")

    snapshot_payload = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "portfolio_mode": cfg.PORTFOLIO_MODE,
        "realistic_friction_enabled": cfg.REALISTIC_FRICTION_ENABLED,
        "elapsed_seconds": round(elapsed, 1),
        "elapsed_hours": round(hours_run, 3),
        "rotation_cycles": rotation_cycles,
        "ws_l2_events_processed": ws_ticks,
        "bankroll_usdc": cfg.TOTAL_BANKROLL_USDC,
        "free_margin_usdc": engine.get_free_margin_usdc(include_hedge_reserve=True),
        "total_fills": engine.total_fills_count,
        "total_fifo_queue_missed": engine.total_queue_missed_count,
        "total_legging_stop_exits": engine.total_legging_exits_count,
        "total_friction_costs_usdc": engine.total_friction_costs_usdc,
        "total_recycled_usdc": engine.total_recycled_usdc,
        "total_net_pnl_usdc": total_net_pnl,
        "total_roi_on_bankroll_pct": total_roi_pct,
        "active_condition_ids": list(engine.inventories.keys()),
        "tournament_leaderboard": [
            {
                "rank": idx + 1,
                "strategy": t,
                "net_pnl_usdc": pnl,
                "roi_on_allocated_pct": roi_alloc,
                "roi_on_deployed_margin_pct": roi_dep,
                "fills": fl,
                "merges": mg,
            }
            for idx, (t, pnl, roi_alloc, roi_dep, fl, mg) in enumerate(ranking_list)
        ],
        "strategies": report_rows,
    }

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(snapshot_payload, f, indent=2)
    except Exception:
        pass

    try:
        with open(history_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "timestamp": snapshot_payload["timestamp"],
                "portfolio_mode": cfg.PORTFOLIO_MODE,
                "elapsed_hours": snapshot_payload["elapsed_hours"],
                "total_fills": snapshot_payload["total_fills"],
                "total_fifo_queue_missed": snapshot_payload["total_fifo_queue_missed"],
                "total_friction_costs_usdc": snapshot_payload["total_friction_costs_usdc"],
                "total_recycled_usdc": snapshot_payload["total_recycled_usdc"],
                "total_net_pnl_usdc": snapshot_payload["total_net_pnl_usdc"],
                "top_strategy": ranking_list[0][0] if ranking_list else "NONE",
                "per_strategy_pnl": {k: v["net_pnl_usdc"] for k, v in report_rows.items()},
            }) + "\n")
    except Exception:
        pass

async def run_bot(max_runtime_seconds: int = 0):
    cfg = BotConfig()
    print_banner(cfg)

    scanner = AutonomousMarketScanner(cfg)
    engine = ExecutionEngine(cfg)
    coordinator = MultiStrategyCoordinator(cfg, engine)

    print("🔍 Escaneando Gamma API para alimentar las 10 estrategias autónomas...")
    buckets = await asyncio.to_thread(scanner.scan_and_select_all, cfg.MAX_MARKETS_PER_STRATEGY)
    token_ids = coordinator.register_selected_markets(buckets)
    print_selected_portfolio_summary(buckets, engine, cfg)

    if not token_ids:
        print("No se encontraron mercados que cumplan los filtros actuales.")
        return

    start_time = time.time()
    last_telemetry_time = start_time
    last_scan_time = start_time
    ws_ticks = 0
    rotation_cycles = 0

    print(f"🔌 Conectando al WebSocket en tiempo real ({cfg.WS_MARKET_URL}) para {len(token_ids)} tokens...")
    while True:
        try:
            async with websockets.connect(cfg.WS_MARKET_URL, ping_interval=15, ping_timeout=10) as ws:
                current_token_ids = coordinator.get_all_active_token_ids() or token_ids
                sub_payload = {"assets_ids": current_token_ids, "type": "market"}
                await ws.send(json.dumps(sub_payload))
                print(f"✅ Suscripción WebSocket L2 activa ({len(current_token_ids)} tokens en las 10 estrategias). Escuchando libro 24/7...\n")

                while True:
                    now = time.time()
                    if engine.check_circuit_breaker():
                        save_and_print_strategy_scorecard(engine, cfg, ws_ticks, now - start_time, rotation_cycles)
                        print("🛑 [KILL-SWITCH] Proceso finalizado por activación de Circuit Breaker.")
                        return

                    if max_runtime_seconds > 0 and (now - start_time) >= max_runtime_seconds:
                        save_and_print_strategy_scorecard(engine, cfg, ws_ticks, now - start_time, rotation_cycles)
                        return

                    # 1. Cada 60 segundos guarda y muestra el Tablero Auditor + Ranking + Historial JSONL
                    if (now - last_telemetry_time) >= 60.0:
                        save_and_print_strategy_scorecard(engine, cfg, ws_ticks, now - start_time, rotation_cycles)
                        last_telemetry_time = now

                    # 2. Cada MARKET_SCAN_INTERVAL_SEC (ej. 180s), re-escanea Gamma API en segundo plano (sin bloquear el Event Loop)
                    #    para agregar partidos nuevos, retirar partidos terminados y recotizar órdenes obsoletas
                    if (now - last_scan_time) >= cfg.MARKET_SCAN_INTERVAL_SEC:
                        last_scan_time = now
                        new_buckets = await asyncio.to_thread(scanner.scan_and_select_all, cfg.MAX_MARKETS_PER_STRATEGY)
                        if any(new_buckets.values()):
                            old_tokens_set = set(coordinator.get_all_active_token_ids())
                            rot_stats = coordinator.sync_and_rotate_markets(new_buckets, now)
                            rotation_cycles += 1
                            new_tokens_list = coordinator.get_all_active_token_ids()
                            if (
                                rot_stats["added_markets"] > 0
                                or rot_stats["retired_markets"] > 0
                                or rot_stats["freed_orders"] > 0
                            ):
                                print(
                                    f"  🔄 [ROTACIÓN 24/7 #{rotation_cycles}] "
                                    f"+{rot_stats['added_markets']} mkts nuevos | "
                                    f"-{rot_stats['retired_markets']} mkts cerrados | "
                                    f"♻️ {rot_stats['freed_orders']} órdenes recotizadas | "
                                    f"Tokens activos: {len(new_tokens_list)}"
                                )
                            # Si entraron nuevos tokens al portafolio, actualizamos la suscripción del WebSocket en caliente
                            if set(new_tokens_list) != old_tokens_set and new_tokens_list:
                                await ws.send(json.dumps({"assets_ids": new_tokens_list, "type": "market"}))

                    try:
                        raw_msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue

                    ws_ticks += 1
                    try:
                        payload = json.loads(raw_msg)
                    except Exception:
                        continue

                    if isinstance(payload, list):
                        for item in payload:
                            asset_id = str(item.get("asset_id") or "")
                            bids = item.get("bids") or []
                            asks = item.get("asks") or []
                            best_bid = max((float(b["price"]) for b in bids), default=0.0)
                            best_ask = min((float(a["price"]) for a in asks), default=0.0)
                            bid_depth = sum(float(b["size"]) for b in bids[:3])
                            ask_depth = sum(float(a["size"]) for a in asks[:3])
                            if asset_id and (best_bid > 0 or best_ask > 0):
                                # El snapshot inicial actualiza el estado del libro L2 (incluyendo profundidad top-3 para S3)
                                coordinator.live_book_state[asset_id] = {
                                    "bid": best_bid,
                                    "ask": best_ask,
                                    "bid_depth": bid_depth,
                                    "ask_depth": ask_depth,
                                }

                    elif isinstance(payload, dict):
                        for chg in payload.get("price_changes") or []:
                            asset_id = str(chg.get("asset_id") or "")
                            best_bid = float(chg.get("best_bid") or 0.0)
                            best_ask = float(chg.get("best_ask") or 0.0)
                            st = coordinator.live_book_state.get(
                                asset_id, {"bid": 0.0, "ask": 0.0, "bid_depth": 0.0, "ask_depth": 0.0}
                            )
                            b_bid = best_bid if best_bid > 0 else st["bid"]
                            b_ask = best_ask if best_ask > 0 else st["ask"]
                            chg_size = float(chg.get("size") or 0.0)
                            chg_side = str(chg.get("side") or "").upper()
                            b_depth = chg_size if (chg_side == "BUY" and chg_size > 0) else st.get("bid_depth", 0.0)
                            a_depth = chg_size if (chg_side == "SELL" and chg_size > 0) else st.get("ask_depth", 0.0)
                            if asset_id and (b_bid > 0 or b_ask > 0):
                                coordinator.live_book_state[asset_id] = {
                                    "bid": b_bid,
                                    "ask": b_ask,
                                    "bid_depth": b_depth,
                                    "ask_depth": a_depth,
                                }
                                coordinator.on_ws_tick(
                                    asset_id,
                                    b_bid,
                                    b_ask,
                                    bid_depth_shares=b_depth,
                                    ask_depth_shares=a_depth,
                                    last_trade_price=0.0,
                                )
                        if payload.get("event_type") == "last_trade_price":
                            asset_id = str(payload.get("asset_id") or "")
                            trade_px = float(payload.get("price") or 0.0)
                            if asset_id and trade_px > 0:
                                st = coordinator.live_book_state.get(
                                    asset_id, {"bid": 0.0, "ask": 0.0, "bid_depth": 0.0, "ask_depth": 0.0}
                                )
                                coordinator.on_ws_tick(
                                    asset_id,
                                    st["bid"],
                                    st["ask"],
                                    bid_depth_shares=st.get("bid_depth", 0.0),
                                    ask_depth_shares=st.get("ask_depth", 0.0),
                                    last_trade_price=trade_px,
                                )

        except Exception as e:
            if max_runtime_seconds > 0 and (time.time() - start_time) >= max_runtime_seconds:
                save_and_print_strategy_scorecard(engine, cfg, ws_ticks, time.time() - start_time, rotation_cycles)
                return
            print(f"⚠️ Reconectando WebSocket tras desconexión ({e})...")
            await asyncio.sleep(2.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polymarket Autonomous 10-Strategy Bot")
    parser.add_argument("--test-seconds", type=int, default=0, help="Correr por N segundos y salir")
    args = parser.parse_args()
    asyncio.run(run_bot(max_runtime_seconds=args.test_seconds))
