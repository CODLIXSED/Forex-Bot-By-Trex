"""
config.py — Konfigurasi utama bot (Exness MT5).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ─── EXNESS MT5 ────────────────────────────────────────────────
    MT5_LOGIN    = int(os.getenv("MT5_LOGIN", "433418879"))
    MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER   = os.getenv("MT5_SERVER", "Exness-MT5Trial7")

    # ─── TELEGRAM ──────────────────────────────────────────────────
    TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    NOTIFY_NO_SIGNAL = False   # True = kirim notif meski tidak ada sinyal

    # ─── BOT SETTINGS ──────────────────────────────────────────────
    DRY_RUN                = True   # Ubah False untuk eksekusi order sungguhan
    CHECK_INTERVAL_MINUTES = 15

    # ─── SCORING ───────────────────────────────────────────────────
    MIN_SCORE_THRESHOLD    = 60    # 60=balanced, 70=konservatif, 50=agresif

    # ─── POLYMARKET ────────────────────────────────────────────────
    MIN_PROBABILITY_SIGNAL = 0.65
    MAX_PROBABILITY_EXIT   = 0.50

    # ─── RISK MANAGEMENT ───────────────────────────────────────────
    UNITS_PER_TRADE     = 1000    # fallback jika ATR tidak tersedia
    RISK_PER_TRADE_USD  = 10      # risiko per trade dalam USD
    MAX_UNITS_PER_TRADE = 5000
    STOP_LOSS_PIPS      = 30
    TAKE_PROFIT_PIPS    = 60

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
