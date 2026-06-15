# 规则检查：自动刷新和完整赛程

检查时间：2026-06-11

## 对照规则

- R013：用户可见层不输出仓位建议。
- R014：展示价格时必须展示回报率。
- R015：优先执行数据自动刷新、状态检测、机会评分、赛程映射和每日工作台。

## 本次建设

- 新增 `tools/schedule/build_worldcup_schedule.py`，生成 104 场世界杯赛事槽位。
- `tools/polymarket/update_pipeline.py` 已纳入赛程生成，并在刷新状态中输出 `match_rows`。
- 新增 `tools/polymarket/auto_refresh_loop.py`，支持前台自动循环刷新。
- 新增 macOS LaunchAgent 模板 `platform/automation/com.serene.worldcup.polymarket-refresh.plist`。
- 进度纵览页展示刷新状态、阶段进度、后续赛程和阶段统计。

## 验证结果

- `python3 tools/schedule/build_worldcup_schedule.py` 通过，生成 104 场。
- `python3 tools/polymarket/update_pipeline.py` 通过。
- `python3 tools/polymarket/auto_refresh_loop.py --once --no-fetch` 通过。
- `node --check site/progress.js` 通过。
- `node --check site/markets.js` 通过。
