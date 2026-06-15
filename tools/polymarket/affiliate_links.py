"""Polymarket affiliate link helpers."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


POLYMARKET_AFFILIATE_VIA = "serene77mc-g6kj"


def with_polymarket_affiliate(url: str, via: str = POLYMARKET_AFFILIATE_VIA) -> str:
    """Return a Polymarket URL with the required affiliate code."""
    if not url:
        return ""
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["via"] = via
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
