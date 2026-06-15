#!/usr/bin/env python3
"""Build the local 2026 World Cup schedule dataset.

The group-stage teams come from data/templates/groups.csv. Knockout matches are
kept as Chinese placeholders until qualifiers are known.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
GROUPS_CSV = ROOT / "data/templates/groups.csv"
MATCHES_CSV = ROOT / "data/templates/matches.csv"
SUMMARY_PATH = ROOT / "data/templates/matches_summary.md"

HEADERS = [
    "match_id",
    "date",
    "utc_time",
    "local_time",
    "china_time",
    "stage",
    "group",
    "home_team",
    "away_team",
    "venue",
    "city",
    "priority",
    "watch_status",
    "home_motivation",
    "away_motivation",
    "lineup_confidence",
    "weather_note",
    "referee_note",
    "market_note",
    "initial_prediction",
    "event_focus",
    "no_bet_reason",
    "review_status",
]

ET = timezone(timedelta(hours=-4))
UTC = timezone.utc

MATCH_TIME_ET = {
    "M001": "2026-06-11 15:00",
    "M002": "2026-06-11 22:00",
    "M007": "2026-06-12 15:00",
    "M019": "2026-06-12 21:00",
    "M008": "2026-06-13 15:00",
    "M013": "2026-06-13 18:00",
    "M014": "2026-06-13 21:00",
    "M020": "2026-06-14 00:00",
    "M025": "2026-06-14 13:00",
    "M031": "2026-06-14 16:00",
    "M026": "2026-06-14 19:00",
    "M032": "2026-06-14 22:00",
    "M043": "2026-06-15 12:00",
    "M037": "2026-06-15 15:00",
    "M044": "2026-06-15 18:00",
    "M038": "2026-06-15 21:00",
    "M049": "2026-06-16 15:00",
    "M050": "2026-06-16 18:00",
    "M055": "2026-06-16 21:00",
    "M056": "2026-06-17 00:00",
    "M061": "2026-06-17 13:00",
    "M067": "2026-06-17 16:00",
    "M068": "2026-06-17 19:00",
    "M062": "2026-06-17 22:00",
    "M004": "2026-06-18 12:00",
    "M010": "2026-06-18 15:00",
    "M009": "2026-06-18 18:00",
    "M003": "2026-06-18 21:00",
    "M021": "2026-06-19 15:00",
    "M016": "2026-06-19 18:00",
    "M015": "2026-06-19 20:30",
    "M022": "2026-06-19 23:00",
    "M033": "2026-06-20 13:00",
    "M027": "2026-06-20 16:00",
    "M028": "2026-06-20 20:00",
    "M034": "2026-06-21 00:00",
    "M045": "2026-06-21 12:00",
    "M039": "2026-06-21 15:00",
    "M046": "2026-06-21 18:00",
    "M040": "2026-06-21 21:00",
    "M057": "2026-06-22 13:00",
    "M051": "2026-06-22 17:00",
    "M052": "2026-06-22 20:00",
    "M058": "2026-06-22 23:00",
    "M063": "2026-06-23 13:00",
    "M069": "2026-06-23 16:00",
    "M070": "2026-06-23 19:00",
    "M064": "2026-06-23 22:00",
    "M012": "2026-06-24 15:00",
    "M011": "2026-06-24 15:00",
    "M018": "2026-06-24 18:00",
    "M017": "2026-06-24 18:00",
    "M005": "2026-06-24 21:00",
    "M006": "2026-06-24 21:00",
    "M029": "2026-06-25 16:00",
    "M030": "2026-06-25 16:00",
    "M035": "2026-06-25 19:00",
    "M036": "2026-06-25 19:00",
    "M024": "2026-06-25 22:00",
    "M023": "2026-06-25 22:00",
    "M053": "2026-06-26 15:00",
    "M054": "2026-06-26 15:00",
    "M048": "2026-06-26 20:00",
    "M047": "2026-06-26 20:00",
    "M041": "2026-06-26 23:00",
    "M042": "2026-06-26 23:00",
    "M072": "2026-06-27 17:00",
    "M071": "2026-06-27 17:00",
    "M065": "2026-06-27 19:30",
    "M066": "2026-06-27 19:30",
    "M060": "2026-06-27 22:00",
    "M059": "2026-06-27 22:00",
}


def kickoff_fields(match_id: str) -> dict[str, str]:
    value = MATCH_TIME_ET.get(match_id)
    if not value:
        return {"utc_time": "", "local_time": "", "china_time": ""}
    et_time = datetime.strptime(value, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    utc_time = et_time.astimezone(UTC)
    china_time = et_time.astimezone(timezone(timedelta(hours=8)))
    return {
        "utc_time": utc_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_time": f"{et_time.strftime('%Y-%m-%d %H:%M')} ET",
        "china_time": china_time.strftime("%Y-%m-%d %H:%M"),
    }


def read_groups() -> dict[str, list[str]]:
    with GROUPS_CSV.open("r", encoding="utf-8", newline="") as handle:
      return {
          row["group_code"]: [team.strip() for team in row["teams"].split(";") if team.strip()]
          for row in csv.DictReader(handle)
      }


def priority_for(group: str, home: str, away: str) -> str:
    high_groups = {"C", "D", "H", "I", "J", "K", "L"}
    if group in high_groups:
        return "A"
    headline_teams = {
        "Argentina",
        "Brazil",
        "England",
        "France",
        "Germany",
        "Mexico",
        "Portugal",
        "Spain",
        "United States",
    }
    if home in headline_teams or away in headline_teams:
        return "A"
    return "B"


def group_match_rows() -> list[dict[str, str]]:
    groups = read_groups()
    match_days = {
        "A": ["2026-06-11", "2026-06-12", "2026-06-18", "2026-06-18", "2026-06-24", "2026-06-24"],
        "B": ["2026-06-12", "2026-06-13", "2026-06-18", "2026-06-18", "2026-06-24", "2026-06-24"],
        "C": ["2026-06-13", "2026-06-13", "2026-06-19", "2026-06-19", "2026-06-24", "2026-06-24"],
        "D": ["2026-06-12", "2026-06-13", "2026-06-19", "2026-06-19", "2026-06-25", "2026-06-25"],
        "E": ["2026-06-14", "2026-06-14", "2026-06-20", "2026-06-20", "2026-06-25", "2026-06-25"],
        "F": ["2026-06-14", "2026-06-14", "2026-06-20", "2026-06-20", "2026-06-25", "2026-06-25"],
        "G": ["2026-06-15", "2026-06-15", "2026-06-21", "2026-06-21", "2026-06-26", "2026-06-26"],
        "H": ["2026-06-15", "2026-06-15", "2026-06-21", "2026-06-21", "2026-06-26", "2026-06-26"],
        "I": ["2026-06-16", "2026-06-16", "2026-06-22", "2026-06-22", "2026-06-26", "2026-06-26"],
        "J": ["2026-06-16", "2026-06-16", "2026-06-22", "2026-06-22", "2026-06-27", "2026-06-27"],
        "K": ["2026-06-17", "2026-06-17", "2026-06-23", "2026-06-23", "2026-06-27", "2026-06-27"],
        "L": ["2026-06-17", "2026-06-17", "2026-06-23", "2026-06-23", "2026-06-27", "2026-06-27"],
    }
    pairings = [(0, 1), (2, 3), (0, 2), (3, 1), (3, 0), (1, 2)]
    rows: list[dict[str, str]] = []
    index = 1
    for group in "ABCDEFGHIJKL":
        teams = groups[group]
        for slot, (home_idx, away_idx) in enumerate(pairings):
            home = teams[home_idx]
            away = teams[away_idx]
            rows.append(
                match_row(
                    match_id=f"M{index:03d}",
                    date=match_days[group][slot],
                    stage="Group",
                    group=group,
                    home_team=home,
                    away_team=away,
                    priority=priority_for(group, home, away),
                    event_focus="90min result;team total;qualification path;cards;corners",
                )
            )
            index += 1
    return rows


def knockout_rows(start_index: int) -> list[dict[str, str]]:
    specs: list[tuple[str, str, int]] = [
        ("Round of 32", "2026-06-28", 3),
        ("Round of 32", "2026-06-29", 3),
        ("Round of 32", "2026-06-30", 3),
        ("Round of 32", "2026-07-01", 3),
        ("Round of 32", "2026-07-02", 2),
        ("Round of 32", "2026-07-03", 2),
        ("Round of 16", "2026-07-04", 2),
        ("Round of 16", "2026-07-05", 2),
        ("Round of 16", "2026-07-06", 2),
        ("Round of 16", "2026-07-07", 2),
        ("Quarterfinal", "2026-07-09", 2),
        ("Quarterfinal", "2026-07-10", 1),
        ("Quarterfinal", "2026-07-11", 1),
        ("Semifinal", "2026-07-14", 1),
        ("Semifinal", "2026-07-15", 1),
        ("Third Place", "2026-07-18", 1),
        ("Final", "2026-07-19", 1),
    ]
    rows: list[dict[str, str]] = []
    index = start_index
    stage_counts: dict[str, int] = {}
    for stage, date, count in specs:
        for _ in range(count):
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            slot = stage_counts[stage]
            rows.append(
                match_row(
                    match_id=f"M{index:03d}",
                    date=date,
                    stage=stage,
                    group="",
                    home_team=f"{stage_label(stage)}待定{slot}A",
                    away_team=f"{stage_label(stage)}待定{slot}B",
                    priority="A" if stage in {"Semifinal", "Final"} else "B",
                    event_focus="winner;advance;champion path;extra time;penalties",
                )
            )
            index += 1
    return rows


def stage_label(stage: str) -> str:
    return {
        "Round of 32": "32强",
        "Round of 16": "16强",
        "Quarterfinal": "八强",
        "Semifinal": "半决赛",
        "Third Place": "季军赛",
        "Final": "决赛",
    }[stage]


def match_row(
    *,
    match_id: str,
    date: str,
    stage: str,
    group: str,
    home_team: str,
    away_team: str,
    priority: str,
    event_focus: str,
) -> dict[str, str]:
    time_fields = kickoff_fields(match_id)
    return {
        "match_id": match_id,
        "date": date,
        "utc_time": time_fields["utc_time"],
        "local_time": time_fields["local_time"],
        "china_time": time_fields["china_time"],
        "stage": stage,
        "group": group,
        "home_team": home_team,
        "away_team": away_team,
        "venue": "待补",
        "city": "待补",
        "priority": priority,
        "watch_status": "waiting",
        "home_motivation": "",
        "away_motivation": "",
        "lineup_confidence": "",
        "weather_note": "",
        "referee_note": "",
        "market_note": "",
        "initial_prediction": "",
        "event_focus": event_focus,
        "no_bet_reason": "",
        "review_status": "pending",
    }


def write_rows(rows: list[dict[str, str]]) -> None:
    MATCHES_CSV.parent.mkdir(parents=True, exist_ok=True)
    with MATCHES_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, str]]) -> None:
    by_stage: dict[str, int] = {}
    for row in rows:
        by_stage[row["stage"]] = by_stage.get(row["stage"], 0) + 1
    lines = [
        "# 世界杯赛程库摘要",
        "",
        f"- 总比赛槽位：{len(rows)}",
        f"- 小组赛：{by_stage.get('Group', 0)}",
        f"- 32强：{by_stage.get('Round of 32', 0)}",
        f"- 16强：{by_stage.get('Round of 16', 0)}",
        f"- 八强：{by_stage.get('Quarterfinal', 0)}",
        f"- 半决赛：{by_stage.get('Semifinal', 0)}",
        f"- 季军赛：{by_stage.get('Third Place', 0)}",
        f"- 决赛：{by_stage.get('Final', 0)}",
        "",
        "说明：小组赛球队来自本地分组库；淘汰赛使用占位队名，待晋级队伍确定后替换。",
    ]
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    rows = group_match_rows()
    rows.extend(knockout_rows(len(rows) + 1))
    write_rows(rows)
    write_summary(rows)
    print(f"Wrote {MATCHES_CSV.relative_to(ROOT)} ({len(rows)} rows)")
    print(f"Wrote {SUMMARY_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
