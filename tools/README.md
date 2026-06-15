# 工具建设库

## 近期要建的工具

### 0. polymarket_market_discovery

优先级最高。先只接 Polymarket，用来发现当前世界杯相关预测事件。

官方本地参考：

- `/Users/ad/Documents/2026世界杯/integrations/agent-skills`
- `/Users/ad/Documents/2026世界杯/integrations/py-clob-client`

本地工具：

- `/Users/ad/Documents/2026世界杯/tools/polymarket/discover_worldcup_markets.py`

运行：

```bash
python3 tools/polymarket/discover_worldcup_markets.py
```

输出：

- `data/polymarket/latest_polymarket_worldcup_markets.csv`
- `data/polymarket/polymarket_worldcup_markets_<timestamp>.csv`
- `data/polymarket/polymarket_worldcup_markets_<timestamp>.json`

输入：

- Polymarket Gamma API events / markets。
- 关键词：`World Cup`, `FIFA`, `Mexico`, `Brazil`, `Argentina`, `England`, `France`, `Portugal`, `Germany`, `Spain` 等。
- 本地比赛表 `data/templates/matches.csv`。

输出：

- 当前可参与的世界杯相关预测事件数量。
- 每个事件的平台、标题、slug、成交量、流动性、价格、截止时间。
- 事件分类：冠军、小组出线、单场胜负、组合串关、球员事件、特殊事件。
- 是否可参与：active / closed / low-liquidity / unclear-resolution。

第一阶段只读，不做下单。

### 0.1 polymarket_sqlite_import

把 Polymarket 最新 CSV 快照导入本地 SQLite。

本地工具：

- `/Users/ad/Documents/2026世界杯/tools/polymarket/import_markets_to_sqlite.py`

运行：

```bash
python3 tools/polymarket/import_markets_to_sqlite.py
```

输出：

- `data/worldcup_prediction.db`

导入表：

- `polymarket_markets`

### 0.2 polymarket_champion_team_map

把冠军盘市场映射到本地球队与小组分层。

本地工具：

- `/Users/ad/Documents/2026世界杯/tools/polymarket/map_champion_markets.py`

运行：

```bash
python3 tools/polymarket/map_champion_markets.py
```

输出：

- `data/polymarket/latest_champion_market_team_map.csv`
- SQLite 表：`polymarket_champion_team_map`

其他平台先保留接口位：

- Kalshi adapter placeholder。
- Manifold adapter placeholder。
- Sportsbook odds adapter placeholder。

### 1. daily_brief_generator

输入：

- `data/templates/matches.csv`
- `data/templates/groups.csv`
- `data/templates/teams.csv`
- `ledger/bet_ledger.csv`

输出：

- `daily/YYYY-MM-DD.md`
- 今日 Top 3 关注事件。
- 今日 Top 3 被忽视事件。
- 今日 Top 3 盈亏比事件。

### 2. staking_calculator

输入：

- bankroll_units
- event_score
- confidence
- risk_level
- correlated_exposure
- daily_profit_loss

输出：

- recommended_stake_units
- max_allowed_stake_units
- no-bet warning

### 3. event_score_model

输入：

- motivation_score
- team_gap_score
- lineup_confidence
- market_heat
- ignored_value
- price_edge
- risk_level

输出：

- importance_score
- ignored_score
- risk_reward_score
- final_action

### 4. content_post_generator

输入：

- 今日最值得关注。
- 今日最被忽视。
- 今日最大盈亏比。
- 昨日复盘。

输出：

- 赛前推文。
- 首发更新。
- 临场机会。
- 赛后复盘。

## 建设原则

- 先人工可用，再自动化。
- 所有自动建议必须保留取消条件。
- 所有下注建议必须写入账本。
- 所有内容输出必须和下注记录分离。
