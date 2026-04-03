"""
polymarket.py — Mengambil data probabilitas dari Polymarket API.
"""

import requests
import logging

logger = logging.getLogger(__name__)

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API  = "https://clob.polymarket.com"


class PolymarketMonitor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "polymarket-forex-bot/1.0"})

    def get_market_odds(self, condition_id: str) -> dict | None:
        """
        Ambil probabilitas terkini untuk sebuah market.
        Returns: {"Yes": 0.72, "No": 0.28} atau None jika gagal.
        """
        try:
            # Coba CLOB API dulu (lebih real-time)
            result = self._fetch_from_clob(condition_id)
            if result:
                return result

            # Fallback ke Gamma API
            return self._fetch_from_gamma(condition_id)

        except Exception as e:
            logger.error(f"Error mengambil data Polymarket ({condition_id}): {e}")
            return None

    def _fetch_from_clob(self, condition_id: str) -> dict | None:
        """Ambil harga dari CLOB (order book) API."""
        try:
            url = f"{CLOB_API}/markets/{condition_id}"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            tokens = data.get("tokens", [])
            if not tokens:
                return None

            result = {}
            for token in tokens:
                outcome = token.get("outcome", "Unknown")
                price = float(token.get("price", 0))
                result[outcome] = price

            logger.debug(f"CLOB data untuk {condition_id}: {result}")
            return result if result else None

        except Exception as e:
            logger.debug(f"CLOB API gagal: {e}")
            return None

    def _fetch_from_gamma(self, condition_id: str) -> dict | None:
        """Ambil data dari Gamma (metadata) API."""
        try:
            url = f"{GAMMA_API}/markets"
            params = {"condition_id": condition_id}
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            markets = resp.json()

            if not markets:
                return None

            market = markets[0]
            outcomes    = market.get("outcomes", "[]")
            prices_str  = market.get("outcomePrices", "[]")

            import json
            outcomes_list = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
            prices_list   = json.loads(prices_str) if isinstance(prices_str, str) else prices_str

            result = {}
            for outcome, price in zip(outcomes_list, prices_list):
                result[outcome] = float(price)

            logger.debug(f"Gamma data untuk {condition_id}: {result}")
            return result if result else None

        except Exception as e:
            logger.debug(f"Gamma API gagal: {e}")
            return None

    def search_markets(self, keyword: str, limit: int = 10) -> list:
        """
        Cari market berdasarkan keyword — berguna untuk temukan condition_id.
        Contoh: poly.search_markets("fed rate cut")
        """
        try:
            url = f"{GAMMA_API}/markets"
            params = {"q": keyword, "active": "true", "limit": limit}
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            markets = resp.json()

            results = []
            for m in markets:
                results.append({
                    "name":         m.get("question", ""),
                    "condition_id": m.get("conditionId", ""),
                    "end_date":     m.get("endDate", ""),
                    "volume":       m.get("volume", 0),
                })
            return results

        except Exception as e:
            logger.error(f"Search markets error: {e}")
            return []
