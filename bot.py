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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from config import BotConfig
from market_scanner import AutonomousMarketScanner
from execution_engine import ExecutionEngine
from strategies import MultiStrategyCoordinator

def print_banner(cfg: BotConfig):
    mode_str = "🔴 LIVE TRADING (DINERO REAL CLOB)" if cfg.LIVE_TRADING else "🟢 PAPER TRADING EN VIVO (WEBSOCKET REAL SIN RIESGO)"
    print("=" * 96)
    print(" 🤖 POLYMARKET 10-STRATEGY AUTONOMOUS ENGINE + DYNAMIC $1,000 USDC MARGIN MANAGER (LONDON VPS)")
    print(f" Modo Ejecución  : {mode_str}")
    print(f" Modo Portafolio : {cfg.PORTFOLIO_MODE}")
    print(
        f" Bankroll Total  : ${cfg.TOTAL_BANKROLL_USDC:,.2f} USDC | "
        f"Cupo Apertura: ${cfg.MAX_TOTAL_EXPOSURE_USDC:,.2f} USDC | "
        f"Reserva Cobertura (Pata B): ${cfg.HEDGE_RESERVE_USDC:,.2f} USDC"
    )
    print("=" * 96)

def print_selected_portfolio_summary(buckets, engine: ExecutionEngine, cfg: BotConfig):
    print("\n📊 RESUMEN DE LAS 10 ESTRATEGIAS Y ASIGNACIÓN DE MARGEN (SOBRE $1,000 USDC):")
    for tag, mlist in buckets.items():
        committed = engine.get_strategy_committed_usdc(tag)
        budget = cfg.STRATEGY_MAX_BUDGET_USDC.get(tag, 80.0)
        order_sz = cfg.STRATEGY_ORDER_SIZE_USDC.get(tag, cfg.ORDER_SIZE_USDC)
        print(
            f"\n  [{tag}] ({len(mlist)} mercados | Orden=${order_sz:.2f} | "
            f"Margen Usado=${committed:.2f} / Cupo=${budget:.2f} USDC):"
        )
        for sm in mlist:
            meta_str = ", ".join(f"{k}={v}" for k, v in sm.metadata.items())
            print(
                f"    • {sm.question[:48]:48s} | "
                f"BidA=${sm.best_bid_a:.3f} AskA=${sm.best_ask_a:.3f} | "
                f"BidB=${sm.best_bid_b:.3f} | Vol24h=${sm.vol_24h:,.0f} | {meta_str}"
            )
    print("\n" + "-" * 96)
    print(
        f"📝 Órdenes Post-Only Activas : {len(engine.open_orders)} órdenes | "
        f"Margen Bloqueado en Libro: ${engine.get_open_order_margin_usdc():,.2f} USDC | "
        f"Margen Libre Apertura: ${engine.get_free_margin_usdc():,.2f} USDC (+ ${cfg.HEDGE_RESERVE_USDC:,.2f} Reserva)"
    )
    print("-" * 96)

def save_and_print_strategy_scorecard(engine: ExecutionEngine, cfg: BotConfig, ws_ticks: int, elapsed: float):
    """Imprime la tabla comparativa de desempeño de las 10 estrategias y guarda paper_trading_report.json."""
    print("\n" + "=" * 96)
    print(f" 📈 TABLERO AUDITOR DE LAS 10 ESTRATEGIAS ({elapsed:.1f}s | {ws_ticks:,} eventos WebSocket L2 reales)")
    print("-" * 96)
    print(
        f"  {'ESTRATEGIA':26s} | {'ABIERTAS':8s} | {'FILLS':5s} | {'MARGEN USADO':12s} | "
        f"{'ARB/MERGE PNL':13s} | {'SPREAD PNL':10s} | {'REBATES':8s}"
    )
    print("-" * 96)

    all_tags = list(cfg.STRATEGY_MAX_BUDGET_USDC.keys())
    report_rows = {}
    for tag in all_tags:
        open_cnt = sum(1 for o in engine.open_orders.values() if o.strategy_tag == tag and o.status == "OPEN")
        fill_cnt = sum(1 for o in engine.filled_orders if o.strategy_tag == tag)
        committed = engine.get_strategy_committed_usdc(tag)
        invs = [inv for inv in engine.inventories.values() if inv.strategy_tag == tag]
        arb_merge_pnl = round(sum(i.locked_dutch_book_profit + i.realized_merge_conv_pnl for i in invs), 4)
        spread_pnl = round(sum(i.realized_spread_pnl for i in invs), 4)
        rebates = round(sum(i.maker_rebates_earned for i in invs), 4)

        print(
            f"  {tag:26s} | {open_cnt:8d} | {fill_cnt:5d} | ${committed:10.2f} | "
            f"${arb_merge_pnl:+11.4f} | ${spread_pnl:+8.4f} | ${rebates:+6.4f}"
        )
        report_rows[tag] = {
            "open_orders": open_cnt,
            "fills": fill_cnt,
            "committed_margin_usdc": committed,
            "arb_and_merge_pnl_usdc": arb_merge_pnl,
            "spread_pnl_usdc": spread_pnl,
            "maker_rebates_usdc": rebates,
        }

    total_locked_arb = sum(inv.locked_dutch_book_profit for inv in engine.inventories.values())
    total_merge_pnl = sum(inv.realized_merge_conv_pnl for inv in engine.inventories.values())
    total_spread_pnl = sum(inv.realized_spread_pnl for inv in engine.inventories.values())
    total_rebates = sum(inv.maker_rebates_earned for inv in engine.inventories.values())
    total_net_pnl = round(total_locked_arb + total_merge_pnl + total_spread_pnl + total_rebates, 4)

    print("-" * 96)
    print(f"  Órdenes Abiertas Totales        : {len(engine.open_orders)} órdenes (${engine.get_open_order_margin_usdc():,.2f} USDC bloqueados)")
    print(f"  Fills Ejecutados en Vivo        : {len(engine.filled_orders)} fills")
    print(f"  Inventario Activo en Posiciones : ${engine.get_invested_inventory_usdc():,.2f} USDC")
    print(f"  Margen Libre Disponible         : ${engine.get_free_margin_usdc(include_hedge_reserve=True):,.2f} USDC (de ${cfg.TOTAL_BANKROLL_USDC:,.2f})")
    print(f"  Capital Reciclado (Auto-Merge)  : ${engine.total_recycled_usdc:,.2f} USDC ({engine.onchain_ops_count} fusiones a $1.00)")
    print(f"  PnL Neto Acumulado (Simulación) : ${total_net_pnl:+.4f} USDC")
    print("=" * 96)

    report_path = os.path.join(os.path.dirname(__file__), "paper_trading_report.json")
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "elapsed_seconds": round(elapsed, 1),
                    "ws_l2_events_processed": ws_ticks,
                    "bankroll_usdc": cfg.TOTAL_BANKROLL_USDC,
                    "free_margin_usdc": engine.get_free_margin_usdc(include_hedge_reserve=True),
                    "total_fills": len(engine.filled_orders),
                    "total_recycled_usdc": engine.total_recycled_usdc,
                    "total_net_pnl_usdc": total_net_pnl,
                    "strategies": report_rows,
                },
                f,
                indent=2,
            )
    except Exception:
        pass

async def run_bot(max_runtime_seconds: int = 0):
    cfg = BotConfig()
    print_banner(cfg)

    scanner = AutonomousMarketScanner(cfg)
    engine = ExecutionEngine(cfg)
    coordinator = MultiStrategyCoordinator(cfg, engine)

    print("🔍 Escaneando Gamma API para alimentar las 10 estrategias autónomas...")
    buckets = scanner.scan_and_select_all(max_per_strategy=3)
    token_ids = coordinator.register_selected_markets(buckets)
    print_selected_portfolio_summary(buckets, engine, cfg)

    if not token_ids:
        print("No se encontraron mercados que cumplan los filtros actuales.")
        return

    start_time = time.time()
    last_telemetry_time = start_time
    ws_ticks = 0

    print(f"🔌 Conectando al WebSocket en tiempo real ({cfg.WS_MARKET_URL}) para {len(token_ids)} tokens...")
    while True:
        try:
            async with websockets.connect(cfg.WS_MARKET_URL, ping_interval=15, ping_timeout=10) as ws:
                sub_payload = {"assets_ids": token_ids, "type": "market"}
                await ws.send(json.dumps(sub_payload))
                print("✅ Suscripción WebSocket L2 activa en las 10 estrategias. Escuchando libro en tiempo real...\n")

                while True:
                    now = time.time()
                    if max_runtime_seconds > 0 and (now - start_time) >= max_runtime_seconds:
                        save_and_print_strategy_scorecard(engine, cfg, ws_ticks, now - start_time)
                        return

                    # Cada 60 segundos en corrida continua, guarda y muestra el tablero auditor
                    if (now - last_telemetry_time) >= 60.0:
                        save_and_print_strategy_scorecard(engine, cfg, ws_ticks, now - start_time)
                        last_telemetry_time = now

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
                                # El snapshot inicial actualiza el estado del libro L2 sin simular fills históricos
                                coordinator.live_book_state[asset_id] = {"bid": best_bid, "ask": best_ask}

                    elif isinstance(payload, dict):
                        for chg in payload.get("price_changes") or []:
                            asset_id = str(chg.get("asset_id") or "")
                            best_bid = float(chg.get("best_bid") or 0.0)
                            best_ask = float(chg.get("best_ask") or 0.0)
                            st = coordinator.live_book_state.get(asset_id, {"bid": 0.0, "ask": 0.0})
                            b_bid = best_bid if best_bid > 0 else st["bid"]
                            b_ask = best_ask if best_ask > 0 else st["ask"]
                            if asset_id and (b_bid > 0 or b_ask > 0):
                                # price_changes actualiza el mejor Bid/Ask en vivo (sin confundir órdenes límite lejanas con trades)
                                coordinator.on_ws_tick(
                                    asset_id, b_bid, b_ask, last_trade_price=0.0
                                )
                        if payload.get("event_type") == "last_trade_price":
                            asset_id = str(payload.get("asset_id") or "")
                            trade_px = float(payload.get("price") or 0.0)
                            if asset_id and trade_px > 0:
                                st = coordinator.live_book_state.get(asset_id, {"bid": 0.0, "ask": 0.0})
                                coordinator.on_ws_tick(
                                    asset_id, st["bid"], st["ask"], last_trade_price=trade_px
                                )

        except Exception as e:
            if max_runtime_seconds > 0 and (time.time() - start_time) >= max_runtime_seconds:
                save_and_print_strategy_scorecard(engine, cfg, ws_ticks, time.time() - start_time)
                return
            print(f"⚠️ Reconectando WebSocket tras desconexión ({e})...")
            await asyncio.sleep(2.0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Polymarket Autonomous 10-Strategy Bot")
    parser.add_argument("--test-seconds", type=int, default=0, help="Correr por N segundos y salir")
    args = parser.parse_args()
    asyncio.run(run_bot(max_runtime_seconds=args.test_seconds))
