#!/usr/bin/env python3
"""Import normalized Polymarket market CSV snapshots into SQLite."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_CSV = Path("data/polymarket/latest_polymarket_worldcup_markets.csv")

TABLE = "polymarket_markets"

COLUMNS = [
    "discovered_at",
    "platform",
    "source",
    "event_id",
    "event_slug",
    "event_title",
    "market_id",
    "market_slug",
    "question",
    "event_type",
    "active",
    "closed",
    "accepting_orders",
    "end_date",
    "volume",
    "volume_24hr",
    "liquidity",
    "open_interest",
    "best_bid",
    "best_ask",
    "last_trade_price",
    "outcome_prices",
    "outcomes",
    "url",
    "matched_keywords",
    "notes",
]

FLOAT_COLUMNS = {"volume", "volume_24hr", "liquidity", "open_interest"}
BOOL_COLUMNS = {"active", "closed"}


def parse_bool(value: str) -> int:
    return 1 if str(value).strip().lower() in {"1", "true", "yes"} else 0


def parse_float(value: str) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    return float(value)


def normalize_row(row: dict[str, str]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for column in COLUMNS:
        value = row.get(column, "")
        if column in BOOL_COLUMNS:
            normalized[column] = parse_bool(value)
        elif column in FLOAT_COLUMNS:
            normalized[column] = parse_float(value)
        else:
            normalized[column] = value
    return normalized


def load_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    conn.executescript(schema_path.read_text(encoding="utf-8"))


def import_csv(conn: sqlite3.Connection, csv_path: Path, replace_snapshot: bool) -> tuple[int, str | None]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [normalize_row(row) for row in reader]

    if not rows:
        return 0, None

    discovered_at = rows[0]["discovered_at"]
    placeholders = ", ".join(f":{column}" for column in COLUMNS)
    column_list = ", ".join(COLUMNS)

    with conn:
        if replace_snapshot:
            conn.execute(f"DELETE FROM {TABLE} WHERE discovered_at = ?", (discovered_at,))
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO {TABLE} ({column_list})
            VALUES ({placeholders})
            """,
            rows,
        )
    return len(rows), str(discovered_at)


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    cursor = conn.execute(
        """
        SELECT event_type, COUNT(*)
        FROM polymarket_markets
        GROUP BY event_type
        ORDER BY COUNT(*) DESC, event_type
        """
    )
    return {str(event_type): int(count) for event_type, count in cursor.fetchall()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument(
        "--append-snapshot",
        action="store_true",
        help="Keep existing rows for the same discovered_at snapshot instead of replacing them.",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")
    if not args.schema.exists():
        raise SystemExit(f"Schema not found: {args.schema}")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    try:
        load_schema(conn, args.schema)
        imported, discovered_at = import_csv(conn, args.csv, replace_snapshot=not args.append_snapshot)
        counts = table_counts(conn)
    finally:
        conn.close()

    print(f"Database: {args.db}")
    print(f"CSV: {args.csv}")
    print(f"Imported rows: {imported}")
    print(f"Snapshot discovered_at: {discovered_at or ''}")
    print("Rows by event_type:")
    for event_type, count in counts.items():
        print(f"- {event_type}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
