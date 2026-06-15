#!/usr/bin/env python3
"""Build a deployable static release package."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist/worldcup-prediction-platform"

SITE_FILES = [
    "admin.html",
    "events.html",
    "index.html",
    "markets.html",
    "progress.html",
    "today.html",
    "admin.js",
    "events.js",
    "app.js",
    "markets.js",
    "progress.js",
    "today.js",
    "styles.css",
    "favicon.svg",
]

API_FILES = [
    "api/recommendations.js",
]

DATA_FILES = [
    "data/templates/glossary_cn_en.csv",
    "data/templates/groups.csv",
    "data/templates/matches.csv",
    "data/templates/matches_summary.md",
    "data/templates/manual_recommendations.csv",
    "data/templates/manual_recommendations.json",
    "data/templates/teams.csv",
    "data/polymarket/latest_champion_market_team_map.csv",
    "data/polymarket/latest_daily_event_rankings.csv",
    "data/polymarket/latest_market_event_scores.csv",
    "data/polymarket/latest_market_opportunities.csv",
    "data/polymarket/latest_market_schedule_links.csv",
    "data/polymarket/latest_polymarket_worldcup_markets.csv",
    "data/polymarket/latest_prediction_market_topics.csv",
    "data/polymarket/latest_refresh_status.json",
    "data/polymarket/latest_topic_changes.csv",
    "data/polymarket/latest_topic_changes.json",
    "data/prediction_events/latest_prediction_event_library.csv",
    "data/prediction_events/latest_prediction_event_library.json",
    "data/prediction_events/latest_prediction_event_library_summary.md",
]


def copy_file(relative_path: str) -> None:
    source = ROOT / relative_path
    target = DIST / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def write_release_readme() -> None:
    status = (ROOT / "data/polymarket/latest_refresh_status.json").read_text(encoding="utf-8").strip()
    readme = f"""# 世界杯预测市场平台发布包

生成时间：{datetime.now(timezone.utc).replace(microsecond=0).isoformat()}

## 入口

- `/site/index.html`
- `/site/today.html`
- `/site/admin.html`
- `/site/events.html`
- `/site/markets.html`
- `/site/progress.html`

## 部署方式

把本目录内容作为静态站点根目录发布。必须保留 `/site/` 和 `/data/` 两个目录，因为页面会从 `/data/...` 读取 CSV/JSON。

本地预览：

```bash
python3 -m http.server 4173
```

然后打开：

```text
http://127.0.0.1:4173/site/index.html
```

## 安全边界

- 只读展示。
- 不连接钱包。
- 不下单。
- 不读取或保存私钥。
- 所有 Polymarket 跳转链接带邀请码。
- 用户可见层不输出仓位、下注金额或下注单位。

## 当前刷新状态

```json
{status}
```
"""
    (DIST / "README_PUBLISH.md").write_text(readme, encoding="utf-8")


def write_root_index() -> None:
    index = """<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta http-equiv="refresh" content="0; url=/site/today.html" />
    <title>世界杯预测市场</title>
    <link rel="icon" href="/site/favicon.svg" type="image/svg+xml" />
    <link rel="canonical" href="/site/today.html" />
  </head>
  <body>
    <script>window.location.replace('/site/today.html');</script>
    <a href="/site/today.html">进入世界杯预测市场</a>
  </body>
</html>
"""
    (DIST / "index.html").write_text(index, encoding="utf-8")


def main() -> int:
    if DIST.exists():
        shutil.rmtree(DIST)
    for filename in SITE_FILES:
        copy_file(f"site/{filename}")
    for filename in API_FILES:
        copy_file(filename)
    for filename in DATA_FILES:
        copy_file(filename)
    write_root_index()
    write_release_readme()
    print(f"Wrote release package: {DIST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
