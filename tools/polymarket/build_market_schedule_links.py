#!/usr/bin/env python3
"""Build market-to-schedule explanation links from opportunity data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_INPUT = Path("data/polymarket/latest_market_opportunities.csv")
DEFAULT_OUTPUT = Path("data/polymarket/latest_market_schedule_links.csv")
DEFAULT_SUMMARY = Path("data/polymarket/latest_market_schedule_links_summary.md")


def link_type(row: dict[str, str]) -> str:
    if row.get("topic_type") == "champion_or_outright" and row.get("group_code"):
        return "team_group_stage"
    if row.get("topic_type") == "special_event":
        return "tournament_special_event"
    return "manual_review"


def schedule_note(row: dict[str, str]) -> str:
    if row.get("topic_type") == "champion_or_outright" and row.get("group_code"):
        return f"{row.get('canonical_team')} 属于 {row.get('group_code')} 组，当前冠军盘需要结合小组赛路径理解。"
    if row.get("topic_type") == "special_event":
        return "赛事组织特殊事件，和具体单场比赛无直接绑定。"
    return "需要人工补充赛程映射。"


def build_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in rows:
        output.append(
            {
                "topic_id": row.get("topic_id", ""),
                "market_id": row.get("market_id", ""),
                "title": row.get("title", ""),
                "topic_type": row.get("topic_type", ""),
                "canonical_team": row.get("canonical_team", ""),
                "group_code": row.get("group_code", ""),
                "schedule_stage": row.get("schedule_stage", ""),
                "link_type": link_type(row),
                "schedule_note": schedule_note(row),
                "affiliate_url": row.get("affiliate_url", ""),
            }
        )
    return output


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "topic_id",
        "market_id",
        "title",
        "topic_type",
        "canonical_team",
        "group_code",
        "schedule_stage",
        "link_type",
        "schedule_note",
        "affiliate_url",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(rows: list[dict[str, str]], path: Path) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["link_type"]] = counts.get(row["link_type"], 0) + 1
    lines = ["# 市场赛程映射", ""]
    for key, value in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## 规则", "", "- 赛程只作为预测市场机会解释层。", "- 未能映射的市场必须保留人工复核状态。"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    with args.input.open("r", encoding="utf-8", newline="") as handle:
        rows = build_rows(list(csv.DictReader(handle)))
    write_csv(rows, args.output)
    write_summary(rows, args.summary)
    print(f"Schedule links: {len(rows)}")
    print(f"Wrote CSV: {args.output}")
    print(f"Wrote summary: {args.summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
