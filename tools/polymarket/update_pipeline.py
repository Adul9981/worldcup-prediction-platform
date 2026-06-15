#!/usr/bin/env python3
"""Run the local Polymarket data rebuild pipeline.

Default mode uses the latest local Polymarket snapshot. Pass --fetch to refresh
from Polymarket before rebuilding derived files.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data/polymarket/latest_refresh_status.json"


def run_step(args: list[str]) -> None:
    print("$", " ".join(args))
    subprocess.run(args, cwd=ROOT, check=True)


def count_csv(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in csv.DictReader(handle)), 0)


def first_csv_value(path: Path, column: str) -> str:
    if not path.exists():
        return ""
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            return str(row.get(column) or "")
    return ""


def write_status(fetched: bool, status: str, error: str = "") -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": status,
        "fetched_from_polymarket": fetched,
        "source_snapshot_at": first_csv_value(ROOT / "data/polymarket/latest_polymarket_worldcup_markets.csv", "discovered_at"),
        "market_rows": count_csv(ROOT / "data/polymarket/latest_polymarket_worldcup_markets.csv"),
        "topic_rows": count_csv(ROOT / "data/polymarket/latest_prediction_market_topics.csv"),
        "opportunity_rows": count_csv(ROOT / "data/polymarket/latest_market_opportunities.csv"),
        "match_rows": count_csv(ROOT / "data/templates/matches.csv"),
        "schedule_link_rows": count_csv(ROOT / "data/polymarket/latest_market_schedule_links.csv"),
        "daily_ranking_rows": count_csv(ROOT / "data/polymarket/latest_daily_event_rankings.csv"),
        "error": error,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Fetch the latest Polymarket World Cup markets before rebuilding local outputs.",
    )
    args = parser.parse_args()

    python = sys.executable
    try:
        if args.fetch:
            run_step([python, "tools/polymarket/discover_worldcup_markets.py"])

        steps = [
            [python, "tools/schedule/build_worldcup_schedule.py"],
            [python, "tools/polymarket/import_markets_to_sqlite.py"],
            [python, "tools/polymarket/map_champion_markets.py"],
            [python, "tools/polymarket/update_topic_status.py"],
            [python, "tools/polymarket/score_topics.py"],
            [python, "tools/polymarket/classify_market_opportunities.py"],
            [python, "tools/polymarket/build_market_schedule_links.py"],
            [python, "tools/polymarket/generate_daily_rankings.py"],
            [python, "tools/events/build_prediction_event_library.py"],
        ]
        for step in steps:
            run_step(step)
    except subprocess.CalledProcessError as exc:
        write_status(args.fetch, "failed", str(exc))
        raise

    write_status(args.fetch, "ok")
    print(f"Wrote refresh status: {STATUS_PATH.relative_to(ROOT)}")
    print("Pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
