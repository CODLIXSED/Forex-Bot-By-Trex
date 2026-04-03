"""
forex.py — Koneksi ke Exness via TradeLocker HTTP API.
Tidak butuh MetaTrader5 — berjalan di Linux/GitHub Actions.
"""

import requests
import logging

logger = logging.getLogger(__name__)

# TradeLocker adalah platform web Exness yang punya REST API
TRADELOCKER_BASE = "https://demo.tradelocker.com/backend-service"


class ForexTrader:
    def __init__(self, login: int, password: str, server: str):
        self.login    = str(login)
        self.password = password
        self.server   = server
        self.session  = requests.Session()
        self.token    = None
        self.acc_id   = None
        self.acc_num  = None
        self._connect()

    def _connect(self):
        """Login ke TradeLocker dan ambil token."""
        try:
            resp = self.session.post(
                f"{TRADELOCKER_BASE}/auth/jwt/token",
                json={
                    "email":       self.login,
                    "password":    self.password,
                    "server":      self.server,
                },
                timeout=15
            )
            resp.raise_for_status()
            data = resp.json()
            self.token = data.get("accessToken")

            if not self.token:
                logger.error(f"Login gagal: {data}")
                return

            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Content-Type":  "application/json",
            })

            # Ambil account info
            acc_resp = self.session.get(
                f"{TRADELOCKER_BASE}/auth/jwt/all-accounts",
                timeout=10
            )
            acc_resp.raise_for_status()
            accounts = acc_resp.json().get("accounts", [])
            if accounts:
                self.acc_id  = accounts[0]["id"]
                self.acc_num = accounts[0]["accNum"]
                logger.info(f"✅ TradeLocker terhubung: akun #{self.acc_num}")
            else:
                logger.error("Tidak ada akun ditemukan.")

        except Exception as e:
            logger.error(f"Koneksi TradeLocker gagal: {e}")

    def get_price(self, symbol: str) -> float | None:
        """Ambil harga terkini."""
        if not self.token or not self.acc_id:
            return None
        sym = symbol.replace("_", "")
        try:
            resp = self.session.get(
                f"{TRADELOCKER_BASE}/trade/quotes",
                params={"symbol": sym, "accNum": self.acc_num},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            bid = float(data.get("bid", 0))
            ask = float(data.get("ask", 0))
            return (bid + ask) / 2
        except Exception as e:
            logger.error(f"Gagal ambil harga {sym}: {e}")
            return None

    def place_order(self, instrument: str, units: int,
                    stop_loss: float = None,
                    take_profit: float = None) -> dict | None:
        """Buat market order. units positif=BUY, negatif=SELL."""
        if not self.token or not self.acc_id:
            logger.error("Tidak terhubung ke TradeLocker.")
            return None

        sym    = instrument.replace("_", "")
        side   = "buy" if units > 0 else "sell"
        volume = abs(units) / 100000
        volume = max(0.01, round(volume, 2))

        price = self.get_price(instrument)
        if not price:
            return None

        pip = 0.01 if "JPY" in sym else 0.0001
        sl  = stop_loss   or (price - 30 * pip if units > 0 else price + 30 * pip)
        tp  = take_profit or (price + 60 * pip if units > 0 else price - 60 * pip)

        try:
            resp = self.session.post(
                f"{TRADELOCKER_BASE}/trade/orders",
                json={
                    "accNum":      self.acc_num,
                    "instrument":  sym,
                    "type":        "market",
                    "side":        side,
                    "qty":         volume,
                    "stopLoss":    round(sl, 5),
                    "takeProfit":  round(tp, 5),
                },
                timeout=15
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(f"✅ Order: {sym} {side} {volume} lot")
            return {"price": str(price), "order": result}
        except Exception as e:
            logger.error(f"Order gagal: {e}")
            return None

    def get_account_summary(self) -> dict:
        """Ringkasan akun."""
        if not self.token or not self.acc_id:
            return {}
        try:
            resp = self.session.get(
                f"{TRADELOCKER_BASE}/trade/accounts/{self.acc_id}",
                params={"accNum": self.acc_num},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "balance":       data.get("balance"),
                "nav":           data.get("equity"),
                "unrealized_pl": data.get("unrealizedPnl"),
                "open_trades":   data.get("positionsCount"),
            }
        except Exception as e:
            logger.error(f"Gagal ambil summary: {e}")
            return {}

    def disconnect(self):
        logger.info("Trader disconnected.")
