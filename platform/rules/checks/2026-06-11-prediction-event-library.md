# 规则检查：预测事件库

检查时间：2026-06-11

## 用户要求

- 平台核心要回答“目前有哪些预测市场下注机会”。
- 建立预测事件库。
- 事件库要明确策略建议和结构情况。
- 不只包含单场比赛结果，还要包含八强、射手王、16强、半决赛、决赛等复杂事件。

## 本次建设

- 新增生成脚本 `tools/events/build_prediction_event_library.py`。
- 新增数据目录 `data/prediction_events/`。
- 新增核心数据：
  - `latest_prediction_event_library.csv`
  - `latest_prediction_event_library.json`
  - `latest_prediction_event_library_summary.md`
- 新增页面 `site/events.html` 和 `site/events.js`。
- 刷新流水线已接入事件库生成。
- 发布包已包含预测事件库。

## 当前事件库内容

- 事件总数：282。
- 当前已上架 Polymarket 市场：61。
- 待上架/待发现监控事件：221。
- 当前买 YES 方向：11。
- 覆盖类型包括：冠军盘、单场赛果、单场总进球、小组第一、小组出线、小组出局、32强晋级、16强晋级、八强晋级、半决赛晋级、决赛胜者、射手王、球员奖项、决赛对阵、大洲表现、特殊事件。

## 验证结果

- `python3 tools/events/build_prediction_event_library.py` 通过。
- `node --check site/events.js` 通过。
- 浏览器验证：预测事件库页面显示 282 个事件，已上架 61 个，待监控 221 个。
- 浏览器验证：页面包含单场赛果、小组出线、八强/进入八强、射手王。
- 浏览器验证：无数据加载失败，无用户禁止的资金类字段，Polymarket 外链邀请码缺失数为 0。
