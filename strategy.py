"""
strategy.py — Strategi multi-faktor untuk akurasi lebih tinggi.

Faktor yang digunakan:
1. Probabilitas Polymarket (sentiment pasar prediksi)
2. Trend teknikal (EMA crossover)
3. Momentum (RSI)
4. Volatilitas (ATR-based filter + position sizing)
5. Polymarket trend (apakah probabilitas sedang naik/turun)

Skor gabungan 0-100. Entry hanya jika skor >= MIN_SCORE_THRESHOLD.
"""

import logging
import requests
from config import Config

logger = logging.getLogger(__name__)


# ─── OANDA Price Fetcher ──────────────────────────────────────────────────────

def fetch_candles(instrument: str, count: int = 60, granularity: str = "H1",
                  api_key: str = "", practice: bool = True) -> list:
    base = "https://api-fxpractice.oanda.com" if practice else "https://api-fxtrade.oanda.com"
    url = f"{base}/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"count": count, "granularity": granularity, "price": "M"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        candles = [c for c in resp.json().get("candles", []) if c.get("complete")]
        return [float(c["mid"]["c"]) for c in candles]
    except Exception as e:
        logger.warning(f"Gagal ambil candle {instrument}: {e}")
        return []


def fetch_hlc_candles(instrument: str, count: int = 20, granularity: str = "H1",
                      api_key: str = "", practice: bool = True):
    base = "https://api-fxpractice.oanda.com" if practice else "https://api-fxtrade.oanda.com"
    url = f"{base}/v3/instruments/{instrument}/candles"
    headers = {"Authorization": f"Bearer {api_key}"}
    params = {"count": count, "granularity": granularity, "price": "M"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        candles = [c for c in resp.json().get("candles", []) if c.get("complete")]
        highs  = [float(c["mid"]["h"]) for c in candles]
        lows   = [float(c["mid"]["l"]) for c in candles]
        closes = [float(c["mid"]["c"]) for c in candles]
        return highs, lows, closes
    except Exception as e:
        logger.warning(f"Gagal ambil HLC {instrument}: {e}")
        return [], [], []


# ─── Indikator Teknikal ───────────────────────────────────────────────────────

def ema(prices: list, period: int):
    if len(prices) < period:
        return None
    k = 2 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val


def rsi(prices: list, period: int = 14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))


def atr(highs: list, lows: list, closes: list, period: int = 14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    return sum(trs[-period:]) / period


def poly_trend(history: list) -> str:
    if len(history) < 3:
        return "NEUTRAL"
    if history[-1] > history[0] + 0.02:
        return "RISING"
    if history[-1] < history[0] - 0.02:
        return "FALLING"
    return "NEUTRAL"


# ─── Main Strategy Class ──────────────────────────────────────────────────────

class TradingStrategy:
    """
    Weighted scoring strategy:

    ┌──────────────────────────────┬────────┐
    │ Faktor                       │ Bobot  │
    ├──────────────────────────────┼────────┤
    │ Probabilitas Polymarket      │  35%   │
    │ EMA Crossover (trend)        │  25%   │
    │ RSI (momentum)               │  20%   │
    │ Polymarket trend             │  15%   │
    │ ATR filter (volatilitas)     │   5%   │
    └──────────────────────────────┴────────┘

    Entry hanya jika total skor >= MIN_SCORE_THRESHOLD (default 60).
    """

    WEIGHTS = dict(poly_prob=0.35, ema=0.25, rsi=0.20, poly_trend=0.15, atr=0.05)

    def analyze(self, market_config: dict, odds: dict,
                prob_history: list = None) -> dict:
        target   = market_config.get("signal_outcome", "Yes")
        prob     = odds.get(target)
        pair     = market_config["forex_pair"]
        direction = market_config["signal_direction"]

        if prob is None:
            return None
        if prob < Config.MIN_PROBABILITY_SIGNAL:
            logger.info(f"  [SKIP] Prob {prob:.1%} < threshold")
            return None

        # ── 1. Polymarket probability score ──────────────────────────────
        min_p = Config.MIN_PROBABILITY_SIGNAL
        prob_score = min(100, (prob - min_p) / (1.0 - min_p) * 100)

        # ── 2. EMA Crossover ──────────────────────────────────────────────
        closes = fetch_candles(pair, count=60, api_key=Config.OANDA_API_KEY,
                               practice=Config.PRACTICE_MODE)
        ema_score, ema_label = 50, "N/A"
        if len(closes) >= 26:
            fast, slow = ema(closes, 9), ema(closes, 21)
            if fast and slow:
                bull = fast > slow
                if (direction == "BUY" and bull) or (direction == "SELL" and not bull):
                    ema_score, ema_label = 100, "KONFIRMASI ✅"
                else:
                    ema_score, ema_label = 0, "MELAWAN TREND ❌"

        # ── 3. RSI ───────────────────────────────────────────────────────
        rsi_val = rsi(closes) if closes else None
        rsi_score, rsi_label = 50, "N/A"
        if rsi_val is not None:
            if direction == "BUY":
                if 40 <= rsi_val <= 65:   rsi_score, rsi_label = 100, f"{rsi_val:.0f} ✅"
                elif rsi_val > 70:        rsi_score, rsi_label = 10,  f"{rsi_val:.0f} OVERBOUGHT ❌"
                elif rsi_val < 30:        rsi_score, rsi_label = 70,  f"{rsi_val:.0f} OVERSOLD ~"
                else:                     rsi_score, rsi_label = 50,  f"{rsi_val:.0f}"
            else:
                if 35 <= rsi_val <= 60:   rsi_score, rsi_label = 100, f"{rsi_val:.0f} ✅"
                elif rsi_val < 30:        rsi_score, rsi_label = 10,  f"{rsi_val:.0f} OVERSOLD ❌"
                elif rsi_val > 70:        rsi_score, rsi_label = 70,  f"{rsi_val:.0f} ~"
                else:                     rsi_score, rsi_label = 50,  f"{rsi_val:.0f}"

        # ── 4. Polymarket trend ───────────────────────────────────────────
        trend = poly_trend(prob_history or [prob])
        trend_map_buy  = {"RISING": 100, "NEUTRAL": 50, "FALLING": 0}
        trend_map_sell = {"FALLING": 100, "NEUTRAL": 50, "RISING": 0}
        trend_score = (trend_map_buy if direction == "BUY" else trend_map_sell)[trend]

        # ── 5. ATR filter ─────────────────────────────────────────────────
        pip = 0.01 if "JPY" in pair else 0.0001
        highs, lows, closes_hlc = fetch_hlc_candles(
            pair, count=20, api_key=Config.OANDA_API_KEY,
            practice=Config.PRACTICE_MODE)
        atr_val = atr(highs, lows, closes_hlc) if highs else None
        atr_score, atr_pips = 50, 0
        if atr_val:
            atr_pips = atr_val / pip
            if 10 <= atr_pips <= 80: atr_score = 100
            elif atr_pips < 5:       atr_score = 20
            else:                    atr_score = 60

        # ── Total score ───────────────────────────────────────────────────
        score = (
            prob_score   * self.WEIGHTS["poly_prob"] +
            ema_score    * self.WEIGHTS["ema"] +
            rsi_score    * self.WEIGHTS["rsi"] +
            trend_score  * self.WEIGHTS["poly_trend"] +
            atr_score    * self.WEIGHTS["atr"]
        )

        logger.info(f"  ┌─ [{pair} {direction}]")
        logger.info(f"  │  Polymarket : {prob:.1%}  → {prob_score:.0f}/100")
        logger.info(f"  │  EMA        : {ema_label}  → {ema_score:.0f}/100")
        logger.info(f"  │  RSI        : {rsi_label}  → {rsi_score:.0f}/100")
        logger.info(f"  │  Poly Trend : {trend}  → {trend_score:.0f}/100")
        logger.info(f"  │  ATR        : {atr_pips:.1f} pips  → {atr_score:.0f}/100")
        logger.info(f"  └─ TOTAL: {score:.1f}/100  (min: {Config.MIN_SCORE_THRESHOLD})")

        if score < Config.MIN_SCORE_THRESHOLD:
            logger.info(f"  ❌ Skor tidak cukup, skip.")
            return None

        logger.info(f"  ✅ SINYAL VALID — {direction} {pair}")
        units = self._position_size(atr_val, pair)

        return {
            "pair": pair, "action": direction, "units": units,
            "probability": prob, "score": score,
            "market_name": market_config["name"],
            "rsi": rsi_val, "ema_signal": ema_label, "atr": atr_val,
        }

    def _position_size(self, atr_val, pair: str) -> int:
        if not atr_val:
            return Config.UNITS_PER_TRADE
        pip = 0.01 if "JPY" in pair else 0.0001
        sl_distance = 1.5 * atr_val
        risk_units = int(Config.RISK_PER_TRADE_USD / (sl_distance / pip))
        return max(100, min(risk_units, Config.MAX_UNITS_PER_TRADE))

    def should_exit(self, market_config: dict, odds: dict, direction: str) -> bool:
        target = market_config.get("signal_outcome", "Yes")
        prob = odds.get(target, 0)
        if prob <= Config.MAX_PROBABILITY_EXIT:
            logger.info(f"Exit: prob turun ke {prob:.1%}")
            return True
        return False
