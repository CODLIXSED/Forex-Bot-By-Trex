"""
search_markets.py — Script bantu untuk mencari condition_id di Polymarket.

Cara pakai:
    python search_markets.py "fed rate"
    python search_markets.py "bitcoin"
    python search_markets.py "election"
"""

import sys
from polymarket import PolymarketMonitor


def main():
    keyword = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "fed rate"
    print(f"\n🔍 Mencari market Polymarket: '{keyword}'\n")

    poly = PolymarketMonitor()
    markets = poly.search_markets(keyword, limit=10)

    if not markets:
        print("Tidak ada market ditemukan.")
        return

    print(f"{'No':<4} {'Name':<55} {'Condition ID':<45} {'Volume':>10}")
    print("-" * 120)
    for i, m in enumerate(markets, 1):
        name = m["name"][:53] + ".." if len(m["name"]) > 53 else m["name"]
        vol  = float(m["volume"]) if m["volume"] else 0
        print(f"{i:<4} {name:<55} {m['condition_id']:<45} ${vol:>10,.0f}")

    print(f"\nSalin condition_id yang diinginkan ke config.py → WATCHED_MARKETS")


if __name__ == "__main__":
    main()
