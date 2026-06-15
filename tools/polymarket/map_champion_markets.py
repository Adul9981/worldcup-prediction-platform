#!/usr/bin/env python3
"""Map Polymarket World Cup champion markets to local team metadata."""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_GROUPS = Path("data/templates/groups.csv")
DEFAULT_TEAMS = Path("data/templates/teams.csv")
DEFAULT_OUTPUT = Path("data/polymarket/latest_champion_market_team_map.csv")
DEFAULT_SUMMARY = Path("data/polymarket/latest_champion_market_team_map_summary.md")

TEAM_RE = re.compile(r"^Will (.+?) win the 2026 FIFA World Cup\?$")
PLACEHOLDER_RE = re.compile(r"^Team [A-Z]{2}$")

ALIASES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Curaçao": "Curacao",
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    "USA": "United States",
    "United States of America": "United States",
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Ivory Coast": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Saudi Arabia": "Saudi Arabia",
    "Any Other Team": "Any Other Team",
}


@dataclass
class TeamMeta:
    team: str
    group_code: str = ""
    confederation: str = ""
    tier: str = ""
    weak_team_level: str = ""
    strong_team_level: str = ""
    swing_level: str = ""
    attention_level: str = ""
    information_gap_level: str = ""
    likely_role: str = ""


@dataclass
class ChampionMarketMap:
    discovered_at: str
    market_id: str
    market_slug: str
    question: str
    extracted_team: str
    canonical_team: str
    mapping_status: str
    group_code: str
    tier: str
    weak_team_level: str
    strong_team_level: str
    swing_level: str
    attention_level: str
    information_gap_level: str
    likely_role: str
    best_bid: str
    best_ask: str
    last_trade_price: str
    implied_yes_probability: float
    volume: float
    volume_24hr: float
    liquidity: float
    url: str
    notes: str


def normalize_name(name: str) -> str:
    stripped = " ".join(name.strip().split())
    return ALIASES.get(stripped, stripped)


def key(name: str) -> str:
    return normalize_name(name).casefold()


def as_float(value: Any) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_groups(path: Path) -> dict[str, TeamMeta]:
    teams: dict[str, TeamMeta] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            group_code = row["group_code"]
            for name in row["teams"].split(";"):
                canonical = normalize_name(name)
                teams[key(canonical)] = TeamMeta(team=canonical, group_code=group_code)
    return teams


def overlay_team_details(teams: dict[str, TeamMeta], path: Path) -> dict[str, TeamMeta]:
    if not path.exists():
        return teams
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            canonical = normalize_name(row["team"])
            existing = teams.get(key(canonical), TeamMeta(team=canonical))
            existing.confederation = row.get("confederation", "")
            existing.tier = row.get("tier", "")
            existing.weak_team_level = row.get("weak_team_level", "")
            existing.strong_team_level = row.get("strong_team_level", "")
            existing.swing_level = row.get("swing_level", "")
            existing.attention_level = row.get("attention_level", "")
            existing.information_gap_level = row.get("information_gap_level", "")
            existing.likely_role = row.get("likely_role", "")
            if row.get("group_code"):
                existing.group_code = row["group_code"]
            teams[key(canonical)] = existing
    return teams


def extract_team(question: str) -> str:
    match = TEAM_RE.match(question.strip())
    return match.group(1).strip() if match else ""


def status_for_team(extracted: str, canonical: str, teams: dict[str, TeamMeta]) -> tuple[str, str]:
    if not extracted:
        return "not_champion_question", "Question did not match champion pattern"
    if PLACEHOLDER_RE.match(extracted):
        return "placeholder", "Placeholder team from market, exclude from decision scoring"
    if canonical == "Any Other Team":
        return "other_bucket", "Other bucket, handle as special market"
    if key(canonical) in teams:
        return "mapped", ""
    return "unmapped_or_not_in_groups", "Not found in local groups/team metadata"


def load_champion_markets(conn: sqlite3.Connection, latest_only: bool) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    where = "event_type = 'champion_or_outright'"
    params: tuple[Any, ...] = ()
    if latest_only:
        where += " AND discovered_at = (SELECT MAX(discovered_at) FROM polymarket_markets)"
    cursor = conn.execute(
        f"""
        SELECT *
        FROM polymarket_markets
        WHERE {where}
        ORDER BY CAST(COALESCE(NULLIF(best_ask, ''), '0') AS REAL) DESC, question
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def map_rows(markets: list[dict[str, Any]], teams: dict[str, TeamMeta]) -> list[ChampionMarketMap]:
    rows: list[ChampionMarketMap] = []
    for market in markets:
        extracted = extract_team(str(market.get("question", "")))
        canonical = normalize_name(extracted)
        status, notes = status_for_team(extracted, canonical, teams)
        meta = teams.get(key(canonical), TeamMeta(team=canonical))
        best_ask = str(market.get("best_ask") or "")
        implied = as_float(best_ask) if best_ask else as_float(market.get("last_trade_price"))
        rows.append(
            ChampionMarketMap(
                discovered_at=str(market.get("discovered_at") or ""),
                market_id=str(market.get("market_id") or ""),
                market_slug=str(market.get("market_slug") or ""),
                question=str(market.get("question") or ""),
                extracted_team=extracted,
                canonical_team=canonical,
                mapping_status=status,
                group_code=meta.group_code,
                tier=meta.tier,
                weak_team_level=meta.weak_team_level,
                strong_team_level=meta.strong_team_level,
                swing_level=meta.swing_level,
                attention_level=meta.attention_level,
                information_gap_level=meta.information_gap_level,
                likely_role=meta.likely_role,
                best_bid=str(market.get("best_bid") or ""),
                best_ask=best_ask,
                last_trade_price=str(market.get("last_trade_price") or ""),
                implied_yes_probability=implied,
                volume=as_float(market.get("volume")),
                volume_24hr=as_float(market.get("volume_24hr")),
                liquidity=as_float(market.get("liquidity")),
                url=str(market.get("url") or ""),
                notes=notes,
            )
        )
    return rows


def write_csv(rows: list[ChampionMarketMap], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ChampionMarketMap.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_summary(rows: list[ChampionMarketMap], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.mapping_status] = status_counts.get(row.mapping_status, 0) + 1

    mapped = [row for row in rows if row.mapping_status == "mapped"]
    ignored = [row for row in rows if row.mapping_status != "mapped"]
    lines = [
        "# Polymarket Champion Market Team Map",
        "",
        f"- Total champion markets: `{len(rows)}`",
        f"- Mapped World Cup teams: `{len(mapped)}`",
        "",
        "## Mapping Status",
        "",
    ]
    for status, count in sorted(status_counts.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- `{status}`: {count}")

    lines.extend(["", "## Top Mapped Contenders", ""])
    for idx, row in enumerate(sorted(mapped, key=lambda item: item.implied_yes_probability, reverse=True)[:20], start=1):
        lines.extend(
            [
                f"{idx}. {row.canonical_team}",
                f"   - Group: `{row.group_code}`",
                f"   - Tier: `{row.tier}`",
                f"   - Role: `{row.likely_role}`",
                f"   - Implied yes probability: `{row.implied_yes_probability:.3f}`",
                f"   - Bid/ask: `{row.best_bid}` / `{row.best_ask}`",
                f"   - 24h volume: `{row.volume_24hr}`",
            ]
        )

    lines.extend(["", "## Excluded Or Special Rows", ""])
    for row in ignored:
        lines.append(f"- `{row.mapping_status}`: {row.canonical_team} - {row.notes}")

    lines.extend(
        [
            "",
            "## Decision Rule",
            "",
            "- `mapped` rows can enter scoring.",
            "- `placeholder` rows must be excluded from opportunity ranking.",
            "- `other_bucket` rows are special markets and require manual review.",
            "- `unmapped_or_not_in_groups` rows are not current 48-team entries and should be excluded unless manually justified.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sqlite(conn: sqlite3.Connection, rows: list[ChampionMarketMap]) -> None:
    if not rows:
        return
    columns = list(ChampionMarketMap.__dataclass_fields__.keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    column_list = ", ".join(columns)
    with conn:
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO polymarket_champion_team_map ({column_list})
            VALUES ({placeholders})
            """,
            [asdict(row) for row in rows],
        )


def print_summary(rows: list[ChampionMarketMap]) -> None:
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row.mapping_status] = status_counts.get(row.mapping_status, 0) + 1
    print(f"Mapped champion markets: {len(rows)}")
    print("Rows by mapping_status:")
    for status, count in sorted(status_counts.items(), key=lambda item: item[1], reverse=True):
        print(f"- {status}: {count}")
    print("Top mapped contenders by implied yes probability:")
    mapped = [row for row in rows if row.mapping_status == "mapped"]
    for row in sorted(mapped, key=lambda item: item.implied_yes_probability, reverse=True)[:12]:
        print(
            f"- {row.canonical_team}: {row.implied_yes_probability:.3f} "
            f"({row.tier or 'tier?'}, group {row.group_code or '?'})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--groups", type=Path, default=DEFAULT_GROUPS)
    parser.add_argument("--teams", type=Path, default=DEFAULT_TEAMS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument(
        "--all-snapshots",
        action="store_true",
        help="Map all historical snapshots instead of only the latest discovered_at.",
    )
    args = parser.parse_args()

    teams = overlay_team_details(load_groups(args.groups), args.teams)
    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(args.schema.read_text(encoding="utf-8"))
        markets = load_champion_markets(conn, latest_only=not args.all_snapshots)
        rows = map_rows(markets, teams)
        write_csv(rows, args.output)
        write_summary(rows, args.summary)
        write_sqlite(conn, rows)
    finally:
        conn.close()

    print_summary(rows)
    print(f"Wrote CSV: {args.output}")
    print(f"Wrote summary: {args.summary}")
    print(f"Updated SQLite table: polymarket_champion_team_map")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
