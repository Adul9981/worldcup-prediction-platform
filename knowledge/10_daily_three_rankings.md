# 今日三榜

## 目标

今日三榜是网站工作台第一屏的核心信息层。

它回答三个问题：

1. 哪些事件今天最值得看。
2. 哪些事件可能被市场或大众忽视。
3. 哪些事件当前盈亏比最好。

三榜不是下单指令。它们是决策入口，必须和仓位建议、取消条件、复盘字段一起展示。

## 三个榜单

### 最值得关注

字段值：`most_watched`

排序核心：

- `attention_score`
- `conservative_score`
- `volume_24hr`

含义：

这类事件是市场温度计，适合用来判断共识、价格锚点和传播热点。它可以没有下注仓位。

### 最被忽视

字段值：`most_ignored`

排序核心：

- `ignored_score`
- `risk_reward_score`
- 较低风险优先

含义：

这类事件可能不是最大热门，但可能存在信息差、传播滞后或定价没有充分反映的机会。

### 最大盈亏比

字段值：`best_risk_reward`

排序核心：

- `risk_reward_score`
- `recommended_stake_units`
- 较低风险优先

含义：

这类事件更接近交易决策层，但仍然必须经过仓位系统约束。高盈亏比不等于重仓。

## 当前输出

- `data/polymarket/latest_daily_event_rankings.csv`
- `data/polymarket/latest_daily_event_rankings_summary.md`
- SQLite 表：`daily_event_rankings`

## 网站展示原则

每条榜单事件至少展示：

- 榜单类型和排名。
- 事件标题。
- 当前状态。
- 关注度、忽视度、盈亏比、风险。
- 建议动作。
- 建议仓位。
- 取消条件。
- Polymarket 跳转链接。

所有 Polymarket 外链必须使用 `affiliate_url`。

## 重要解释

`最值得关注` 不等于 `最值得下注`。

一个事件可能交易量高、关注度高，但赔率已经不划算，因此只适合观察。另一个事件可能交易量暂时不高，但刚上线、离比赛时间远、或市场还没扩散，仍然应该留在观察池。

只有市场关闭、结算、规则失效或事件确定结束，才应从活跃决策层移除。
