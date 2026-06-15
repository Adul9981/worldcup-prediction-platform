#!/usr/bin/env python3
"""Read-only Polymarket World Cup market discovery.

Fetches active Gamma events, filters likely 2026 World Cup markets, and writes
normalized JSON/CSV snapshots. No credentials, wallet, or trading endpoint is
used.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GAMMA_BASE = "https://gamma-api.polymarket.com"
DEFAULT_OUTPUT_DIR = Path("data/polymarket")

WORLD_CUP_KEYWORDS = [
    "world cup",
    "fifa",
    "2026",
    "mexico",
    "south africa",
    "korea",
    "czech",
    "canada",
    "bosnia",
    "qatar",
    "switzerland",
    "brazil",
    "morocco",
    "haiti",
    "scotland",
    "united states",
    "usa",
    "paraguay",
    "australia",
    "turkey",
    "turkiye",
    "germany",
    "curacao",
    "ivory coast",
    "ecuador",
    "netherlands",
    "japan",
    "sweden",
    "tunisia",
    "belgium",
    "egypt",
    "iran",
    "new zealand",
    "spain",
    "cape verde",
    "saudi",
    "uruguay",
    "france",
    "senegal",
    "iraq",
    "norway",
    "argentina",
    "algeria",
    "austria",
    "jordan",
    "portugal",
    "congo",
    "uzbekistan",
    "colombia",
    "england",
    "croatia",
    "ghana",
    "panama",
]

MATCH_TICKER_RE = re.compile(r"KXWCGAME-[A-Z0-9]+", re.IGNORECASE)


@dataclass
class NormalizedMarket:
    discovered_at: str
    platform: str
    source: str
    event_id: str
    event_slug: str
    event_title: str
    market_id: str
    market_slug: str
    question: str
    event_type: str
    active: bool
    closed: bool
    accepting_orders: str
    end_date: str
    volume: float
    volume_24hr: float
    liquidity: float
    open_interest: float
    best_bid: str
    best_ask: str
    last_trade_price: str
    outcome_prices: str
    outcomes: str
    url: str
    matched_keywords: str
    notes: str


def fetch_json(path: str, params: dict[str, Any], timeout: int) -> Any:
    url = f"{GAMMA_BASE}{path}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "worldcup-prediction-ops/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def text_blob(event: dict[str, Any], market: dict[str, Any] | None = None) -> str:
    market = market or {}
    fields = [
        event.get("title"),
        event.get("slug"),
        event.get("description"),
        event.get("ticker"),
        market.get("question"),
        market.get("slug"),
        market.get("description"),
        market.get("ticker"),
        market.get("groupItemTitle"),
    ]
    tags = event.get("tags") or []
    for tag in tags:
        if isinstance(tag, dict):
            fields.extend([tag.get("label"), tag.get("slug")])
    series = event.get("series") or []
    for item in series:
        if isinstance(item, dict):
            fields.extend([item.get("title"), item.get("slug"), item.get("ticker")])
    return " ".join(str(field) for field in fields if field).lower()


def is_worldcup_related(event: dict[str, Any], market: dict[str, Any] | None = None) -> tuple[bool, list[str]]:
    blob = text_blob(event, market)
    matched = [keyword for keyword in WORLD_CUP_KEYWORDS if keyword in blob]
    has_wc_ticker = bool(MATCH_TICKER_RE.search(blob))
    has_world_cup = "world cup" in blob or "fifa" in blob or has_wc_ticker
    if has_world_cup:
        return True, sorted(set(matched + (["kxwcgame"] if has_wc_ticker else [])))
    return False, []


def classify_event(event: dict[str, Any], market: dict[str, Any]) -> str:
    blob = text_blob(event, market)
    ticker = f"{event.get('ticker', '')} {market.get('ticker', '')}".upper()
    question = str(market.get("question") or event.get("title") or "").lower()

    if "relocat" in blob or "scheduled in the us" in blob:
        return "special_event"
    if "world cup winner" in blob or "win the 2026 fifa world cup" in question:
        return "champion_or_outright"
    if "group" in blob or "qualify" in blob or "advance" in blob:
        return "group_or_qualification"
    if "top scorer" in blob or "golden boot" in blob or "player" in blob:
        return "player_prop"
    if "KXWCGAME-" in ticker:
        return "single_match_winner"
    if "yes " in question and "," in question:
        return "multi_leg_or_parlay"
    return "unclear_worldcup"


def normalize_event(event: dict[str, Any], discovered_at: str) -> list[NormalizedMarket]:
    rows: list[NormalizedMarket] = []
    markets = event.get("markets") or []
    if not markets:
        related, matched = is_worldcup_related(event)
        if related:
            rows.append(
                NormalizedMarket(
                    discovered_at=discovered_at,
                    platform="polymarket",
                    source="gamma_events",
                    event_id=str(event.get("id") or ""),
                    event_slug=str(event.get("slug") or ""),
                    event_title=str(event.get("title") or ""),
                    market_id="",
                    market_slug="",
                    question=str(event.get("title") or ""),
                    event_type="event_only",
                    active=bool(event.get("active")),
                    closed=bool(event.get("closed")),
                    accepting_orders="",
                    end_date=str(event.get("endDate") or ""),
                    volume=as_float(event.get("volume")),
                    volume_24hr=as_float(event.get("volume24hr")),
                    liquidity=as_float(event.get("liquidity")),
                    open_interest=as_float(event.get("openInterest")),
                    best_bid="",
                    best_ask="",
                    last_trade_price="",
                    outcome_prices="",
                    outcomes="",
                    url=f"https://polymarket.com/event/{event.get('slug')}",
                    matched_keywords=";".join(matched),
                    notes="event has no nested markets in response",
                )
            )
        return rows

    for market in markets:
        related, matched = is_worldcup_related(event, market)
        if not related:
            continue
        rows.append(
            NormalizedMarket(
                discovered_at=discovered_at,
                platform="polymarket",
                source="gamma_events",
                event_id=str(event.get("id") or ""),
                event_slug=str(event.get("slug") or ""),
                event_title=str(event.get("title") or ""),
                market_id=str(market.get("id") or ""),
                market_slug=str(market.get("slug") or ""),
                question=str(market.get("question") or event.get("title") or ""),
                event_type=classify_event(event, market),
                active=bool(market.get("active", event.get("active"))),
                closed=bool(market.get("closed", event.get("closed"))),
                accepting_orders=str(market.get("acceptingOrders", "")),
                end_date=str(market.get("endDate") or event.get("endDate") or ""),
                volume=as_float(market.get("volume", event.get("volume"))),
                volume_24hr=as_float(market.get("volume24hr", event.get("volume24hr"))),
                liquidity=as_float(market.get("liquidity", event.get("liquidity"))),
                open_interest=as_float(event.get("openInterest")),
                best_bid=str(market.get("bestBid", "")),
                best_ask=str(market.get("bestAsk", "")),
                last_trade_price=str(market.get("lastTradePrice", "")),
                outcome_prices=str(market.get("outcomePrices", "")),
                outcomes=str(market.get("outcomes", "")),
                url=f"https://polymarket.com/event/{event.get('slug')}",
                matched_keywords=";".join(matched),
                notes="",
            )
        )
    return rows


def fetch_events(limit: int, pages: int, timeout: int, sleep_seconds: float) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for page in range(pages):
        offset = page * limit
        payload = fetch_json(
            "/events",
            {
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset,
                "order": "volume_24hr",
                "ascending": "false",
            },
            timeout,
        )
        if isinstance(payload, dict):
            batch = payload.get("events") or payload.get("data") or []
            has_more = bool(payload.get("has_more"))
        elif isinstance(payload, list):
            batch = payload
            has_more = len(batch) >= limit
        else:
            batch = []
            has_more = False
        events.extend(event for event in batch if isinstance(event, dict))
        if not has_more or not batch:
            break
        if sleep_seconds:
            time.sleep(sleep_seconds)
    return events


def write_markdown_summary(rows: list[NormalizedMarket], output_dir: Path, discovered_at: str, summary: dict[str, Any]) -> Path:
    path = output_dir / "latest_polymarket_worldcup_summary.md"
    lines = [
        "# Polymarket World Cup Market Discovery",
        "",
        f"- Discovered at UTC: `{discovered_at}`",
        f"- Total World Cup markets: `{summary['total_worldcup_markets']}`",
        f"- Actionable markets: `{summary['actionable_markets']}`",
        "",
        "## By Type",
        "",
    ]
    for event_type, count in sorted(summary["by_type"].items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- `{event_type}`: {count}")
    lines.extend(["", "## Top By Activity", ""])
    for idx, item in enumerate(summary["top_by_activity"], start=1):
        lines.extend(
            [
                f"{idx}. {item['question']}",
                f"   - Type: `{item['event_type']}`",
                f"   - 24h volume: `{item['volume_24hr']}`",
                f"   - Total volume: `{item['volume']}`",
                f"   - Liquidity: `{item['liquidity']}`",
                f"   - Bid/ask: `{item['best_bid']}` / `{item['best_ask']}`",
                f"   - URL: {item['url']}",
            ]
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This is read-only discovery from Polymarket Gamma API.",
            "- No wallet, private key, order placement, bridge, or gasless transaction is used.",
            "- Country names alone do not trigger inclusion; markets must explicitly mention World Cup/FIFA or a World Cup game ticker.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_outputs(rows: list[NormalizedMarket], output_dir: Path, discovered_at: str) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = discovered_at.replace(":", "").replace("-", "").replace("+", "Z")
    json_path = output_dir / f"polymarket_worldcup_markets_{stamp}.json"
    csv_path = output_dir / f"polymarket_worldcup_markets_{stamp}.csv"
    latest_path = output_dir / "latest_polymarket_worldcup_markets.csv"

    data = [asdict(row) for row in rows]
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    fieldnames = list(asdict(rows[0]).keys()) if rows else list(NormalizedMarket.__dataclass_fields__.keys())
    for path in (csv_path, latest_path):
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
    return json_path, csv_path, latest_path


def summarize(rows: list[NormalizedMarket]) -> dict[str, Any]:
    by_type: dict[str, int] = {}
    actionable = 0
    for row in rows:
        by_type[row.event_type] = by_type.get(row.event_type, 0) + 1
        if row.active and not row.closed and row.accepting_orders.lower() != "false":
            actionable += 1
    top = sorted(rows, key=lambda row: (row.volume_24hr, row.volume, row.liquidity), reverse=True)[:10]
    return {
        "total_worldcup_markets": len(rows),
        "actionable_markets": actionable,
        "by_type": by_type,
        "top_by_activity": [
            {
                "question": row.question,
                "event_type": row.event_type,
                "volume_24hr": row.volume_24hr,
                "volume": row.volume,
                "liquidity": row.liquidity,
                "best_bid": row.best_bid,
                "best_ask": row.best_ask,
                "url": row.url,
            }
            for row in top
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=500, help="Gamma events page size, max 500.")
    parser.add_argument("--pages", type=int, default=10, help="Maximum pages to scan.")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout seconds.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Delay between pages.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    discovered_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    try:
        events = fetch_events(min(args.limit, 500), args.pages, args.timeout, args.sleep)
    except Exception as exc:  # noqa: BLE001 - command-line tool should report all fetch failures clearly.
        print(f"Fetch failed: {exc}", file=sys.stderr)
        return 2

    rows: list[NormalizedMarket] = []
    seen: set[tuple[str, str]] = set()
    for event in events:
        for row in normalize_event(event, discovered_at):
            key = (row.event_id, row.market_id or row.question)
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)

    summary = summarize(rows)
    json_path, csv_path, latest_path = write_outputs(rows, args.output_dir, discovered_at)
    summary_path = write_markdown_summary(rows, args.output_dir, discovered_at, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote JSON: {json_path}")
    print(f"Wrote CSV: {csv_path}")
    print(f"Wrote latest CSV: {latest_path}")
    print(f"Wrote summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
