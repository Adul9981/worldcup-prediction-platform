#!/usr/bin/env python3
"""Score prediction market topics with conservative and upside tracks."""

from __future__ import annotations

import argparse
import csv
import math
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_OUTPUT = Path("data/polymarket/latest_market_event_scores.csv")
DEFAULT_SUMMARY = Path("data/polymarket/latest_market_event_scores_summary.md")

TIER_BASE = {
    "elite": 80,
    "strong": 62,
    "medium": 42,
    "weak": 20,
}

ROLE_BONUS = {
    "group_favorite": 8,
    "host_contender": 6,
    "contender": 5,
    "swing_team": 0,
    "swing_underdog": -4,
    "weak_side": -8,
}


@dataclass
class ScoreRow:
    scored_at: str
    topic_id: str
    platform: str
    title: str
    topic_type: str
    canonical_team: str
    group_code: str
    current_status: str
    conservative_score: float
    upside_score: float
    attention_score: float
    ignored_score: float
    risk_reward_score: float
    risk_score: float
    implied_yes_probability: float
    volume_24hr: float
    liquidity: float
    recommendation_track: str
    action_label: str
    rationale: str
    affiliate_url: str


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def as_float(value: Any) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def scaled_log(value: float, scale: float, cap: float = 100.0) -> float:
    if value <= 0:
        return 0.0
    return clamp(math.log10(value + 1) / math.log10(scale + 1) * cap)


def probability_from_row(row: dict[str, Any]) -> float:
    best_ask = as_float(row.get("best_ask"))
    last_trade = as_float(row.get("last_trade_price"))
    return best_ask or last_trade


def team_strength(row: dict[str, Any]) -> float:
    tier = str(row.get("tier") or "").lower()
    role = str(row.get("likely_role") or "")
    return clamp(TIER_BASE.get(tier, 35) + ROLE_BONUS.get(role, 0))


def status_modifier(status: str) -> float:
    return {
        "hot": 8,
        "active": 3,
        "watchlist": -8,
        "low_liquidity": -12,
        "excluded": -100,
        "closed": -100,
        "resolved": -100,
    }.get(status, 0)


def risk_score(row: dict[str, Any], implied_probability: float) -> float:
    status = str(row.get("current_status") or "")
    liquidity = as_float(row.get("liquidity"))
    volume_24h = as_float(row.get("volume_24hr"))
    risk = 30.0
    if status in {"excluded", "closed", "resolved"}:
        return 100.0
    if status in {"watchlist", "low_liquidity"}:
        risk += 20
    if liquidity < 1_000:
        risk += 20
    elif liquidity < 10_000:
        risk += 10
    if volume_24h < 100:
        risk += 15
    if implied_probability <= 0.003:
        risk += 18
    elif implied_probability <= 0.01:
        risk += 10
    if implied_probability >= 0.20:
        risk += 5
    return clamp(risk)


def score_row(row: dict[str, Any], scored_at: str) -> ScoreRow:
    status = str(row.get("current_status") or "")
    implied = probability_from_row(row)
    volume_24h = as_float(row.get("volume_24hr"))
    liquidity = as_float(row.get("liquidity"))
    attention = clamp(0.65 * scaled_log(volume_24h, 5_000_000) + 0.35 * scaled_log(liquidity, 10_000_000))
    strength = team_strength(row)
    risk = risk_score(row, implied)
    price_quality = clamp(100 - abs(implied - 0.08) / 0.08 * 45)

    # Low public price plus real team metadata can be an ignored-value signal.
    ignored = clamp((100 - attention) * 0.35 + strength * 0.35 + (1 - min(implied, 0.2) / 0.2) * 30)
    risk_reward = clamp(ignored * 0.55 + strength * 0.25 + (100 - risk) * 0.20)

    conservative = clamp(
        strength * 0.40
        + attention * 0.20
        + (100 - risk) * 0.20
        + price_quality * 0.12
        + max(status_modifier(status), 0) * 0.50
    )
    upside = clamp(
        risk_reward * 0.40
        + ignored * 0.25
        + attention * 0.15
        + (100 - risk) * 0.10
        + status_modifier(status)
        + (18 if 0.002 <= implied <= 0.04 else 0)
    )

    if status == "excluded":
        track = "excluded"
        action = "exclude"
        rationale = "Excluded from scoring by market status or mapping rule."
    elif conservative >= 76 and implied >= 0.015:
        track = "conservative"
        action = "稳健机会"
        rationale = "Strong team/market profile with acceptable risk."
    elif upside >= 70:
        track = "upside"
        action = "高盈亏比观察"
        rationale = "Potentially underpriced or early market; observe before staking."
    elif status in {"watchlist", "low_liquidity"}:
        track = "watchlist"
        action = "只观察"
        rationale = "Low activity or special bucket; do not treat as ended."
    else:
        track = "neutral"
        action = "等待"
        rationale = "Track, but no current edge signal."

    return ScoreRow(
        scored_at=scored_at,
        topic_id=str(row.get("topic_id") or ""),
        platform=str(row.get("platform") or ""),
        title=str(row.get("title") or ""),
        topic_type=str(row.get("topic_type") or ""),
        canonical_team=str(row.get("canonical_team") or ""),
        group_code=str(row.get("group_code") or ""),
        current_status=status,
        conservative_score=round(conservative, 2),
        upside_score=round(upside, 2),
        attention_score=round(attention, 2),
        ignored_score=round(ignored, 2),
        risk_reward_score=round(risk_reward, 2),
        risk_score=round(risk, 2),
        implied_yes_probability=round(implied, 4),
        volume_24hr=round(volume_24h, 4),
        liquidity=round(liquidity, 4),
        recommendation_track=track,
        action_label=action,
        rationale=rationale,
        affiliate_url=str(row.get("affiliate_url") or ""),
    )


def fetch_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT
          pmt.*,
          mss.best_bid,
          mss.best_ask,
          mss.last_trade_price,
          mss.volume,
          mss.volume_24hr,
          mss.liquidity,
          ctm.tier,
          ctm.likely_role
        FROM prediction_market_topics pmt
        JOIN market_status_snapshots mss
          ON pmt.topic_id = mss.topic_id
         AND mss.captured_at = pmt.latest_seen_at
        LEFT JOIN polymarket_champion_team_map ctm
          ON pmt.market_id = ctm.market_id
         AND ctm.discovered_at = pmt.latest_seen_at
        WHERE pmt.latest_seen_at = (SELECT MAX(latest_seen_at) FROM prediction_market_topics)
        ORDER BY pmt.title
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def ensure_schema_migrations(conn: sqlite3.Connection, schema: Path) -> None:
    conn.executescript(schema.read_text(encoding="utf-8"))


def write_csv(rows: list[ScoreRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(ScoreRow.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_sqlite(conn: sqlite3.Connection, rows: list[ScoreRow], scored_at: str) -> None:
    columns = list(ScoreRow.__dataclass_fields__.keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    with conn:
        conn.execute("DELETE FROM market_event_scores WHERE scored_at = ?", (scored_at,))
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO market_event_scores ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            [asdict(row) for row in rows],
        )


def write_summary(rows: list[ScoreRow], path: Path, scored_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_track: dict[str, int] = {}
    for row in rows:
        by_track[row.recommendation_track] = by_track.get(row.recommendation_track, 0) + 1
    conservative = sorted(
        [row for row in rows if row.recommendation_track == "conservative"],
        key=lambda row: row.conservative_score,
        reverse=True,
    )[:10]
    upside = sorted(
        [row for row in rows if row.recommendation_track == "upside"],
        key=lambda row: row.upside_score,
        reverse=True,
    )[:10]
    lines = [
        "# Market Event Scores",
        "",
        f"- Scored at: `{scored_at}`",
        f"- Total scored topics: `{len(rows)}`",
        "",
        "## Recommendation Tracks",
        "",
    ]
    for track, count in sorted(by_track.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- `{track}`: {count}")
    lines.extend(["", "## 稳健机会 Top", ""])
    if not conservative:
        lines.append("- None")
    for row in conservative:
        lines.append(
            f"- {row.title}: conservative `{row.conservative_score}`, risk `{row.risk_score}`, implied `{row.implied_yes_probability}`"
        )
    lines.extend(["", "## 高盈亏比观察 Top", ""])
    if not upside:
        lines.append("- None")
    for row in upside:
        lines.append(
            f"- {row.title}: upside `{row.upside_score}`, risk_reward `{row.risk_reward_score}`, implied `{row.implied_yes_probability}`"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Scores are heuristic and must be calibrated with review data.",
            "- `hot` activity does not mean a recommended bet.",
            "- Upside opportunities are observation candidates unless staking rules confirm entry.",
            "- Excluded rows are retained in raw data but not actionable.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    scored_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = sqlite3.connect(args.db)
    try:
        ensure_schema_migrations(conn, args.schema)
        raw_rows = fetch_rows(conn)
        rows = [score_row(row, scored_at) for row in raw_rows]
        write_sqlite(conn, rows, scored_at)
    finally:
        conn.close()

    write_csv(rows, args.output)
    write_summary(rows, args.summary, scored_at)
    print(f"Scored topics: {len(rows)}")
    print(f"Wrote CSV: {args.output}")
    print(f"Wrote summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
