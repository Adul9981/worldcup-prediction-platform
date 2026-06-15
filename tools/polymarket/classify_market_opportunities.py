#!/usr/bin/env python3
"""Classify prediction market structures and model-side trading directions."""

from __future__ import annotations

import argparse
import csv
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DB = Path("data/worldcup_prediction.db")
DEFAULT_SCHEMA = Path("models/schema.sql")
DEFAULT_OUTPUT = Path("data/polymarket/latest_market_opportunities.csv")
DEFAULT_SUMMARY = Path("data/polymarket/latest_market_opportunities_summary.md")
DEFAULT_GLOSSARY = Path("data/templates/glossary_cn_en.csv")


@dataclass
class OpportunityRow:
    analyzed_at: str
    topic_id: str
    platform: str
    event_slug: str
    market_id: str
    title: str
    topic_type: str
    canonical_team: str
    group_code: str
    market_structure_type: str
    outcome_relation: str
    neg_risk_status: str
    current_status: str
    implied_yes_probability: float
    volume: float
    volume_24hr: float
    liquidity: float
    open_interest: float
    recommendation_track: str
    selection_direction: str
    direction_confidence: str
    direction_source: str
    opportunity_segment: str
    schedule_stage: str
    direction_thesis: str
    cancel_condition: str
    affiliate_url: str


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


def thesis_zh(text: str) -> str:
    if text == "Model direction is YES; price, risk and score passed current rules.":
        return "模型方向为买 YES；价格、风险和评分通过当前规则。"
    if text == "No current edge signal; keep it in the watch pool.":
        return "当前没有明确优势信号，保留在观察池。"
    if text == "Conservative profile is visible; wait for price or thesis confirmation before entry.":
        return "存在稳健观察特征，等待价格或交易理由确认。"
    if text == "Upside profile is visible; wait for price, quota, or thesis confirmation before entry.":
        return "存在高盈亏比观察特征，等待价格或交易理由确认。"
    if text == "Price is already rich; no model edge without a stronger thesis.":
        return "当前价格偏贵，缺少更强交易理由前不进入。"
    if text.startswith("Avoid: status/risk rules block entry for "):
        return "回避：状态或风险规则阻止进入。"
    return text


def fetch_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
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
        ),
        event_counts AS (
            SELECT event_slug, COUNT(*) AS event_market_count
            FROM prediction_market_topics
            WHERE latest_seen_at = (SELECT MAX(latest_seen_at) FROM prediction_market_topics)
            GROUP BY event_slug
        )
        SELECT
            p.topic_id,
            p.platform,
            p.event_slug,
            p.market_id,
            p.title,
            p.topic_type,
            p.canonical_team,
            p.group_code,
            p.current_status,
            mss.best_ask,
            mss.last_trade_price,
            mss.volume,
            mss.volume_24hr,
            mss.liquidity,
            mss.open_interest,
            p.affiliate_url,
            ec.event_market_count,
            s.recommendation_track,
            s.risk_score,
            s.conservative_score,
            s.upside_score,
            ctm.tier,
            ctm.weak_team_level,
            ctm.swing_level,
            ctm.strong_team_level,
            ctm.attention_level,
            st.action_label AS stake_action_label,
            st.recommended_stake_units,
            st.cancel_condition
        FROM prediction_market_topics p
        LEFT JOIN market_status_snapshots mss
          ON p.topic_id = mss.topic_id
         AND mss.captured_at = p.latest_seen_at
        LEFT JOIN latest_scores s
          ON p.topic_id = s.topic_id
        LEFT JOIN polymarket_champion_team_map ctm
          ON p.market_id = ctm.market_id
         AND ctm.discovered_at = p.latest_seen_at
        LEFT JOIN latest_stakes st
          ON p.topic_id = st.topic_id
        LEFT JOIN event_counts ec
          ON p.event_slug = ec.event_slug
        WHERE p.latest_seen_at = (SELECT MAX(latest_seen_at) FROM prediction_market_topics)
        ORDER BY p.event_slug, p.title
        """
    )
    return [dict(row) for row in cursor.fetchall()]


def structure_for(row: dict[str, Any]) -> tuple[str, str]:
    event_count = int(as_float(row.get("event_market_count")))
    topic_type = str(row.get("topic_type") or "")
    event_slug = str(row.get("event_slug") or "")
    if topic_type == "champion_or_outright" and event_count > 1:
        return "multi_market_mutually_exclusive_group", "one_winner_with_yes_no_submarkets"
    if topic_type == "special_event":
        return "special_event_binary", "single_yes_no"
    if event_count == 1:
        return "independent_binary", "single_yes_no"
    if event_slug:
        return "non_exclusive_related_markets", "related_unknown"
    return "unknown_structure", "manual_review_required"


def direction_for(row: dict[str, Any]) -> tuple[str, str, str, str]:
    status = str(row.get("current_status") or "")
    track = str(row.get("recommendation_track") or "")
    stake = as_float(row.get("recommended_stake_units"))
    risk = as_float(row.get("risk_score"))
    implied = as_float(row.get("best_ask")) or as_float(row.get("last_trade_price"))
    title = str(row.get("title") or "This market")

    if status in {"excluded", "closed", "resolved"} or risk >= 70:
        return (
            "AVOID",
            "high",
            "scoring_model",
            f"Avoid: status/risk rules block entry for {title}.",
        )
    if stake > 0:
        confidence = "medium" if stake < 1 else "high"
        return (
            "YES",
            confidence,
            "scoring_model",
            "Model direction is YES; price, risk and score passed current rules.",
        )
    if track == "conservative":
        return (
            "WAIT",
            "medium",
            "scoring_model",
            "Conservative profile is visible; wait for price or thesis confirmation before entry.",
        )
    if track == "upside":
        return (
            "WAIT",
            "medium",
            "scoring_model",
            "Upside profile is visible; wait for price, quota, or thesis confirmation before entry.",
        )
    if implied >= 0.25:
        return (
            "WAIT",
            "low",
            "model",
            "Price is already rich; no model edge without a stronger thesis.",
        )
    return (
        "WAIT",
        "low",
        "model",
        "No current edge signal; keep it in the watch pool.",
    )


def opportunity_segment_for(row: dict[str, Any], structure: str, direction: str) -> str:
    status = str(row.get("current_status") or "")
    tier = str(row.get("tier") or "")
    weak = str(row.get("weak_team_level") or "")
    swing = str(row.get("swing_level") or "")
    strong = str(row.get("strong_team_level") or "")
    attention = str(row.get("attention_level") or "")
    implied = as_float(row.get("best_ask")) or as_float(row.get("last_trade_price"))
    event_count = int(as_float(row.get("event_market_count")))

    if direction == "AVOID" or status in {"excluded", "closed", "resolved"}:
        return "risk_avoid"
    if structure == "special_event_binary":
        return "special_event"
    if event_count > 1 and implied >= 0.15:
        return "mutual_group_high_price_anchor"
    if tier == "elite" or strong == "high":
        return "strong_team"
    if weak == "high":
        return "weak_team_related"
    if swing == "high" or tier == "strong":
        return "swing_team"
    if attention in {"very_high", "high"} and implied >= 0.10:
        return "overheat_risk"
    if direction == "YES":
        return "buy_direction"
    if implied and implied <= 0.005:
        return "high_return_watch"
    return "normal_watch"


def schedule_stage_for(row: dict[str, Any]) -> str:
    if str(row.get("topic_type") or "") == "champion_or_outright":
        return "冠军盘 / 小组赛前置定价"
    if str(row.get("topic_type") or "") == "special_event":
        return "赛事组织特殊事件"
    group_code = str(row.get("group_code") or "")
    return f"{group_code}组相关" if group_code else "赛程待映射"


def build_rows(rows: list[dict[str, Any]], analyzed_at: str) -> list[OpportunityRow]:
    output: list[OpportunityRow] = []
    for row in rows:
        structure, relation = structure_for(row)
        direction, confidence, source, thesis = direction_for(row)
        implied = as_float(row.get("best_ask")) or as_float(row.get("last_trade_price"))
        output.append(
            OpportunityRow(
                analyzed_at=analyzed_at,
                topic_id=str(row.get("topic_id") or ""),
                platform=str(row.get("platform") or ""),
                event_slug=str(row.get("event_slug") or ""),
                market_id=str(row.get("market_id") or ""),
                title=str(row.get("title") or ""),
                topic_type=str(row.get("topic_type") or ""),
                canonical_team=str(row.get("canonical_team") or ""),
                group_code=str(row.get("group_code") or ""),
                market_structure_type=structure,
                outcome_relation=relation,
                neg_risk_status="neg_risk_unknown",
                current_status=str(row.get("current_status") or ""),
                implied_yes_probability=round(implied, 4),
                volume=round(as_float(row.get("volume")), 4),
                volume_24hr=round(as_float(row.get("volume_24hr")), 4),
                liquidity=round(as_float(row.get("liquidity")), 4),
                open_interest=round(as_float(row.get("open_interest")), 4),
                recommendation_track=str(row.get("recommendation_track") or ""),
                selection_direction=direction,
                direction_confidence=confidence,
                direction_source=source,
                opportunity_segment=opportunity_segment_for(row, structure, direction),
                schedule_stage=schedule_stage_for(row),
                direction_thesis=thesis,
                cancel_condition=str(row.get("cancel_condition") or "Cancel if market closes, liquidity disappears, or thesis cannot be written in one sentence."),
                affiliate_url=str(row.get("affiliate_url") or ""),
            )
        )
    return output


def write_csv(rows: list[OpportunityRow], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(OpportunityRow.__dataclass_fields__.keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)


def ensure_columns(conn: sqlite3.Connection) -> None:
    existing = {row[1] for row in conn.execute("PRAGMA table_info(market_opportunities)")}
    additions = {
        "volume": "REAL DEFAULT 0",
        "volume_24hr": "REAL DEFAULT 0",
        "liquidity": "REAL DEFAULT 0",
        "open_interest": "REAL DEFAULT 0",
        "canonical_team": "TEXT",
        "group_code": "TEXT",
        "opportunity_segment": "TEXT",
        "schedule_stage": "TEXT",
    }
    for column, definition in additions.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE market_opportunities ADD COLUMN {column} {definition}")


def write_sqlite(conn: sqlite3.Connection, rows: list[OpportunityRow], analyzed_at: str) -> None:
    ensure_columns(conn)
    columns = list(OpportunityRow.__dataclass_fields__.keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    with conn:
        conn.execute("DELETE FROM market_opportunities WHERE analyzed_at = ?", (analyzed_at,))
        conn.executemany(
            f"""
            INSERT OR REPLACE INTO market_opportunities ({", ".join(columns)})
            VALUES ({placeholders})
            """,
            [asdict(row) for row in rows],
        )


def write_summary(rows: list[OpportunityRow], path: Path, analyzed_at: str, glossary: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    by_structure: dict[str, int] = {}
    by_direction: dict[str, int] = {}
    for row in rows:
        by_structure[row.market_structure_type] = by_structure.get(row.market_structure_type, 0) + 1
        by_direction[row.selection_direction] = by_direction.get(row.selection_direction, 0) + 1
    lines = [
        "# 预测市场机会",
        "",
        f"- 分析时间: `{analyzed_at}`",
        f"- 选题数量: `{len(rows)}`",
        "",
        "## 选题结构",
        "",
    ]
    for key, value in sorted(by_structure.items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## 下注方向", ""])
    for key, value in sorted(by_direction.items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## 买 YES 方向", ""])
    positive = [row for row in rows if row.selection_direction == "YES"]
    if not positive:
        lines.append("- None")
    for row in positive[:20]:
        lines.append(
            f"- {market_title_zh(row.title, glossary)}：买 YES，{zh(row.market_structure_type, glossary)}。{thesis_zh(row.direction_thesis)}"
        )
    lines.extend(
        [
            "",
            "## 规则检查",
            "",
            "- 预测市场选题是主分析单位。",
            "- 已包含选题结构。",
            "- 已标记方向：YES / WAIT / AVOID。",
            "- 本机会层只输出方向和分析，不输出下注数量。",
            "- `neg_risk_status` 在捕获官方字段前保持未知。",
            "- 当前仍为只读分析。",
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
    args = parser.parse_args()

    analyzed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    conn = sqlite3.connect(args.db)
    try:
        conn.executescript(args.schema.read_text(encoding="utf-8"))
        rows = build_rows(fetch_rows(conn), analyzed_at)
        write_sqlite(conn, rows, analyzed_at)
    finally:
        conn.close()

    write_csv(rows, args.output)
    write_summary(rows, args.summary, analyzed_at, load_glossary(args.glossary))
    print(f"Opportunity rows: {len(rows)}")
    print(f"Wrote CSV: {args.output}")
    print(f"Wrote summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
