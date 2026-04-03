"""
config.py — Konfigurasi utama bot.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ─── EXNESS TRADELOCKER ────────────────────────────────────────
    # Gunakan email + password login Exness Anda
    MT5_LOGIN    = os.getenv("MT5_LOGIN", "")      # email Exness
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")   # password Exness
    MT5_SERVER   = os.getenv("MT5_SERVER", "Exness-MT5Trial7")

    # ─── POLYGON API (opsional, untuk data harga lebih akurat) ─────
    # Daftar gratis di https://polygon.io
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

    # ─── TELEGRAM ──────────────────────────────────────────────────
    TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    NOTIFY_NO_SIGNAL = False

    # ─── BOT SETTINGS ──────────────────────────────────────────────
    DRY_RUN                = True
    CHECK_INTERVAL_MINUTES = 15

    # ─── SCORING ───────────────────────────────────────────────────
    MIN_SCORE_THRESHOLD    = 60

    # ─── POLYMARKET ────────────────────────────────────────────────
    MIN_PROBABILITY_SIGNAL = 0.65
    MAX_PROBABILITY_EXIT   = 0.50

    # ─── RISK MANAGEMENT ───────────────────────────────────────────
    UNITS_PER_TRADE     = 1000
    RISK_PER_TRADE_USD  = 10
    MAX_UNITS_PER_TRADE = 5000
    STOP_LOSS_PIPS      = 30
    TAKE_PROFIT_PIPS    = 60

    # ─── WATCHED MARKETS ───────────────────────────────────────────
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
