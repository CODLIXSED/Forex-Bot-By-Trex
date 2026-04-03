"""
bot.py — Entry point utama.
Jalankan: python bot.py
"""

import time
import json
import os
import schedule
import logging
from datetime import datetime

from config import Config
from polymarket import PolymarketMonitor
from forex import ForexTrader
from strategy import TradingStrategy
from logger import setup_logger

logger = setup_logger()

# File untuk menyimpan riwayat probabilitas (untuk deteksi trend)
HISTORY_FILE = "prob_history.json"


def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_history(history: dict):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def run_bot():
    logger.info("=" * 55)
    logger.info(f"⏰ Cek: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    poly     = PolymarketMonitor()
    trader   = ForexTrader(Config.OANDA_API_KEY, Config.OANDA_ACCOUNT_ID,
                           Config.PRACTICE_MODE)
    strategy = TradingStrategy()
    history  = load_history()

    for market in Config.WATCHED_MARKETS:
        cid  = market["condition_id"]
        name = market["name"]
        logger.info(f"\n📊 {name}")

        odds = poly.get_market_odds(cid)
        if not odds:
            logger.warning("  Gagal ambil data Polymarket.")
            continue

        # Simpan riwayat probabilitas untuk deteksi trend
        target = market.get("signal_outcome", "Yes")
        prob   = odds.get(target, 0)
        if cid not in history:
            history[cid] = []
        history[cid].append(prob)
        history[cid] = history[cid][-10:]   # simpan 10 data terakhir
        save_history(history)

        # Analisis multi-faktor
        signal = strategy.analyze(market, odds, prob_history=history[cid])

        if not signal:
            continue

        if Config.DRY_RUN:
            logger.info(f"  [DRY RUN] {signal['action']} {signal['pair']} "
                        f"| units: {signal['units']} | skor: {signal['score']:.1f}")
        else:
            units = signal["units"] if signal["action"] == "BUY" else -signal["units"]
            result = trader.place_order(signal["pair"], units)
            if result:
                logger.info(f"  ✅ Order berhasil: {result}")
            else:
                logger.error(f"  ❌ Order gagal")

    # Ringkasan akun
    if not Config.DRY_RUN:
        summary = trader.get_account_summary()
        if summary:
            logger.info(f"\n💰 Akun: Balance={summary['balance']} | "
                        f"NAV={summary['nav']} | PnL={summary['unrealized_pl']}")


def main():
    logger.info("🚀 Bot dimulai")
    logger.info(f"Mode: {'PRACTICE' if Config.PRACTICE_MODE else '⚠️  LIVE'} | "
                f"DryRun: {Config.DRY_RUN} | "
                f"Threshold: {Config.MIN_SCORE_THRESHOLD}/100")

    run_bot()
    schedule.every(Config.CHECK_INTERVAL_MINUTES).minutes.do(run_bot)
    logger.info(f"Jadwal: setiap {Config.CHECK_INTERVAL_MINUTES} menit.")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
