#!/usr/bin/env python3
"""Generate the daily three ranking lists for the World Cup prediction workbench."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_OUTPUT = Path("data/polymarket/latest_daily_event_rankings.csv")
DEFAULT_SUMMARY = Path("data/polymarket/latest_daily_event_rankings_summary.md")
DEFAULT_GLOSSARY = Path("data/templates/glossary_cn_en.csv")
DEFAULT_LIMIT = 5


@dataclass
class RankingRow:
    date: str
    rank_type: str
    rank: int
    topic_id: str
    platform: str
    match_id: str | None
    event_id: str | None
    event_title: str
    category: str
    current_status: str
    importance_score: float
    attention_score: float
    ignored_score: float
    risk_reward_score: float
    risk_score: float
    implied_yes_probability: float
    recommendation_track: str
    recommended_action: str
    cancel_condition: str
    copy_angle: str
    affiliate_url: str


RANK_LABELS = {
    "most_watched": "最值得关注",
    "most_ignored": "最被忽视",
    "best_risk_reward": "最大盈亏比",
}


def as_float(value: Any) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_glossary(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {row["en"]: row["zh"] for row in csv.DictReader(handle) if row.get("en")}


def zh(value: str, glossary: dict[str, str]) -> str:
    return glossary.get(value, value)


def market_title_zh(title: str, glossary: dict[str, str]) -> str:
    if title in glossary:
        return glossary[title]
    prefix = "Will "
    suffix = " win the 2026 FIFA World Cup?"
    if title.startswith(prefix) and title.endswith(suffix):
        team = title[len(prefix) : -len(suffix)]
        return f"{zh(team, glossary)}是否赢得2026年世界杯？"
    return title.replace("?", "？")


def ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(daily_event_rankings)")}
    additions = {
        "topic_id": "TEXT REFERENCES prediction_market_topics(topic_id)",
        "platform": "TEXT",
        "current_status": "TEXT",
        "attention_score": "REAL",
        "risk_score": "REAL DEFAULT 0",
        "implied_yes_probability": "REAL DEFAULT 0",
        "recommendation_track": "TEXT",
        "affiliate_url": "TEXT",
    }
    for column, definition in additions.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE daily_event_rankings ADD COLUMN {column} {definition}")


def fetch_candidates(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """
        WITH latest_scores AS (
            SELECT *
            FROM market_event_scores
            WHERE scored_at = (SELECT MAX(scored_at) FROM market_event_scores)
        ),
        latest_stakes AS (
            SELECT *
            FROM staking_recommendations
            WHERE calculated_at = (SELECT MAX(calculated_at) FROM staking_recommendations)
        )
        SELECT
            s.*,
            COALESCE(st.action_label, s.action_label) AS stake_action_label,
            COALESCE(st.recommended_stake_units, 0) AS recommended_stake_units,
            COALESCE(st.cancel_condition, '') AS cancel_condition
        FROM latest_scores s
        LEFT JOIN latest_stakes st
          ON s.topic_id = st.topic_id
        WHERE s.current_status NOT IN ('excluded', 'closed', 'resolved')
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def copy_angle(rank_type: str, row: dict[str, Any]) -> str:
    team = str(row.get("canonical_team") or "").strip()
    title = str(row.get("title") or "").strip()
    if rank_type == "most_watched":
        if team:
            return f"{team} is a high-attention market; use it as the day's consensus benchmark."
        return "High-attention event; use it as the day's market temperature check."
    if rank_type == "most_ignored":
        if team:
            return f"{team} may be under-discussed relative to its market profile."
        return "Low-noise market with a possible information gap."
    if rank_type == "best_risk_reward":
        if team:
            return f"{team} sits in the asymmetric watch zone; thesis quality decides whether it is actionable."
        return "Asymmetric setup; require a clear thesis before treating it as actionable."
    return title


def action_for(row: dict[str, Any]) -> str:
    stake = as_float(row.get("recommended_stake_units"))
    stake_action = str(row.get("stake_action_label") or "")
    track = str(row.get("recommendation_track") or "")
    if stake > 0:
        return "买 YES"
    if stake_action == "日额度等待":
        return "观察，等待条件确认"
    if track == "upside":
        return "观察高盈亏比"
    if track == "conservative":
        return "观察稳健机会"
    return stake_action or "等待"


def build_rows(candidates: list[dict[str, Any]], date: str, limit: int) -> list[RankingRow]:
    sorters = {
        "most_watched": lambda row: (
            as_float(row.get("attention_score")),
            as_float(row.get("conservative_score")),
            as_float(row.get("volume_24hr")),
        ),
        "most_ignored": lambda row: (
            as_float(row.get("ignored_score")),
            as_float(row.get("risk_reward_score")),
            -as_float(row.get("risk_score")),
        ),
        "best_risk_reward": lambda row: (
            as_float(row.get("risk_reward_score")),
            as_float(row.get("attention_score")),
            -as_float(row.get("risk_score")),
        ),
    }
    rows: list[RankingRow] = []
    for rank_type, sorter in sorters.items():
        filtered = [
            row
            for row in candidates
            if as_float(row.get("risk_score")) <= 65
            and str(row.get("recommendation_track") or "") != "excluded"
        ]
        ranked = sorted(filtered, key=sorter, reverse=True)[:limit]
        for index, row in enumerate(ranked, start=1):
            attention = as_float(row.get("attention_score"))
            rows.append(
                RankingRow(
                    date=date,
                    rank_type=rank_type,
                    rank=index,
                    topic_id=str(row.get("topic_id") or ""),
                    platform=str(row.get("platform") or ""),
                    match_id=None,
                    event_id=None,
                    event_title=str(row.get("title") or ""),
                    category=str(row.get("topic_type") or ""),
                    current_status=str(row.get("current_status") or ""),
                    importance_score=round(attention, 2),
                    attention_score=round(attention, 2),
                    ignored_score=round(as_float(row.get("ignored_score")), 2),
                    risk_reward_score=round(as_float(row.get("risk_reward_score")), 2),
                    risk_score=round(as_float(row.get("risk_score")), 2),
                    implied_yes_probability=round(as_float(row.get("implied_yes_probability")), 4),
                    recommendation_track=str(row.get("recommendation_track") or ""),
                    recommended_action=action_for(row),
                    cancel_condition=str(row.get("cancel_condition") or ""),
                    copy_angle=copy_angle(rank_type, row),
                    affiliate_url=str(row.get("affiliate_url") or ""),
                )
            )
    return rows


def write_csv(rows: list[RankingRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(RankingRow.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def write_sqlite(conn: sqlite3.Connection, rows: list[RankingRow], date: str) -> None:
    columns = list(RankingRow.__dataclass_fields__.keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    with conn:
        conn.execute("DELETE FROM daily_event_rankings WHERE date = ?", (date,))
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO daily_event_rankings ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            [asdict(row) for row in rows],
        )


def write_summary(rows: list[RankingRow], path: Path, date: str, glossary: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 每日预测事件决策榜",
        "",
        f"- 日期: `{date}`",
        f"- 条目数: `{len(rows)}`",
        "",
    ]
    for rank_type, label in RANK_LABELS.items():
        lines.extend([f"## {label}", ""])
        selected = [row for row in rows if row.rank_type == rank_type]
        if not selected:
            lines.append("- None")
        for row in selected:
            lines.append(
                "- "
                f"#{row.rank} {market_title_zh(row.event_title, glossary)}: "
                f"关注 `{row.attention_score}`, 忽视 `{row.ignored_score}`, "
                f"盈亏比 `{row.risk_reward_score}`。"
                f"{row.recommended_action}"
            )
        lines.append("")
    lines.extend(
        [
            "## 展示规则",
            "",
            "- 这些榜单是方向分析，不是下单指令。",
            "- 不输出下注数量、下注金额或单位。",
            "- 低交易量不是事件结束理由。",
            "- Polymarket 外链必须使用 `affiliate_url`。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--glossary", type=Path, default=DEFAULT_GLOSSARY)
    parser.add_argument("--date", default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(args.schema.read_text(encoding="utf-8"))
        ensure_columns(conn)
        candidates = fetch_candidates(conn)
        rows = build_rows(candidates, args.date, args.limit)
        write_sqlite(conn, rows, args.date)
    finally:
        conn.close()

    write_csv(rows, args.output)
    write_summary(rows, args.summary, args.date, load_glossary(args.glossary))
    print(f"Ranking rows: {len(rows)}")
    print(f"Wrote CSV: {args.output}")
    print(f"Wrote summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
