"""
telegram_notify.py — Kirim notifikasi ke Telegram.
"""

import requests
import logging

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token   = token
        self.chat_id = chat_id
        self.base    = f"https://api.telegram.org/bot{token}"

    def send(self, message: str) -> bool:
        """Kirim pesan teks ke Telegram."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram token/chat_id kosong, skip notifikasi.")
            return False
        try:
            url  = f"{self.base}/sendMessage"
            data = {
                "chat_id":    self.chat_id,
                "text":       message,
                "parse_mode": "HTML",
            }
            resp = requests.post(url, json=data, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Gagal kirim Telegram: {e}")
            return False

    def signal(self, signal: dict) -> bool:
        """Notifikasi sinyal trading baru."""
        action_icon = "🟢" if signal["action"] == "BUY" else "🔴"
        msg = (
            f"{action_icon} <b>SINYAL TRADING</b>\n\n"
            f"📌 <b>Market:</b> {signal['market_name']}\n"
            f"💱 <b>Pair:</b> {signal['pair']}\n"
            f"📈 <b>Aksi:</b> {signal['action']}\n"
            f"🎯 <b>Probabilitas:</b> {signal['probability']:.1%}\n"
            f"⭐ <b>Skor:</b> {signal['score']:.1f}/100\n"
            f"📊 <b>RSI:</b> {signal.get('rsi', 'N/A')}\n"
            f"📉 <b>EMA:</b> {signal.get('ema_signal', 'N/A')}\n"
            f"📦 <b>Units:</b> {signal['units']}"
        )
        return self.send(msg)

    def order_success(self, pair: str, action: str, units: int, price: str) -> bool:
        """Notifikasi order berhasil dieksekusi."""
        icon = "🟢" if action == "BUY" else "🔴"
        msg = (
            f"{icon} <b>ORDER BERHASIL</b>\n\n"
            f"💱 <b>Pair:</b> {pair}\n"
            f"📈 <b>Aksi:</b> {action}\n"
            f"📦 <b>Units:</b> {units}\n"
            f"💰 <b>Harga:</b> {price}"
        )
        return self.send(msg)

    def order_failed(self, pair: str, action: str) -> bool:
        """Notifikasi order gagal."""
        msg = (
            f"❌ <b>ORDER GAGAL</b>\n\n"
            f"💱 <b>Pair:</b> {pair}\n"
            f"📈 <b>Aksi:</b> {action}\n"
            f"⚠️ Cek log GitHub Actions untuk detail."
        )
        return self.send(msg)

    def no_signal(self) -> bool:
        """Notifikasi tidak ada sinyal (opsional, bisa dimatikan)."""
        msg = "ℹ️ <b>Tidak ada sinyal</b> pada run ini."
        return self.send(msg)

    def bot_started(self, mode: str, dry_run: bool, threshold: int) -> bool:
        """Notifikasi bot mulai jalan."""
        msg = (
            f"🚀 <b>Bot dimulai</b>\n\n"
            f"⚙️ Mode: <b>{mode}</b>\n"
            f"🧪 Dry Run: <b>{'Ya' if dry_run else 'Tidak'}</b>\n"
            f"🎯 Threshold: <b>{threshold}/100</b>"
        )
        return self.send(msg)

    def error(self, context: str, detail: str) -> bool:
        """Notifikasi error."""
        msg = (
            f"🔥 <b>ERROR</b>\n\n"
            f"📍 <b>Lokasi:</b> {context}\n"
            f"💬 <b>Detail:</b> {detail}"
        )
        return self.send(msg)
