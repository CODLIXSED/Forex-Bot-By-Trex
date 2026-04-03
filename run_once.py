"""
run_once.py — Versi bot untuk GitHub Actions (berjalan sekali).
"""

import json
import os
import logging
from datetime import datetime

from config import Config
from polymarket import PolymarketMonitor
from forex import ForexTrader
from strategy import TradingStrategy
from logger import setup_logger
from telegram_notify import TelegramNotifier

logger   = setup_logger()
HISTORY_FILE = "prob_history.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return json.load(f)
    return {}


def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)


def main():
    logger.info("=" * 55)
    logger.info(f"🚀 Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    tg = TelegramNotifier(Config.TELEGRAM_TOKEN, Config.TELEGRAM_CHAT_ID)

    poly     = PolymarketMonitor()
    trader   = ForexTrader(Config.OANDA_API_KEY, Config.OANDA_ACCOUNT_ID,
                           Config.PRACTICE_MODE)
    strategy = TradingStrategy()
    history  = load_history()

    any_signal = False

    for market in Config.WATCHED_MARKETS:
        cid  = market["condition_id"]
        name = market["name"]
        logger.info(f"\n📊 {name}")

        odds = poly.get_market_odds(cid)
        if not odds:
            logger.warning("  Gagal ambil data Polymarket.")
            tg.error(name, "Gagal ambil data dari Polymarket API")
            continue

        # Simpan riwayat probabilitas
        target = market.get("signal_outcome", "Yes")
        prob   = odds.get(target, 0)
        if cid not in history:
            history[cid] = []
        history[cid].append(round(prob, 4))
        history[cid] = history[cid][-10:]
        save_history(history)

        # Analisis multi-faktor
        signal = strategy.analyze(market, odds, prob_history=history[cid])

        if not signal:
            continue

        any_signal = True

        # Kirim notifikasi sinyal ke Telegram
        tg.signal(signal)

        if Config.DRY_RUN:
            logger.info(f"  [DRY RUN] {signal['action']} {signal['pair']} "
                        f"| units: {signal['units']} | skor: {signal['score']:.1f}")
            tg.send(f"🧪 <b>DRY RUN</b> — tidak ada order sungguhan.")
        else:
            units  = signal["units"] if signal["action"] == "BUY" else -signal["units"]
            result = trader.place_order(signal["pair"], units)
            if result:
                price = result.get("price", "?")
                logger.info(f"  ✅ Order berhasil @ {price}")
                tg.order_success(signal["pair"], signal["action"], signal["units"], price)
            else:
                logger.error(f"  ❌ Order gagal")
                tg.order_failed(signal["pair"], signal["action"])

    if not any_signal:
        logger.info("\nℹ️  Tidak ada sinyal valid.")
        # Kirim notif "tidak ada sinyal" hanya jika diaktifkan
        if Config.NOTIFY_NO_SIGNAL:
            tg.no_signal()

    logger.info("\n✅ Run selesai.")


if __name__ == "__main__":
    main()
