#!/usr/bin/env python3
"""Calculate disciplined staking recommendations from event scores."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_OUTPUT = Path("data/polymarket/latest_staking_recommendations.csv")
DEFAULT_SUMMARY = Path("data/polymarket/latest_staking_recommendations_summary.md")

DAILY_MAX_UNITS = 5.0
SINGLE_MARKET_MAX_UNITS = 2.0
LONG_HORIZON_MAX_UNITS = 1.0


@dataclass
class StakeRow:
    calculated_at: str
    topic_id: str
    title: str
    recommendation_track: str
    action_label: str
    recommended_stake_units: float
    max_allowed_stake_units: float
    stake_band: str
    risk_rule: str
    entry_condition: str
    cancel_condition: str
    rationale: str
    affiliate_url: str


def as_float(value: Any) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def fetch_latest_scores(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        SELECT *
        FROM market_event_scores
        WHERE scored_at = (SELECT MAX(scored_at) FROM market_event_scores)
        ORDER BY
            CASE recommendation_track
                WHEN 'conservative' THEN 1
                WHEN 'upside' THEN 2
                WHEN 'watchlist' THEN 3
                WHEN 'neutral' THEN 4
                WHEN 'excluded' THEN 5
                ELSE 6
            END,
            conservative_score DESC,
            upside_score DESC,
            title
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def stake_for_score(row: dict[str, Any], calculated_at: str) -> StakeRow:
    track = str(row.get("recommendation_track") or "")
    topic_type = str(row.get("topic_type") or "")
    conservative = as_float(row.get("conservative_score"))
    upside = as_float(row.get("upside_score"))
    risk = as_float(row.get("risk_score"))
    implied = as_float(row.get("implied_yes_probability"))

    stake = 0.0
    max_allowed = 0.0
    stake_band = "0"
    action = "不下注"
    risk_rule = "No stake unless scoring and risk rules permit entry."
    entry = "No entry."
    cancel = "Cancel if market closes, liquidity disappears, or thesis cannot be written in one sentence."

    if track == "excluded":
        risk_rule = "Excluded market: placeholder, non-current team, or invalid decision-layer candidate."
    elif track == "watchlist":
        action = "只观察"
        risk_rule = "Watchlist market: low activity/special bucket is not ended, but no stake yet."
        entry = "Reassess after status becomes active/hot and rules are clear."
    elif track == "neutral":
        action = "等待"
        risk_rule = "Neutral score: no current edge signal."
        entry = "Wait for price move, new information, or model upgrade."
    elif track == "conservative":
        max_allowed = LONG_HORIZON_MAX_UNITS if topic_type == "champion_or_outright" else SINGLE_MARKET_MAX_UNITS
        if conservative >= 84 and risk <= 35 and 0.03 <= implied <= 0.14:
            stake = min(1.0, max_allowed)
            stake_band = "1.0"
            action = "稳健小仓"
        elif conservative >= 78 and risk <= 40:
            stake = min(0.5, max_allowed)
            stake_band = "0.5"
            action = "稳健观察仓"
        else:
            stake = 0.25
            stake_band = "0.25"
            action = "小仓观察"
        risk_rule = "Long-horizon market cap applies; do not exceed daily and related-exposure limits."
        entry = "Enter only if price remains near current range and thesis is documented."
    elif track == "upside":
        max_allowed = 0.5 if topic_type == "champion_or_outright" else 1.0
        if upside >= 84 and risk <= 35 and implied >= 0.01:
            stake = 0.5
            stake_band = "0.5"
            action = "高盈亏比小仓"
        elif upside >= 76 and risk <= 50:
            stake = 0.25
            stake_band = "0.25"
            action = "高盈亏比观察仓"
        else:
            stake = 0.0
            stake_band = "0"
            action = "只观察"
        risk_rule = "Upside track is never a heavy stake by default."
        entry = "Enter only if this remains a small, thesis-driven asymmetric idea."

    if risk >= 70:
        stake = 0.0
        stake_band = "0"
        action = "风险过高"
        risk_rule = "Risk score too high; no stake."

    stake = min(stake, max_allowed, SINGLE_MARKET_MAX_UNITS)
    if stake == 0.0:
        max_allowed = 0.0 if track in {"excluded", "watchlist", "neutral"} else max_allowed

    rationale = (
        f"track={track}; conservative={conservative}; upside={upside}; "
        f"risk={risk}; implied={implied}; daily_max={DAILY_MAX_UNITS}"
    )
    return StakeRow(
        calculated_at=calculated_at,
        topic_id=str(row.get("topic_id") or ""),
        title=str(row.get("title") or ""),
        recommendation_track=track,
        action_label=action,
        recommended_stake_units=round(stake, 2),
        max_allowed_stake_units=round(max_allowed, 2),
        stake_band=stake_band,
        risk_rule=risk_rule,
        entry_condition=entry,
        cancel_condition=cancel,
        rationale=rationale,
        affiliate_url=str(row.get("affiliate_url") or ""),
    )


def apply_daily_cap(rows: list[StakeRow]) -> None:
    allocated = 0.0
    for row in rows:
        stake = row.recommended_stake_units
        if stake <= 0:
            continue
        remaining = round(DAILY_MAX_UNITS - allocated, 2)
        if remaining <= 0:
            row.recommended_stake_units = 0.0
            row.stake_band = "0"
            row.action_label = "日额度等待"
            row.risk_rule = (
                "Candidate passed base staking rules, but today's daily unit cap is already allocated."
            )
            continue
        if stake > remaining:
            row.recommended_stake_units = remaining
            row.stake_band = f"{remaining:.2f}".rstrip("0").rstrip(".")
            row.action_label = f"{row.action_label}（额度内减仓）"
            row.risk_rule = (
                f"{row.risk_rule} Reduced to fit the daily {DAILY_MAX_UNITS:.2f}-unit cap."
            )
            allocated = DAILY_MAX_UNITS
            continue
        allocated = round(allocated + stake, 2)


def write_csv(rows: list[StakeRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(StakeRow.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_sqlite(conn: sqlite3.Connection, rows: list[StakeRow], calculated_at: str) -> None:
    columns = list(StakeRow.__dataclass_fields__.keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    with conn:
        conn.execute("DELETE FROM staking_recommendations WHERE calculated_at = ?", (calculated_at,))
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO staking_recommendations ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            [asdict(row) for row in rows],
        )


def write_summary(rows: list[StakeRow], path: Path, calculated_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_action: dict[str, int] = {}
    for row in rows:
        by_action[row.action_label] = by_action.get(row.action_label, 0) + 1
    stake_rows = sorted(
        [row for row in rows if row.recommended_stake_units > 0],
        key=lambda row: row.recommended_stake_units,
        reverse=True,
    )
    total_recommended = sum(row.recommended_stake_units for row in stake_rows)
    lines = [
        "# Staking Recommendations",
        "",
        f"- Calculated at: `{calculated_at}`",
        f"- Actual recommended exposure after daily cap: `{total_recommended:.2f}` units",
        f"- Daily max rule: `{DAILY_MAX_UNITS:.2f}` units",
        "",
        "## Action Counts",
        "",
    ]
    for action, count in sorted(by_action.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- `{action}`: {count}")
    lines.extend(["", "## Positive Stake Candidates", ""])
    if not stake_rows:
        lines.append("- None")
    for row in stake_rows[:30]:
        lines.append(
            f"- {row.title}: `{row.recommended_stake_units}` units, {row.action_label}. {row.risk_rule}"
        )
    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- These are recommendations, not orders.",
            "- No wallet, private key, or trading endpoint is used.",
            "- Upside track stays small by default.",
            "- Do not exceed daily max, single-market max, or related-exposure max.",
            "- Every actual stake requires a written thesis and later review.",
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

    calculated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(args.schema.read_text(encoding="utf-8"))
        score_rows = fetch_latest_scores(conn)
        rows = [stake_for_score(row, calculated_at) for row in score_rows]
        apply_daily_cap(rows)
        write_sqlite(conn, rows, calculated_at)
    finally:
        conn.close()

    write_csv(rows, args.output)
    write_summary(rows, args.summary, calculated_at)
    print(f"Stake rows: {len(rows)}")
    print(f"Wrote CSV: {args.output}")
    print(f"Wrote summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
