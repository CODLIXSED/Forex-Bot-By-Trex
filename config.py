"""
config.py — Konfigurasi utama bot.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ─── OANDA API ─────────────────────────────────────────────────
    OANDA_API_KEY    = os.getenv("OANDA_API_KEY", "")
    OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
    PRACTICE_MODE    = True    # True = akun demo OANDA

    # ─── TELEGRAM ──────────────────────────────────────────────────
    TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    NOTIFY_NO_SIGNAL = False   # True = kirim notif meski tidak ada sinyal

    # ─── BOT SETTINGS ──────────────────────────────────────────────
    DRY_RUN                = True
    CHECK_INTERVAL_MINUTES = 15

    # ─── SCORING ───────────────────────────────────────────────────
    MIN_SCORE_THRESHOLD    = 60   # 0-100 (60=balanced, 70=konservatif)

    # ─── POLYMARKET ────────────────────────────────────────────────
    MIN_PROBABILITY_SIGNAL = 0.65
    MAX_PROBABILITY_EXIT   = 0.50

    # ─── RISK MANAGEMENT ───────────────────────────────────────────
    UNITS_PER_TRADE      = 1000
    RISK_PER_TRADE_USD   = 10
    MAX_UNITS_PER_TRADE  = 5000
    STOP_LOSS_PIPS       = 30
    TAKE_PROFIT_PIPS     = 60

    # ─── WATCHED MARKETS ───────────────────────────────────────────
    # Cari condition_id: python search_markets.py "kata kunci"
    WATCHED_MARKETS = [
        {
            "name": "Fed Rate Cut 2025",
            "condition_id": "GANTI_DENGAN_CONDITION_ID_ASLI",
            "forex_pair": "EUR_USD",
            "signal_outcome": "Yes",
            "signal_direction": "BUY",
        },
        {
            "name": "Bitcoin above $100k",
            "condition_id": "GANTI_DENGAN_CONDITION_ID_ASLI",
            "forex_pair": "USD_JPY",
            "signal_outcome": "Yes",
            "signal_direction": "BUY",
        },
    ]
