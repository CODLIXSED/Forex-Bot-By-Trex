"""
forex.py — Koneksi ke Exness via MetaTrader5 API.

Kredensial akun demo:
  Login  : 433418879
  Server : Exness-MT5Trial7
"""

import logging
import subprocess
import sys
import os

logger = logging.getLogger(__name__)

# Auto-install MetaTrader5 jika belum ada (untuk GitHub Actions)
try:
    import MetaTrader5 as mt5
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "MetaTrader5"])
    import MetaTrader5 as mt5


class ForexTrader:
    def __init__(self, login: int, password: str, server: str):
        self.login    = login
        self.password = password
        self.server   = server
        self._connected = False
        self._connect()

    def _connect(self):
        """Konek ke MT5."""
        if not mt5.initialize():
            logger.error(f"MT5 initialize gagal: {mt5.last_error()}")
            return

        authorized = mt5.login(
            login=self.login,
            password=self.password,
            server=self.server
        )
        if authorized:
            info = mt5.account_info()
            logger.info(f"✅ MT5 terhubung: #{info.login} | "
                        f"Balance: ${info.balance:.2f} | Server: {info.server}")
            self._connected = True
        else:
            logger.error(f"❌ MT5 login gagal: {mt5.last_error()}")

    def get_price(self, symbol: str) -> float | None:
        """Ambil harga terkini."""
        if not self._connected:
            return None
        # Konversi format: EUR_USD → EURUSD
        symbol = symbol.replace("_", "")
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            return (tick.bid + tick.ask) / 2
        logger.error(f"Gagal ambil harga {symbol}: {mt5.last_error()}")
        return None

    def place_order(self, instrument: str, units: int,
                    stop_loss: float = None,
                    take_profit: float = None) -> dict | None:
        """
        Buat market order.
        units positif = BUY, negatif = SELL
        """
        if not self._connected:
            logger.error("MT5 tidak terhubung.")
            return None

        symbol = instrument.replace("_", "")
        action = mt5.ORDER_TYPE_BUY if units > 0 else mt5.ORDER_TYPE_SELL
        volume = abs(units) / 100000  # konversi units ke lot (1 lot = 100000)
        volume = max(0.01, round(volume, 2))  # minimum 0.01 lot

        # Ambil harga
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"Tidak bisa ambil tick {symbol}")
            return None

        price = tick.ask if units > 0 else tick.bid

        # Hitung SL/TP otomatis jika tidak diberikan
        pip  = 0.01 if "JPY" in symbol else 0.0001
        sl   = stop_loss   or (price - 30 * pip if units > 0 else price + 30 * pip)
        tp   = take_profit or (price + 60 * pip if units > 0 else price - 60 * pip)

        request = {
            "action":     mt5.TRADE_ACTION_DEAL,
            "symbol":     symbol,
            "volume":     volume,
            "type":       action,
            "price":      price,
            "sl":         round(sl, 5),
            "tp":         round(tp, 5),
            "deviation":  20,
            "magic":      20250101,
            "comment":    "polymarket-bot",
            "type_time":  mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"✅ Order berhasil: {symbol} {volume} lot @ {result.price}")
            return {"price": str(result.price), "order": result.order}
        else:
            logger.error(f"❌ Order gagal: {result.retcode if result else mt5.last_error()}")
            return None

    def get_open_trades(self) -> list:
        """Ambil posisi terbuka."""
        if not self._connected:
            return []
        positions = mt5.positions_get()
        return list(positions) if positions else []

    def get_account_summary(self) -> dict:
        """Ringkasan akun."""
        if not self._connected:
            return {}
        info = mt5.account_info()
        if info:
            return {
                "balance":       info.balance,
                "nav":           info.equity,
                "unrealized_pl": info.profit,
                "open_trades":   info.positions_total,
            }
        return {}

    def get_candles(self, symbol: str, timeframe=None, count: int = 60) -> list:
        """Ambil data candle untuk indikator teknikal."""
        if not self._connected:
            return []
        sym = symbol.replace("_", "")
        tf  = timeframe or mt5.TIMEFRAME_H1
        rates = mt5.copy_rates_from_pos(sym, tf, 0, count)
        if rates is None:
            return []
        return [float(r["close"]) for r in rates]

    def get_hlc_candles(self, symbol: str, timeframe=None, count: int = 20):
        """Ambil high, low, close untuk ATR."""
        if not self._connected:
            return [], [], []
        sym = symbol.replace("_", "")
        tf  = timeframe or mt5.TIMEFRAME_H1
        rates = mt5.copy_rates_from_pos(sym, tf, 0, count)
        if rates is None:
            return [], [], []
        highs  = [float(r["high"])  for r in rates]
        lows   = [float(r["low"])   for r in rates]
        closes = [float(r["close"]) for r in rates]
        return highs, lows, closes

    def disconnect(self):
        mt5.shutdown()
        logger.info("MT5 disconnected.")
