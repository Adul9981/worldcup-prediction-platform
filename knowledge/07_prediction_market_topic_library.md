# 预测市场选题库

更新时间：2026-06-10。

## 为什么需要选题库

世界杯预测市场不是一次性列完的。

很多事件会随着赛程推进不断出现：

- 冠军。
- 小组出线。
- 小组第一。
- 单场胜负。
- 晋级下一轮。
- 最佳射手。
- 球员事件。
- 比赛迁移、规则、场地等特殊事件。
- 多腿组合事件。

所以平台必须统计“当前预测市场到底提供了多少相关选题”，并持续更新每个事件的状态。

## 当前 Polymarket 统计

最新快照：

- 世界杯相关市场：61 个。
- 初步可参与市场：49 个。
- 类型分布：
  - `champion_or_outright`: 60
  - `special_event`: 1

冠军盘映射：

- 当前 48 支参赛队：48 个。
- 占位队：9 个。
- Any Other Team：1 个。
- 非当前 48 队：2 个。

## 关键原则

低交易量不等于低关注，也不等于低价值。

可能原因：

- 事件刚上架。
- 比赛窗口还没到。
- 传播还没开始。
- 相关球队还没踢关键比赛。
- 市场还没形成流动性。

因此：

- 低交易量事件进入观察池。
- 不因为交易量小直接排除。
- 只有事件关闭、结算、规则判定结束，才标记为结束。
- 交易量增长本身是一个信号，需要被跟踪。

## 选题状态定义

### discovered

刚发现，尚未分类完成。

### watchlist

值得观察，但暂不参与。常见原因：

- 交易量小。
- 流动性不足。
- 时间窗口未到。
- 信息不足。

### active

可参与候选。要求：

- 市场 open。
- 规则清晰。
- 价格可解释。
- 有基本流动性。

### hot

交易量或价格变化明显，适合进入今日重点。

### low_liquidity

流动性不足，但不能直接排除。继续观察是否增长。

### stale

长时间没有价格或成交变化，需要降权。

### closed

市场已关闭，但可能未结算。

### resolved

结果已结算或事件已判定。

### excluded

不进入评分。常见原因：

- 占位队伍。
- 非当前 48 队。
- 规则不清。
- 误抓。
- 与世界杯无关。

## 统计口径

### 当前选题数量

只使用最新快照，按 `market_id` 或等价唯一标识去重。

### 历史选题数量

使用所有快照，但需要按市场唯一 ID 聚合，不能把每次快照重复计入新市场。

### 状态变化

比较相邻快照：

- 新增市场。
- 消失市场。
- open -> closed。
- closed -> resolved。
- 价格变化。
- 交易量增长。
- 流动性变化。

### 活跃度

活跃度不是价值本身，只是当前市场参与程度。

需要区分：

- 低活跃但早期。
- 低活跃且长期停滞。
- 高活跃但价格过热。
- 高活跃且信息充分。

## 定期更新规则

### 常规阶段

每天至少刷新 2 次：

- 早上：建立今日观察池。
- 晚上：记录市场变化和内容复盘。

### 比赛日

建议刷新 4 次：

- 赛前早盘。
- 首发前后。
- 比赛结束后。
- 当日复盘前。

### 淘汰赛阶段

建议提高频率：

- 每 3-6 小时检查一次。
- 大事件后立即刷新，例如强队出局、核心球员伤停、晋级路径改变。

## 输出产物

当前已有：

- `data/polymarket/latest_polymarket_worldcup_markets.csv`
- `data/polymarket/latest_polymarket_worldcup_summary.md`
- `data/polymarket/latest_champion_market_team_map.csv`
- `data/polymarket/latest_champion_market_team_map_summary.md`
- SQLite: `polymarket_markets`
- SQLite: `polymarket_champion_team_map`

下一步需要：

- `prediction_market_topics` 表。已建立。
- `market_status_snapshots` 表。已建立。
- 状态更新脚本。已建立。
- 新增/消失/热度增长报告。

## 决策规则

- 新上架低交易量：进入 watchlist。
- 高交易量低流动性：谨慎，检查是否异常。
- 高流动性高热度：进入重点观察，但防止拥挤交易。
- 已关闭未结算：不新增仓位，只复盘。
- 已结算：转入历史，不再参与。
- 占位或非当前参赛队：排除评分，但保留原始记录。

## 当前状态更新工具

运行：

```bash
python3 tools/polymarket/update_topic_status.py
```

输出：

- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_prediction_market_topics.csv`
- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_topic_status_summary.md`
- SQLite 表：`prediction_market_topics`
- SQLite 表：`market_status_snapshots`

当前状态统计：

- 当前选题数量：61。
- `hot`: 38。
- `active`: 11。
- `excluded`: 11。
- `watchlist`: 1。

说明：

- `hot` 只表示当前交易活跃，不等于推荐下注。
- `watchlist` 可能是低交易量、早期、特殊或需要人工判断的事件。
- `excluded` 保留原始记录，但不进入评分和仓位建议。
