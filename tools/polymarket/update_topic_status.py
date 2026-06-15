#!/usr/bin/env python3
"""Build prediction market topic library and status snapshots from Polymarket data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from affiliate_links import POLYMARKET_AFFILIATE_VIA, with_polymarket_affiliate


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_OUTPUT = Path("data/polymarket/latest_topic_status_summary.md")
DEFAULT_CURRENT_CSV = Path("data/polymarket/latest_prediction_market_topics.csv")
DEFAULT_CHANGES_CSV = Path("data/polymarket/latest_topic_changes.csv")
DEFAULT_CHANGES_JSON = Path("data/polymarket/latest_topic_changes.json")

LOW_LIQUIDITY_THRESHOLD = 100.0
LOW_VOLUME_24H_THRESHOLD = 100.0
HOT_VOLUME_24H_THRESHOLD = 1_000_000.0
PRICE_MOVE_THRESHOLD = 0.01
VOLUME_GROWTH_THRESHOLD = 10_000.0


@dataclass
class TopicRow:
    topic_id: str
    platform: str
    market_id: str
    event_slug: str
    market_slug: str
    title: str
    topic_type: str
    canonical_team: str
    group_code: str
    first_seen_at: str
    latest_seen_at: str
    current_status: str
    lifecycle_note: str
    url: str
    affiliate_url: str


@dataclass
class StatusSnapshot:
    snapshot_id: str
    topic_id: str
    captured_at: str
    active: int
    closed: int
    accepting_orders: str
    status: str
    best_bid: str
    best_ask: str
    last_trade_price: str
    volume: float
    volume_24hr: float
    liquidity: float
    open_interest: float
    status_note: str


def as_float(value: Any) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def as_int_bool(value: Any) -> int:
    return 1 if str(value).strip().lower() in {"1", "true", "yes"} else 0


def topic_id(platform: str, market_id: str) -> str:
    return hashlib.sha1(f"{platform}:{market_id}".encode("utf-8")).hexdigest()[:16]


def snapshot_id(topic: str, captured_at: str) -> str:
    return hashlib.sha1(f"{topic}:{captured_at}".encode("utf-8")).hexdigest()[:20]


def latest_snapshot_at(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT MAX(discovered_at) FROM polymarket_markets").fetchone()
    return str(row[0] or "")


def ensure_schema_migrations(conn: sqlite3.Connection) -> None:
    """Apply small additive migrations for existing local databases."""
    columns = {
        str(row[1])
        for row in conn.execute("PRAGMA table_info(prediction_market_topics)").fetchall()
    }
    if "affiliate_url" not in columns:
        conn.execute("ALTER TABLE prediction_market_topics ADD COLUMN affiliate_url TEXT")


def previous_snapshot_at(conn: sqlite3.Connection, latest_at: str) -> str:
    row = conn.execute(
        "SELECT MAX(discovered_at) FROM polymarket_markets WHERE discovered_at < ?",
        (latest_at,),
    ).fetchone()
    return str(row[0] or "")


def fetch_markets(conn: sqlite3.Connection, discovered_at: str) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT pm.*, ctm.canonical_team, ctm.group_code, ctm.mapping_status
        FROM polymarket_markets pm
        LEFT JOIN polymarket_champion_team_map ctm
          ON pm.discovered_at = ctm.discovered_at
         AND pm.market_id = ctm.market_id
        WHERE pm.discovered_at = ?
        ORDER BY pm.event_type, pm.question
        """,
        (discovered_at,),
    )
    return [dict(row) for row in cursor.fetchall()]


def status_for_market(row: dict[str, Any]) -> tuple[str, str]:
    active = as_int_bool(row.get("active"))
    closed = as_int_bool(row.get("closed"))
    accepting = str(row.get("accepting_orders") or "").lower()
    liquidity = as_float(row.get("liquidity"))
    volume_24h = as_float(row.get("volume_24hr"))
    mapping_status = str(row.get("mapping_status") or "")

    if mapping_status in {"placeholder", "unmapped_or_not_in_groups"}:
        return "excluded", f"Excluded from scoring: {mapping_status}"
    if mapping_status == "other_bucket":
        return "watchlist", "Other bucket requires manual review"
    if closed:
        return "closed", "Market is closed; do not open new positions"
    if not active:
        return "watchlist", "Market is not active, keep as watchlist unless resolved"
    if accepting == "false":
        return "watchlist", "Market active but not accepting orders"
    if volume_24h >= HOT_VOLUME_24H_THRESHOLD:
        return "hot", "High current trading activity"
    if liquidity < LOW_LIQUIDITY_THRESHOLD:
        return "low_liquidity", "Low liquidity; observe, do not assume low value"
    if volume_24h < LOW_VOLUME_24H_THRESHOLD:
        return "watchlist", "Low current volume; may be early or outside event window"
    return "active", "Open and trackable"


def build_rows(markets: list[dict[str, Any]], existing_first_seen: dict[str, str]) -> tuple[list[TopicRow], list[StatusSnapshot]]:
    topics: list[TopicRow] = []
    snapshots: list[StatusSnapshot] = []
    for row in markets:
        platform = str(row.get("platform") or "polymarket")
        market_id = str(row.get("market_id") or "")
        tid = topic_id(platform, market_id)
        captured_at = str(row.get("discovered_at") or "")
        status, note = status_for_market(row)
        first_seen = existing_first_seen.get(tid, captured_at)
        canonical_team = str(row.get("canonical_team") or "")
        group_code = str(row.get("group_code") or "")

        topics.append(
            TopicRow(
                topic_id=tid,
                platform=platform,
                market_id=market_id,
                event_slug=str(row.get("event_slug") or ""),
                market_slug=str(row.get("market_slug") or ""),
                title=str(row.get("question") or ""),
                topic_type=str(row.get("event_type") or ""),
                canonical_team=canonical_team,
                group_code=group_code,
                first_seen_at=first_seen,
                latest_seen_at=captured_at,
                current_status=status,
                lifecycle_note=note,
                url=str(row.get("url") or ""),
                affiliate_url=with_polymarket_affiliate(str(row.get("url") or "")),
            )
        )
        snapshots.append(
            StatusSnapshot(
                snapshot_id=snapshot_id(tid, captured_at),
                topic_id=tid,
                captured_at=captured_at,
                active=as_int_bool(row.get("active")),
                closed=as_int_bool(row.get("closed")),
                accepting_orders=str(row.get("accepting_orders") or ""),
                status=status,
                best_bid=str(row.get("best_bid") or ""),
                best_ask=str(row.get("best_ask") or ""),
                last_trade_price=str(row.get("last_trade_price") or ""),
                volume=as_float(row.get("volume")),
                volume_24hr=as_float(row.get("volume_24hr")),
                liquidity=as_float(row.get("liquidity")),
                open_interest=as_float(row.get("open_interest")),
                status_note=note,
            )
        )
    return topics, snapshots


def existing_first_seen(conn: sqlite3.Connection) -> dict[str, str]:
    first_seen: dict[str, str] = {}
    cursor = conn.execute(
        """
        SELECT platform, market_id, MIN(discovered_at)
        FROM polymarket_markets
        GROUP BY platform, market_id
        """
    )
    for platform, market_id, seen_at in cursor.fetchall():
        first_seen[topic_id(str(platform), str(market_id))] = str(seen_at)

    cursor = conn.execute("SELECT topic_id, first_seen_at FROM prediction_market_topics")
    for existing_topic_id, seen_at in cursor.fetchall():
        tid = str(existing_topic_id)
        current = first_seen.get(tid)
        if current is None or str(seen_at) < current:
            first_seen[tid] = str(seen_at)
    return first_seen


def upsert_topics(conn: sqlite3.Connection, topics: list[TopicRow], snapshots: list[StatusSnapshot]) -> None:
    topic_columns = list(TopicRow.__dataclass_fields__.keys())
    snapshot_columns = list(StatusSnapshot.__dataclass_fields__.keys())
    topic_values = ", ".join(f":{column}" for column in topic_columns)
    snapshot_values = ", ".join(f":{column}" for column in snapshot_columns)

    with conn:
        conn.executemany(
            f"""
            INSERT INTO prediction_market_topics ({", ".join(topic_columns)})
            VALUES ({topic_values})
            ON CONFLICT(topic_id) DO UPDATE SET
              event_slug=excluded.event_slug,
              market_slug=excluded.market_slug,
              title=excluded.title,
              topic_type=excluded.topic_type,
              canonical_team=excluded.canonical_team,
              group_code=excluded.group_code,
              first_seen_at=MIN(prediction_market_topics.first_seen_at, excluded.first_seen_at),
              latest_seen_at=excluded.latest_seen_at,
              current_status=excluded.current_status,
              lifecycle_note=excluded.lifecycle_note,
              url=excluded.url,
              affiliate_url=excluded.affiliate_url
            """,
            [asdict(topic) for topic in topics],
        )
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO market_status_snapshots ({", ".join(snapshot_columns)})
            VALUES ({snapshot_values})
            """,
            [asdict(snapshot) for snapshot in snapshots],
        )


def compare_snapshots(current: list[StatusSnapshot], previous: list[StatusSnapshot]) -> dict[str, list[dict[str, Any]]]:
    previous_by_topic = {row.topic_id: row for row in previous}
    current_by_topic = {row.topic_id: row for row in current}
    changes: dict[str, list[dict[str, Any]]] = {
        "new_topics": [],
        "missing_from_latest": [],
        "status_changes": [],
        "price_moves": [],
        "volume_growth": [],
    }

    for topic, current_row in current_by_topic.items():
        prev = previous_by_topic.get(topic)
        if prev is None:
            changes["new_topics"].append({"topic_id": topic, "status": current_row.status})
            continue
        if prev.status != current_row.status:
            changes["status_changes"].append(
                {"topic_id": topic, "from": prev.status, "to": current_row.status}
            )
        prev_price = as_float(prev.best_ask or prev.last_trade_price)
        current_price = as_float(current_row.best_ask or current_row.last_trade_price)
        if abs(current_price - prev_price) >= PRICE_MOVE_THRESHOLD:
            changes["price_moves"].append(
                {"topic_id": topic, "from": prev_price, "to": current_price, "delta": current_price - prev_price}
            )
        if current_row.volume_24hr - prev.volume_24hr >= VOLUME_GROWTH_THRESHOLD:
            changes["volume_growth"].append(
                {
                    "topic_id": topic,
                    "from": prev.volume_24hr,
                    "to": current_row.volume_24hr,
                    "delta": current_row.volume_24hr - prev.volume_24hr,
                }
            )

    for topic, prev in previous_by_topic.items():
        if topic not in current_by_topic:
            changes["missing_from_latest"].append({"topic_id": topic, "previous_status": prev.status})
    return changes


def fetch_snapshots(conn: sqlite3.Connection, captured_at: str) -> list[StatusSnapshot]:
    if not captured_at:
        return []
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT * FROM market_status_snapshots WHERE captured_at = ?", (captured_at,))
    return [StatusSnapshot(**dict(row)) for row in cursor.fetchall()]


def counts_by_status(rows: list[StatusSnapshot]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def topic_lookup(topics: list[TopicRow]) -> dict[str, TopicRow]:
    return {topic.topic_id: topic for topic in topics}


def write_current_csv(topics: list[TopicRow], snapshots: list[StatusSnapshot], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    snap_by_topic = {snapshot.topic_id: snapshot for snapshot in snapshots}
    fieldnames = list(TopicRow.__dataclass_fields__.keys()) + [
        "best_bid",
        "best_ask",
        "last_trade_price",
        "volume",
        "volume_24hr",
        "liquidity",
        "open_interest",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for topic in topics:
            snapshot = snap_by_topic[topic.topic_id]
            row = asdict(topic)
            row.update(
                {
                    "best_bid": snapshot.best_bid,
                    "best_ask": snapshot.best_ask,
                    "last_trade_price": snapshot.last_trade_price,
                    "volume": snapshot.volume,
                    "volume_24hr": snapshot.volume_24hr,
                    "liquidity": snapshot.liquidity,
                    "open_interest": snapshot.open_interest,
                }
            )
            writer.writerow(row)


def change_label(key: str) -> str:
    return {
        "new_topics": "新增选题",
        "missing_from_latest": "本次消失",
        "status_changes": "状态变化",
        "price_moves": "价格变化",
        "volume_growth": "交易量变化",
    }.get(key, key)


def write_changes(
    topics: list[TopicRow],
    changes: dict[str, list[dict[str, Any]]],
    csv_path: Path,
    json_path: Path,
    latest_at: str,
    previous_at: str,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    lookup = topic_lookup(topics)
    rows: list[dict[str, Any]] = []
    for change_type, items in changes.items():
        for item in items:
            topic = lookup.get(str(item.get("topic_id")))
            rows.append(
                {
                    "latest_snapshot_at": latest_at,
                    "previous_snapshot_at": previous_at,
                    "change_type": change_type,
                    "change_label": change_label(change_type),
                    "topic_id": str(item.get("topic_id") or ""),
                    "title": topic.title if topic else "",
                    "event_slug": topic.event_slug if topic else "",
                    "current_status": topic.current_status if topic else "",
                    "details": json.dumps(item, ensure_ascii=False),
                    "affiliate_url": topic.affiliate_url if topic else "",
                }
            )
    fieldnames = [
        "latest_snapshot_at",
        "previous_snapshot_at",
        "change_type",
        "change_label",
        "topic_id",
        "title",
        "event_slug",
        "current_status",
        "details",
        "affiliate_url",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_summary(
    topics: list[TopicRow],
    snapshots: list[StatusSnapshot],
    changes: dict[str, list[dict[str, Any]]],
    output: Path,
    latest_at: str,
    previous_at: str,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lookup = topic_lookup(topics)
    counts = counts_by_status(snapshots)
    lines = [
        "# Prediction Market Topic Status",
        "",
        f"- Latest snapshot: `{latest_at}`",
        f"- Previous snapshot: `{previous_at or 'none'}`",
        f"- Current topic count: `{len(topics)}`",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- `{status}`: {count}")

    lines.extend(["", "## Current Principles", ""])
    lines.append("- Low trading volume does not mean low attention or low value.")
    lines.append("- Newly listed or pre-window markets stay in watchlist/low_liquidity, not ended.")
    lines.append("- Only closed/resolved/settled markets are treated as ended.")
    lines.append("- Current counts use the latest snapshot only; historical snapshots are for trend analysis.")

    sections = [
        ("New Topics", "new_topics"),
        ("Missing From Latest", "missing_from_latest"),
        ("Status Changes", "status_changes"),
        ("Price Moves", "price_moves"),
        ("Volume Growth", "volume_growth"),
    ]
    for title, key in sections:
        rows = changes.get(key, [])
        lines.extend(["", f"## {title}", ""])
        if not rows:
            lines.append("- None")
            continue
        for item in rows[:30]:
            topic = lookup.get(str(item.get("topic_id")))
            label = topic.title if topic else str(item.get("topic_id"))
            lines.append(f"- {label}: `{item}`")

    watch = [topic for topic in topics if topic.current_status in {"watchlist", "low_liquidity"}]
    lines.extend(["", "## Watchlist / Low Liquidity", ""])
    if not watch:
        lines.append("- None")
    else:
        for topic in watch[:40]:
            lines.append(f"- `{topic.current_status}` {topic.title} - {topic.lifecycle_note}")

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--current-csv", type=Path, default=DEFAULT_CURRENT_CSV)
    parser.add_argument("--changes-csv", type=Path, default=DEFAULT_CHANGES_CSV)
    parser.add_argument("--changes-json", type=Path, default=DEFAULT_CHANGES_JSON)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(args.schema.read_text(encoding="utf-8"))
        ensure_schema_migrations(conn)
        latest_at = latest_snapshot_at(conn)
        if not latest_at:
            raise SystemExit("No Polymarket snapshots found. Run discovery/import first.")
        previous_at = previous_snapshot_at(conn, latest_at)
        first_seen = existing_first_seen(conn)
        markets = fetch_markets(conn, latest_at)
        topics, snapshots = build_rows(markets, first_seen)
        upsert_topics(conn, topics, snapshots)
        previous_snapshots = fetch_snapshots(conn, previous_at)
        changes = compare_snapshots(snapshots, previous_snapshots)
    finally:
        conn.close()

    write_current_csv(topics, snapshots, args.current_csv)
    write_changes(topics, changes, args.changes_csv, args.changes_json, latest_at, previous_at)
    write_summary(topics, snapshots, changes, args.output, latest_at, previous_at)

    print(f"Latest snapshot: {latest_at}")
    print(f"Current topic count: {len(topics)}")
    print("Status counts:")
    for status, count in sorted(counts_by_status(snapshots).items(), key=lambda item: item[1], reverse=True):
        print(f"- {status}: {count}")
    print(f"Wrote CSV: {args.current_csv}")
    print(f"Wrote changes CSV: {args.changes_csv}")
    print(f"Wrote changes JSON: {args.changes_json}")
    print(f"Wrote summary: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
