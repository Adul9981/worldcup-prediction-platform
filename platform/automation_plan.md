# 定期更新计划

## 目标

定期刷新预测市场选题库，确认当前到底有多少世界杯相关预测市场选题，并跟踪每个事件的状态变化。

## 默认频率

常规阶段：

- 每天 09:00 刷新一次。
- 每天 21:00 刷新一次。

比赛日：

- 早盘。
- 首发前后。
- 比赛后。
- 当日复盘前。

## 每次更新要执行

```bash
python3 tools/polymarket/update_pipeline.py --fetch
```

本地重建、不联网刷新时：

```bash
python3 tools/polymarket/update_pipeline.py
```

前台自动循环刷新：

```bash
python3 tools/polymarket/auto_refresh_loop.py --interval-minutes 60 --fetch
```

macOS 后台发布配置：

- LaunchAgent 模板：`platform/automation/com.serene.worldcup.polymarket-refresh.plist`
- 默认频率：每 60 分钟联网刷新一次。
- 日志：`data/polymarket/auto_refresh.log`、`data/polymarket/launchagent.out.log`、`data/polymarket/launchagent.err.log`

## 每次更新要输出

- 当前世界杯相关市场数量。
- 当前可参与市场数量。
- 按类型统计。
- 新发现市场。
- 消失市场。
- closed / resolved 市场。
- 低交易量但值得观察的市场。
- 成交量增长明显的市场。
- 流动性变化明显的市场。
- 价格变化明显的市场。
- 今日三榜：最值得关注、最被忽视、最大盈亏比。
- 当前预测选题结构分类和模型下注方向。
- 完整赛程槽位数量。

## 关键原则

- 低交易量不等于低关注。
- 低交易量不等于低价值。
- 新上架低交易量事件进入观察池。
- 只有市场关闭、结算、规则判定结束，才标记为结束。
- 当前数量按最新快照去重。
- 历史快照用于趋势分析，不能直接累加为当前数量。

## 禁止事项

- 不使用 API key。
- 不读取或保存私钥。
- 不连接钱包。
- 不下单。
- 不桥接。
- 不调用 gasless 交易。
