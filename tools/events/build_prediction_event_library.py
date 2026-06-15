#!/usr/bin/env python3
"""Build the central prediction event library.

The library combines current Polymarket opportunities with event types that
should be monitored as the tournament progresses.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OPPORTUNITIES = ROOT / "data/polymarket/latest_market_opportunities.csv"
MATCHES = ROOT / "data/templates/matches.csv"
GROUPS = ROOT / "data/templates/groups.csv"
TEAMS = ROOT / "data/templates/teams.csv"
GLOSSARY = ROOT / "data/templates/glossary_cn_en.csv"
OUT_DIR = ROOT / "data/prediction_events"
OUT_CSV = OUT_DIR / "latest_prediction_event_library.csv"
OUT_JSON = OUT_DIR / "latest_prediction_event_library.json"
OUT_SUMMARY = OUT_DIR / "latest_prediction_event_library_summary.md"

HEADERS = [
    "library_id",
    "availability",
    "source",
    "platform",
    "market_id",
    "event_category",
    "event_category_cn",
    "event_title",
    "event_title_cn",
    "stage",
    "group_code",
    "match_id",
    "home_team",
    "away_team",
    "market_structure_type",
    "structure_cn",
    "outcome_relation",
    "is_mutually_exclusive",
    "selection_direction",
    "direction_cn",
    "strategy_bucket",
    "risk_tier",
    "rule_check_result",
    "focus_bucket",
    "focus_admission_note",
    "strategy_summary",
    "opportunity_segment",
    "status",
    "price",
    "return_rate",
    "volume_24hr",
    "liquidity",
    "affiliate_url",
    "monitor_trigger",
    "cancel_condition",
    "updated_at",
]

STRUCTURE_CN = {
    "multi_market_mutually_exclusive_group": "多选题互斥组",
    "special_event_binary": "特殊事件二元",
    "binary_single_market": "二元市场",
    "independent_binary": "独立二元",
    "single_match_three_way": "单场三选一",
    "single_match_binary_derivative": "单场二元衍生",
    "stage_reach_binary": "阶段到达二元",
    "group_rank_mutually_exclusive": "小组排名互斥",
    "player_award_mutually_exclusive": "球员奖项互斥",
    "final_pairing_mutually_exclusive": "决赛组合互斥",
}

CATEGORY_CN = {
    "champion_or_outright": "冠军盘",
    "special_event": "特殊事件",
    "single_match_result": "单场赛果",
    "single_match_total_goals": "单场总进球",
    "single_match_handicap": "单场让球",
    "single_match_cards_corners": "单场牌角球",
    "group_winner": "小组第一",
    "group_qualify": "小组出线",
    "group_elimination": "小组出局",
    "round_of_32_reach": "进入32强",
    "round_of_16_reach": "进入16强",
    "quarterfinal_reach": "进入八强",
    "semifinal_reach": "进入半决赛",
    "final_reach": "进入决赛",
    "round_of_32_advance": "32强晋级",
    "round_of_16_advance": "16强晋级",
    "quarterfinal_advance": "八强晋级",
    "semifinal_advance": "半决赛晋级",
    "final_advance": "决赛胜者",
    "third_place_advance": "季军赛胜者",
    "top_scorer": "射手王",
    "player_award": "球员奖项",
    "final_pairing": "决赛对阵",
    "continent_performance": "大洲表现",
}

DIRECTION_CN = {
    "YES": "买 YES",
    "NO": "买 NO",
    "WAIT": "等待",
    "AVOID": "回避",
    "MONITOR": "监控",
}

FOCUS_BUCKET_NONE = "未入选"
FOCUS_ADMISSION_DEFAULT = "未经过人工准入"
MANUAL_FOCUS_ADMISSIONS: dict[str, tuple[str, str]] = {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def glossary() -> dict[str, str]:
    return {row["en"]: row["zh"] for row in read_csv(GLOSSARY)}


def team_map() -> dict[str, dict[str, str]]:
    return {row["team"]: row for row in read_csv(TEAMS)}


def zh(value: str, zh_map: dict[str, str]) -> str:
    return zh_map.get(value, value)


def market_title_cn(title: str, zh_map: dict[str, str]) -> str:
    if title in zh_map:
        return zh_map[title]
    prefix = "Will "
    suffix = " win the 2026 FIFA World Cup?"
    if title.startswith(prefix) and title.endswith(suffix):
        team = title[len(prefix) : -len(suffix)]
        return f"{zh(team, zh_map)}是否赢得2026年世界杯？"
    return title.replace("?", "？")


def as_float(value: str) -> float:
    try:
        return float(value or 0)
    except ValueError:
        return 0.0


def return_rate(price: str) -> str:
    number = as_float(price)
    if number <= 0 or number >= 1:
        return "0%" if number == 1 else ""
    return f"{(1 / number - 1) * 100:.1f}%"


def current_strategy(row: dict[str, str], zh_map: dict[str, str]) -> str:
    team = zh(row.get("canonical_team", ""), zh_map)
    direction = row.get("selection_direction", "")
    segment = row.get("opportunity_segment", "")
    if direction == "YES":
        return f"当前模型方向为买 YES；重点复核价格、成交深度和同组互斥关系。关联对象：{team or '该事件'}。"
    if direction == "AVOID":
        return "当前规则建议回避；只有状态、流动性或市场结构改善后再重新评估。"
    if row.get("recommendation_track") == "upside":
        return "高回报观察；价格空间大，但需要等待更清晰的基本面理由或盘口确认。"
    if segment == "weak_team_related":
        return "弱队相关观察；优先寻找对手方向、进球数、让球或小组出局类市场。"
    return "保留观察；当前没有明确优势信号。"


def strategy_bucket_for(row: dict[str, str]) -> str:
    direction = row.get("selection_direction", "")
    segment = row.get("opportunity_segment", "")
    if direction == "YES":
        return "候选池"
    if direction == "AVOID":
        return "回避策略"
    if segment in {"high_return_watch", "weak_team_related", "swing_team"} or row.get("recommendation_track") == "upside":
        return "候选池"
    if row.get("availability") == "待上架/待发现":
        return "候选池"
    return "普通观察"


def risk_tier_for(row: dict[str, str]) -> str:
    availability = row.get("availability", "")
    direction = row.get("selection_direction", "")
    status = row.get("current_status") or row.get("status", "")
    segment = row.get("opportunity_segment", "")
    category = row.get("topic_type") or row.get("event_category", "")
    price = as_float(row.get("implied_yes_probability") or row.get("price", ""))
    liquidity = as_float(row.get("liquidity", ""))
    if availability != "已上架":
        return "待监控"
    if direction == "AVOID" or status in {"excluded", "closed", "resolved"}:
        return "回避"
    if category == "champion_or_outright":
        return "跨阶段观察"
    return "普通观察"


def focus_admission_for(item: dict[str, str]) -> tuple[str, str]:
    return MANUAL_FOCUS_ADMISSIONS.get(item.get("library_id", ""), (FOCUS_BUCKET_NONE, FOCUS_ADMISSION_DEFAULT))


def rule_check_for(item: dict[str, str]) -> str:
    failures = []
    if not item.get("strategy_summary"):
        failures.append("缺少策略说明")
    if not item.get("structure_cn"):
        failures.append("缺少结构说明")
    if item.get("availability") == "已上架":
        if item.get("price") and not item.get("return_rate"):
            failures.append("价格缺少回报率")
        if item.get("affiliate_url") and "via=serene77mc-g6kj" not in item.get("affiliate_url", ""):
            failures.append("链接缺少邀请码")
    if item.get("focus_bucket") in {"每日关注", "低风险", "高风险", "可选策略"}:
        if item.get("focus_admission_note") in {"", FOCUS_ADMISSION_DEFAULT}:
            failures.append("重点清单缺少人工准入记录")
        if item.get("selection_direction") == "AVOID" and item.get("focus_bucket") != "高风险":
            failures.append("回避方向不能列入重点清单")
        if item.get("status") in {"excluded", "closed", "resolved"}:
            failures.append("结束或排除状态不能列入重点清单")
    return "通过" if not failures else "不通过：" + "；".join(failures)


def base_row(updated_at: str) -> dict[str, str]:
    return {header: "" for header in HEADERS} | {"updated_at": updated_at}


def current_market_rows(updated_at: str, zh_map: dict[str, str]) -> list[dict[str, str]]:
    rows = []
    for row in read_csv(OPPORTUNITIES):
        category = row.get("topic_type") or "current_market"
        structure = row.get("market_structure_type", "")
        direction = row.get("selection_direction", "")
        item = base_row(updated_at)
        item.update(
            {
                "library_id": f"pm-{row.get('topic_id')}",
                "availability": "已上架",
                "source": "polymarket_current_market",
                "platform": "polymarket",
                "market_id": row.get("market_id", ""),
                "event_category": category,
                "event_category_cn": CATEGORY_CN.get(category, category),
                "event_title": row.get("title", ""),
                "event_title_cn": market_title_cn(row.get("title", ""), zh_map),
                "stage": row.get("schedule_stage", ""),
                "group_code": row.get("group_code", ""),
                "home_team": row.get("canonical_team", ""),
                "market_structure_type": structure,
                "structure_cn": STRUCTURE_CN.get(structure, structure),
                "outcome_relation": row.get("outcome_relation", ""),
                "is_mutually_exclusive": "是" if "mutually_exclusive" in structure else "否",
                "selection_direction": direction,
                "direction_cn": DIRECTION_CN.get(direction, direction),
                "opportunity_segment": row.get("opportunity_segment", ""),
                "status": row.get("current_status", ""),
                "price": row.get("implied_yes_probability", ""),
                "return_rate": return_rate(row.get("implied_yes_probability", "")),
                "volume_24hr": row.get("volume_24hr", ""),
                "liquidity": row.get("liquidity", ""),
                "affiliate_url": row.get("affiliate_url", ""),
                "monitor_trigger": "价格、交易量、流动性或球队状态出现明显变化时复核。",
                "cancel_condition": row.get("cancel_condition", ""),
            }
        )
        item["strategy_bucket"] = strategy_bucket_for(item | row)
        item["risk_tier"] = risk_tier_for(item | row)
        item["strategy_summary"] = current_strategy(row, zh_map)
        item["focus_bucket"], item["focus_admission_note"] = focus_admission_for(item)
        item["rule_check_result"] = rule_check_for(item)
        rows.append(item)
    return rows


def add_watch_row(
    rows: list[dict[str, str]],
    updated_at: str,
    *,
    library_id: str,
    category: str,
    title: str,
    stage: str,
    structure: str,
    relation: str,
    strategy: str,
    trigger: str,
    group_code: str = "",
    match_id: str = "",
    home_team: str = "",
    away_team: str = "",
    risk_tier: str = "待监控",
    strategy_bucket: str = "候选池",
) -> None:
    item = base_row(updated_at)
    item.update(
        {
            "library_id": library_id,
            "availability": "待上架/待发现",
            "source": "event_watch_template",
            "platform": "polymarket_first",
            "event_category": category,
            "event_category_cn": CATEGORY_CN.get(category, category),
            "event_title": title,
            "event_title_cn": title,
            "stage": stage,
            "group_code": group_code,
            "match_id": match_id,
            "home_team": home_team,
            "away_team": away_team,
            "market_structure_type": structure,
            "structure_cn": STRUCTURE_CN.get(structure, structure),
            "outcome_relation": relation,
            "is_mutually_exclusive": "是" if "mutually_exclusive" in structure or "three_way" in structure else "否",
            "selection_direction": "MONITOR",
            "direction_cn": DIRECTION_CN["MONITOR"],
            "strategy_bucket": strategy_bucket,
            "risk_tier": risk_tier,
            "focus_bucket": FOCUS_BUCKET_NONE,
            "focus_admission_note": FOCUS_ADMISSION_DEFAULT,
            "strategy_summary": strategy,
            "opportunity_segment": "watch_template",
            "status": "watch_template",
            "monitor_trigger": trigger,
            "cancel_condition": "市场未上架、规则不清晰、流动性不足或无法写出明确策略时不参与。",
        }
    )
    item["rule_check_result"] = rule_check_for(item)
    rows.append(item)


def is_secondary_strong_vs_strong(home: dict[str, str], away: dict[str, str]) -> bool:
    home_tier = home.get("tier", "")
    away_tier = away.get("tier", "")
    tiers = {home_tier, away_tier}
    return "strong" in tiers and bool(tiers & {"elite", "strong"}) and home_tier in {"elite", "strong"} and away_tier in {"elite", "strong"} and home.get("team") != away.get("team")


def watch_template_rows(updated_at: str, zh_map: dict[str, str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    teams = team_map()
    for match in read_csv(MATCHES):
        home = zh(match.get("home_team", ""), zh_map)
        away = zh(match.get("away_team", ""), zh_map)
        title_base = f"{home} 对阵 {away}"
        match_id = match.get("match_id", "")
        stage = match.get("stage", "")
        group = match.get("group", "")
        if stage == "Group":
            add_watch_row(
                rows,
                updated_at,
                library_id=f"watch-{match_id}-result",
                category="single_match_result",
                title=f"{title_base} 单场赛果",
                stage="小组赛",
                group_code=group,
                match_id=match_id,
                home_team=match.get("home_team", ""),
                away_team=match.get("away_team", ""),
                structure="single_match_three_way",
                relation="home_draw_away",
                strategy="根据强弱差、主场、赛程动机判断胜平负；强弱明显时看强队胜，实力接近时重点看平局和低比分。",
                trigger="单场赛果、胜平负、比赛胜者类市场上架。",
            )
            add_watch_row(
                rows,
                updated_at,
                library_id=f"watch-{match_id}-goals",
                category="single_match_total_goals",
                title=f"{title_base} 总进球",
                stage="小组赛",
                group_code=group,
                match_id=match_id,
                home_team=match.get("home_team", ""),
                away_team=match.get("away_team", ""),
                structure="single_match_binary_derivative",
                relation="over_under",
                strategy="强队打弱队看大比分和强队进球数；两队接近且首战谨慎时看小球或平局保护。",
                trigger="总进球、双方进球、球队进球数类市场上架。",
            )
            home_info = teams.get(match.get("home_team", ""), {})
            away_info = teams.get(match.get("away_team", ""), {})
            if is_secondary_strong_vs_strong(home_info | {"team": match.get("home_team", "")}, away_info | {"team": match.get("away_team", "")}):
                add_watch_row(
                    rows,
                    updated_at,
                    library_id=f"watch-{match_id}-secondary-strong",
                    category="single_match_result",
                    title=f"{title_base} 次级强队挑战盘",
                    stage="小组赛",
                    group_code=group,
                    match_id=match_id,
                    home_team=match.get("home_team", ""),
                    away_team=match.get("away_team", ""),
                    structure="single_match_three_way",
                    relation="home_draw_away_or_handicap",
                    strategy="次级强队或强队互打，不直接追热门强队；优先观察平局、受让、双方进球或总进球等回报更合理的路径。",
                    trigger="胜平负、受让、双方进球、总进球等市场上架，且价格给出合理回报。",
                    strategy_bucket="候选池",
                )
        else:
            add_watch_row(
                rows,
                updated_at,
                library_id=f"watch-{match_id}-advance",
                category=f"{stage.lower().replace(' ', '_')}_advance",
                title=f"{title_base} 淘汰赛晋级",
                stage=stage,
                match_id=match_id,
                structure="single_match_binary_derivative",
                relation="team_a_or_team_b_advance",
                strategy="淘汰赛优先看晋级而不是90分钟胜负；结合加时、点球和路径消耗判断。",
                trigger="淘汰赛晋级、比赛胜者、加时/点球相关市场上架。",
            )
    for group in read_csv(GROUPS):
        code = group.get("group_code", "")
        group_team_names = "、".join(zh(team.strip(), zh_map) for team in group.get("teams", "").split(";") if team.strip())
        for category, title_suffix, strategy in [
            ("group_winner", "小组第一", "看强队稳定性、赛程顺序和净胜球动机；热门过热时等待回调。"),
            ("group_qualify", "小组出线", "摇摆队核心市场；重点比较第二名、第三名和同组直接对话。"),
            ("group_elimination", "小组出局", "弱队和死亡组价值区；低关注小组可能出现信息差。"),
        ]:
            add_watch_row(
                rows,
                updated_at,
                library_id=f"watch-group-{code}-{category}",
                category=category,
                title=f"{code}组{title_suffix}：{group_team_names}",
                stage="小组赛",
                group_code=code,
                structure="group_rank_mutually_exclusive",
                relation="group_rank_or_qualification",
                strategy=strategy,
                trigger=f"{code}组{title_suffix}、出线、淘汰或排名市场上架。",
            )
    complex_events = [
        ("round_of_32_reach", "进入32强", "stage_reach_binary", "球队是否进入32强", "小组赛中后段根据积分形势、第三名规则和最后一轮动机判断。"),
        ("round_of_16_reach", "进入16强", "stage_reach_binary", "球队是否进入16强", "32强对阵确定后，重点看路径难度和热门队过热。"),
        ("quarterfinal_reach", "进入八强", "stage_reach_binary", "球队是否进入八强", "强队路径盘的核心；适合和冠军盘联动比较。"),
        ("semifinal_reach", "进入半决赛", "stage_reach_binary", "球队是否进入半决赛", "八强路径清晰后重点看半区强弱和伤停。"),
        ("final_reach", "进入决赛", "stage_reach_binary", "球队是否进入决赛", "半决赛前后重点监控价格收敛和公众热度。"),
        ("top_scorer", "射手王", "player_award_mutually_exclusive", "球员射手王", "结合小组对手强弱、点球权、球队预计场次和赔率热度。"),
        ("player_award", "最佳球员/金球", "player_award_mutually_exclusive", "球员奖项", "通常跟冠军路径强相关，避免孤立判断。"),
        ("final_pairing", "决赛对阵组合", "final_pairing_mutually_exclusive", "决赛双方", "淘汰赛签表明确后监控高回报组合。"),
        ("continent_performance", "大洲表现", "binary_single_market", "大洲最佳成绩", "适合观察非欧洲/南美球队突破时的叙事机会。"),
    ]
    for category, title, structure, relation, strategy in complex_events:
        add_watch_row(
            rows,
            updated_at,
            library_id=f"watch-complex-{category}",
            category=category,
            title=title,
            stage="跨阶段",
            structure=structure,
            relation=relation,
            strategy=strategy,
            trigger=f"{title}相关市场上架或交易量开始增长。",
        )
    stage_targets = [
        ("round_of_32_reach", "进入32强", "小组赛阶段强队进入32强属于基础路径事件；价格过低或阵容异常则取消。"),
        ("round_of_16_reach", "进入16强", "强队进入16强需要结合32强潜在对手和路径难度复核。"),
        ("quarterfinal_reach", "进入八强", "强队进入八强属于阶段到达候选，必须先确认路径和准入理由。"),
        ("semifinal_reach", "进入半决赛", "强队进入半决赛风险上升，只作为候选观察，等待签表和对手确认。"),
    ]
    for team, info in teams.items():
        if info.get("tier") != "elite":
            continue
        team_cn = zh(team, zh_map)
        for category, label, strategy in stage_targets:
            add_watch_row(
                rows,
                updated_at,
                library_id=f"watch-team-stage-{team}-{category}".replace(" ", "-").lower(),
                category=category,
                title=f"{team_cn}{label}",
                stage="跨阶段",
                group_code=info.get("group_code", ""),
                home_team=team,
                structure="stage_reach_binary",
                relation="team_reaches_stage_yes_no",
                strategy=strategy,
                trigger=f"{team_cn}{label}相关市场上架，且价格与赛程路径匹配。",
                strategy_bucket="候选池",
            )
    return rows


def write_summary(rows: list[dict[str, str]]) -> None:
    availability: dict[str, int] = {}
    categories: dict[str, int] = {}
    current_yes = 0
    risk_counts: dict[str, int] = {}
    focus_counts: dict[str, int] = {}
    for row in rows:
        availability[row["availability"]] = availability.get(row["availability"], 0) + 1
        categories[row["event_category_cn"]] = categories.get(row["event_category_cn"], 0) + 1
        risk_counts[row["risk_tier"]] = risk_counts.get(row["risk_tier"], 0) + 1
        focus_counts[row["focus_bucket"]] = focus_counts.get(row["focus_bucket"], 0) + 1
        if row["selection_direction"] == "YES":
            current_yes += 1
    lines = [
        "# 预测事件库摘要",
        "",
        f"- 事件总数：{len(rows)}",
        f"- 底层模型 YES 方向：{current_yes}",
        f"- 入选重点清单：{sum(value for key, value in focus_counts.items() if key != FOCUS_BUCKET_NONE)}",
        "",
        "## 上架状态",
    ]
    lines.extend(f"- {key}：{value}" for key, value in sorted(availability.items()))
    lines.extend(["", "## 风险分层"])
    lines.extend(f"- {key}：{value}" for key, value in sorted(risk_counts.items()))
    lines.extend(["", "## 重点清单准入"])
    lines.extend(f"- {key}：{value}" for key, value in sorted(focus_counts.items()))
    lines.extend(["", "## 类型分布"])
    lines.extend(f"- {key}：{value}" for key, value in sorted(categories.items(), key=lambda item: item[0]))
    OUT_SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    updated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    zh_map = glossary()
    rows = current_market_rows(updated_at, zh_map)
    rows.extend(watch_template_rows(updated_at, zh_map))
    write_csv(OUT_CSV, rows)
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_summary(rows)
    print(f"Wrote {OUT_CSV.relative_to(ROOT)} ({len(rows)} rows)")
    print(f"Wrote {OUT_JSON.relative_to(ROOT)}")
    print(f"Wrote {OUT_SUMMARY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
