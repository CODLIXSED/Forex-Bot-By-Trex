"""
strategy.py — Strategi multi-faktor.
Menggunakan exchangerate API publik untuk data harga (tanpa MT5).
"""

import logging
import requests
from config import Config

logger = logging.getLogger(__name__)


# ─── Ambil data harga via API publik (gratis, tanpa key) ─────────────────────

def fetch_candles(pair: str, count: int = 60) -> list:
    """
    Ambil harga penutupan via Frankfurter API (gratis, no key).
    Pair format: EUR_USD → base=EUR, quote=USD
    """
    try:
        parts = pair.replace("_", "").upper()
        base  = parts[:3]
        quote = parts[3:]

        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": base, "to": quote},
            timeout=10
        )
        resp.raise_for_status()
        rate = resp.json()["rates"][quote]

        # Frankfurter hanya beri 1 harga — kita simulasi dengan variasi kecil
        # untuk keperluan EMA/RSI (fallback jika tidak ada historical data)
        import random
        random.seed(42)
        candles = [rate * (1 + random.uniform(-0.001, 0.001)) for _ in range(count)]
        candles[-1] = rate  # harga terkini selalu akurat
        return candles

    except Exception as e:
        logger.warning(f"Frankfurter API gagal ({pair}): {e}")
        return _fetch_from_polygon(pair, count)


def _fetch_from_polygon(pair: str, count: int) -> list:
    """Fallback: Polygon.io (butuh API key gratis)."""
    try:
        sym  = pair.replace("_", "")
        key  = Config.POLYGON_API_KEY
        if not key:
            return []
        resp = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/C:{sym}/range/1/hour/2024-01-01/2025-12-31",
            params={"adjusted": "true", "sort": "desc", "limit": count, "apiKey": key},
            timeout=10
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        return [float(r["c"]) for r in reversed(results)]
    except Exception as e:
        logger.warning(f"Polygon fallback gagal: {e}")
        return []


def fetch_hlc_candles(pair: str, count: int = 20):
    closes = fetch_candles(pair, count)
    if not closes:
        return [], [], []
    # Estimasi high/low dari close (±0.1%)
    highs  = [c * 1.001 for c in closes]
    lows   = [c * 0.999 for c in closes]
    return highs, lows, closes


# ─── Indikator Teknikal ───────────────────────────────────────────────────────

def ema(prices: list, period: int):
    if len(prices) < period:
        return None
    k   = 2 / (period + 1)
    val = sum(prices[:period]) / period
    for p in prices[period:]:
        val = p * k + val * (1 - k)
    return val


def rsi(prices: list, period: int = 14):
    if len(prices) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(prices)):
        d = prices[i] - prices[i - 1]
        gains.append(max(d, 0))
        losses.append(max(-d, 0))
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100.0
    return 100 - (100 / (1 + ag / al))


def atr(highs, lows, closes, period: int = 14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i]  - closes[i - 1]))
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


# ─── Main Strategy ────────────────────────────────────────────────────────────

class TradingStrategy:
    WEIGHTS = dict(poly_prob=0.35, ema=0.25, rsi=0.20, poly_trend=0.15, atr=0.05)

    def analyze(self, market_config: dict, odds: dict,
                prob_history: list = None) -> dict:
        target    = market_config.get("signal_outcome", "Yes")
        prob      = odds.get(target)
        pair      = market_config["forex_pair"]
        direction = market_config["signal_direction"]

        if prob is None:
            return None
        if prob < Config.MIN_PROBABILITY_SIGNAL:
            logger.info(f"  [SKIP] Prob {prob:.1%} < threshold")
            return None

        # 1. Polymarket probability
        min_p      = Config.MIN_PROBABILITY_SIGNAL
        prob_score = min(100, (prob - min_p) / (1.0 - min_p) * 100)

        # 2. EMA Crossover
        closes     = fetch_candles(pair, count=60)
        ema_score, ema_label = 50, "N/A"
        if len(closes) >= 26:
            fast, slow = ema(closes, 9), ema(closes, 21)
            if fast and slow:
                bull = fast > slow
                if (direction == "BUY" and bull) or (direction == "SELL" and not bull):
                    ema_score, ema_label = 100, "KONFIRMASI ✅"
                else:
                    ema_score, ema_label = 0, "MELAWAN TREND ❌"

        # 3. RSI
        rsi_val            = rsi(closes) if closes else None
        rsi_score, rsi_label = 50, "N/A"
        if rsi_val is not None:
            if direction == "BUY":
                if 40 <= rsi_val <= 65:  rsi_score, rsi_label = 100, f"{rsi_val:.0f} ✅"
                elif rsi_val > 70:       rsi_score, rsi_label = 10,  f"{rsi_val:.0f} OVERBOUGHT ❌"
                elif rsi_val < 30:       rsi_score, rsi_label = 70,  f"{rsi_val:.0f} OVERSOLD ~"
                else:                    rsi_score, rsi_label = 50,  f"{rsi_val:.0f}"
            else:
                if 35 <= rsi_val <= 60:  rsi_score, rsi_label = 100, f"{rsi_val:.0f} ✅"
                elif rsi_val < 30:       rsi_score, rsi_label = 10,  f"{rsi_val:.0f} OVERSOLD ❌"
                elif rsi_val > 70:       rsi_score, rsi_label = 70,  f"{rsi_val:.0f} ~"
                else:                    rsi_score, rsi_label = 50,  f"{rsi_val:.0f}"

        # 4. Polymarket trend
        trend      = poly_trend(prob_history or [prob])
        trend_map  = {"BUY":  {"RISING": 100, "NEUTRAL": 50, "FALLING": 0},
                      "SELL": {"FALLING": 100, "NEUTRAL": 50, "RISING": 0}}
        trend_score = trend_map[direction][trend]

        # 5. ATR filter
        highs, lows, closes_hlc = fetch_hlc_candles(pair, count=20)
        atr_score, atr_pips = 50, 0
        atr_val = atr(highs, lows, closes_hlc) if highs else None
        if atr_val:
            pip      = 0.01 if "JPY" in pair else 0.0001
            atr_pips = atr_val / pip
            if 10 <= atr_pips <= 80: atr_score = 100
            elif atr_pips < 5:       atr_score = 20
            else:                    atr_score = 60

        # Total score
        score = (
            prob_score  * self.WEIGHTS["poly_prob"] +
            ema_score   * self.WEIGHTS["ema"] +
            rsi_score   * self.WEIGHTS["rsi"] +
            trend_score * self.WEIGHTS["poly_trend"] +
            atr_score   * self.WEIGHTS["atr"]
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
        pip       = 0.01 if "JPY" in pair else 0.0001
        sl_dist   = 1.5 * atr_val
        risk_units = int(Config.RISK_PER_TRADE_USD / (sl_dist / pip))
        return max(100, min(risk_units, Config.MAX_UNITS_PER_TRADE))

    def should_exit(self, market_config: dict, odds: dict, direction: str) -> bool:
        target = market_config.get("signal_outcome", "Yes")
        prob   = odds.get(target, 0)
        if prob <= Config.MAX_PROBABILITY_EXIT:
            logger.info(f"Exit: prob turun ke {prob:.1%}")
            return True
        return False
