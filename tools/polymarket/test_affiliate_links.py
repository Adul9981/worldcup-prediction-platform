#!/usr/bin/env python3
"""Small self-test for Polymarket affiliate link generation."""

from affiliate_links import with_polymarket_affiliate


def main() -> int:
    cases = {
        "https://polymarket.com/event/world-cup-winner": "https://polymarket.com/event/world-cup-winner?via=serene77mc-g6kj",
        "https://polymarket.com/event/world-cup-winner?foo=bar": "https://polymarket.com/event/world-cup-winner?foo=bar&via=serene77mc-g6kj",
        "https://polymarket.com/event/world-cup-winner?via=old": "https://polymarket.com/event/world-cup-winner?via=serene77mc-g6kj",
        "": "",
    }
    for original, expected in cases.items():
        actual = with_polymarket_affiliate(original)
        if actual != expected:
            raise AssertionError(f"{original!r}: expected {expected!r}, got {actual!r}")
    print("affiliate link tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
