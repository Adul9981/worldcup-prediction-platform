#!/usr/bin/env python3
"""Run the Polymarket refresh pipeline on a fixed interval.

This is intentionally read-only: it only fetches public market data and rebuilds
local CSV/JSON/SQLite outputs.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "data/polymarket/auto_refresh.log"


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"{datetime.now(timezone.utc).replace(microsecond=0).isoformat()} {message}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run_once(fetch: bool) -> int:
    args = [sys.executable, "tools/polymarket/update_pipeline.py"]
    if fetch:
        args.append("--fetch")
    log(f"start {' '.join(args)}")
    completed = subprocess.run(args, cwd=ROOT)
    log(f"finish exit_code={completed.returncode}")
    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-minutes", type=float, default=60.0)
    parser.add_argument("--fetch", action="store_true", default=True)
    parser.add_argument("--no-fetch", action="store_false", dest="fetch")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    if args.interval_minutes <= 0:
        parser.error("--interval-minutes must be positive")

    while True:
        run_once(args.fetch)
        if args.once:
            return 0
        time.sleep(args.interval_minutes * 60)


if __name__ == "__main__":
    raise SystemExit(main())
