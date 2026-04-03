"""
forex.py — Koneksi ke OANDA REST API untuk eksekusi order Forex.
"""

import requests
import logging

logger = logging.getLogger(__name__)


class ForexTrader:
    def __init__(self, api_key: str, account_id: str, practice: bool = True):
        self.account_id = account_id
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        base = "https://api-fxtrade.oanda.com" if not practice else "https://api-fxpractice.oanda.com"
        self.base_url = f"{base}/v3/accounts/{account_id}"
        logger.info(f"ForexTrader init — {'PRACTICE' if practice else 'LIVE'} mode")

    def get_price(self, instrument: str) -> float | None:
        """Ambil harga terkini untuk instrument (misal: EUR_USD)."""
        try:
            url = f"{self.base_url}/pricing"
            params = {"instruments": instrument}
            resp = requests.get(url, headers=self.headers, params=params, timeout=10)
            resp.raise_for_status()
            prices = resp.json().get("prices", [])
            if prices:
                bid = float(prices[0]["bids"][0]["price"])
                ask = float(prices[0]["asks"][0]["price"])
                mid = (bid + ask) / 2
                logger.debug(f"Harga {instrument}: bid={bid}, ask={ask}, mid={mid}")
                return mid
        except Exception as e:
            logger.error(f"Gagal ambil harga {instrument}: {e}")
        return None

    def place_order(
        self,
        instrument: str,
        units: int,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> dict | None:
        """
        Buat market order.

        Args:
            instrument: misal "EUR_USD"
            units: positif = BUY, negatif = SELL
            stop_loss: harga stop loss (opsional)
            take_profit: harga take profit (opsional)
        """
        try:
            current_price = self.get_price(instrument)
            if not current_price:
                logger.error(f"Tidak bisa ambil harga untuk {instrument}")
                return None

            # Hitung SL/TP jika tidak diberikan eksplisit
            pip = 0.01 if "JPY" in instrument else 0.0001
            if units > 0:  # BUY
                sl = round(current_price - 30 * pip, 5) if stop_loss is None else stop_loss
                tp = round(current_price + 60 * pip, 5) if take_profit is None else take_profit
            else:  # SELL
                sl = round(current_price + 30 * pip, 5) if stop_loss is None else stop_loss
                tp = round(current_price - 60 * pip, 5) if take_profit is None else take_profit

            order = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units),
                    "stopLossOnFill": {"price": str(sl)},
                    "takeProfitOnFill": {"price": str(tp)},
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                }
            }

            url = f"{self.base_url}/orders"
            resp = requests.post(url, headers=self.headers, json=order, timeout=10)
            resp.raise_for_status()
            result = resp.json()

            trade = result.get("orderFillTransaction", {})
            logger.info(
                f"Order tereksekusi: {instrument} {units} units @ {trade.get('price')} "
                f"| SL: {sl} | TP: {tp}"
            )
            return trade

        except requests.HTTPError as e:
            logger.error(f"HTTP Error saat order: {e.response.text}")
        except Exception as e:
            logger.error(f"Error saat place_order: {e}")
        return None

    def get_open_trades(self) -> list:
        """Ambil daftar posisi yang sedang terbuka."""
        try:
            url = f"{self.base_url}/openTrades"
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            return resp.json().get("trades", [])
        except Exception as e:
            logger.error(f"Gagal ambil open trades: {e}")
            return []

    def close_trade(self, trade_id: str) -> bool:
        """Tutup posisi berdasarkan trade ID."""
        try:
            url = f"{self.base_url}/trades/{trade_id}/close"
            resp = requests.put(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            logger.info(f"Posisi {trade_id} berhasil ditutup.")
            return True
        except Exception as e:
            logger.error(f"Gagal tutup posisi {trade_id}: {e}")
            return False

    def get_account_summary(self) -> dict:
        """Ambil ringkasan akun (balance, P&L, dll)."""
        try:
            url = f"{self.base_url}/summary"
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.raise_for_status()
            account = resp.json().get("account", {})
            return {
                "balance":     account.get("balance"),
                "nav":         account.get("NAV"),
                "unrealized_pl": account.get("unrealizedPL"),
                "open_trades": account.get("openTradeCount"),
            }
        except Exception as e:
            logger.error(f"Gagal ambil account summary: {e}")
            return {}
