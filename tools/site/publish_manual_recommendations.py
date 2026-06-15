#!/usr/bin/env python3
"""Validate and publish manual recommendations JSON into the site data folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "data/templates/manual_recommendations.json"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 tools/site/publish_manual_recommendations.py path/to/manual_recommendations.json")
        return 2
    source = Path(sys.argv[1])
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("Manual recommendations must be a JSON array.")
        return 2
    cleaned = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            print(f"Item {index} is not an object.")
            return 2
        title = str(item.get("title") or "").strip()
        analysis = str(item.get("analysis") or "").strip()
        if not title and not analysis:
            continue
        cleaned.append(
            {
                "id": str(item.get("id") or f"manual-{index}"),
                "date": str(item.get("date") or ""),
                "title": title or analysis.splitlines()[0],
                "direction": str(item.get("direction") or "重点推荐"),
                "analysis": analysis,
                "url": str(item.get("url") or ""),
                "status": str(item.get("status") or "active"),
            }
        )
    TARGET.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(ROOT)} ({len(cleaned)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
