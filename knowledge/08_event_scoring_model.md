# 事件评分模型

更新时间：2026-06-10。

## 目标

事件评分模型不是直接下单模型，而是把预测市场选题拆成两个观察轨道：

1. 稳健机会。
2. 高盈亏比观察。

后续仓位系统会再决定是否下注、下注多少、是否只观察。

## 当前工具

运行：

```bash
python3 tools/polymarket/score_topics.py
```

输出：

- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_market_event_scores.csv`
- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_market_event_scores_summary.md`
- SQLite 表：`market_event_scores`

## 当前评分结果

最新结果：

- 总评分选题：61。
- `conservative`: 7。
- `upside`: 29。
- `neutral`: 13。
- `excluded`: 11。
- `watchlist`: 1。

## 双轨定义

### 稳健机会

特征：

- 球队强度高。
- 市场流动性和成交活跃。
- 风险分可接受。
- 价格没有极端偏低导致纯彩票化。

当前代表：

- Argentina。
- Brazil。
- Germany。
- Portugal。
- England。
- France。
- Spain。

### 高盈亏比观察

特征：

- 价格较低。
- 不是纯占位或无效市场。
- 有球队实力、路径、主场、黑马、信息差等支撑。
- 可以进入观察池，但不能自动下注。

当前代表：

- Switzerland。
- USA。
- Belgium。
- Mexico。
- Uruguay。
- Morocco。
- Japan。
- Colombia。
- Norway。
- Netherlands。

## 重要原则

- `hot` 只表示交易活跃，不等于推荐下注。
- `upside` 只表示有高盈亏比观察价值，不等于重仓。
- 低交易量不等于低关注，也不等于低价值。
- `excluded` 保留原始记录，但不进入评分和仓位建议。
- 评分模型是启发式，必须通过复盘数据持续校准。

## 当前输入

- 预测市场选题状态。
- Polymarket 价格。
- 24 小时成交量。
- 流动性。
- 球队分层。
- 小组信息。
- 占位/非参赛队过滤结果。

## 当前输出字段

- `conservative_score`
- `upside_score`
- `attention_score`
- `ignored_score`
- `risk_reward_score`
- `risk_score`
- `recommendation_track`
- `action_label`
- `rationale`
- `affiliate_url`

## 后续优化

- 加入我方概率。
- 加入小组路径难度。
- 加入赛程阶段。
- 加入价格变化趋势。
- 加入成交量增长速度。
- 加入复盘后的校准权重。
