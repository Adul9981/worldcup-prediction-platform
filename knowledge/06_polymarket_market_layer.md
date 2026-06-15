# Polymarket 市场接入层

更新时间：2026-06-10。

## 当前结论

已接入官方 `Polymarket/agent-skills` 作为主参考，并建立只读市场发现工具。

当前本地工具：

- `/Users/ad/Documents/2026世界杯/tools/polymarket/discover_worldcup_markets.py`

最新输出：

- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_polymarket_worldcup_markets.csv`
- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_polymarket_worldcup_summary.md`

## 最新发现结果

最近一次抓取结果：

- Polymarket 世界杯相关市场：61 个。
- 初步可参与市场：49 个。
- 类型分布：
  - `champion_or_outright`: 60
  - `special_event`: 1

这说明 Polymarket 当前更适合作为长周期事件市场，而不是单场比赛盘口库。

## 策略定位

Polymarket 在本项目里的优先用途：

1. 冠军 / outright 价格雷达。
2. 公众情绪和热门球队定价观察。
3. 长周期仓位和对冲。
4. 内容选题，例如“市场最看好的冠军队”和“被低估的黑马”。
5. 与我们自己的小组赛/淘汰赛模型进行概率差比较。

暂不把 Polymarket 当作主要单场下注市场，除非后续出现更多 World Cup match markets。

## 可参与事件类型

### 已发现

- 冠军队伍 Yes/No 市场。
- 世界杯美国赛程迁移特殊事件。

### 需要持续监控

- 小组出线。
- 小组第一。
- 单场胜负。
- 球员事件。
- 最佳射手。
- 淘汰赛晋级。
- 多腿组合事件。

## 使用方法

运行：

```bash
python3 tools/polymarket/discover_worldcup_markets.py --pages 10 --limit 500
```

输出后先看：

```text
data/polymarket/latest_polymarket_worldcup_summary.md
```

再看完整表：

```text
data/polymarket/latest_polymarket_worldcup_markets.csv
```

## 安全边界

当前只读：

- 不使用 API key。
- 不读取或存储私钥。
- 不下单。
- 不桥接。
- 不调用 gasless 交易。

后续如果启用交易，必须先完成：

- 纸上交易记录。
- 仓位上限。
- 订单模拟。
- 风险确认。
- 单独授权。

## 下一步

1. 把 Polymarket 市场与 `teams.csv` 里的球队强弱分层关联。
2. 给冠军市场计算我们自己的概率。
3. 输出“市场价格 vs 我方概率”的差值。
4. 生成冠军盘观察榜：
   - 最拥挤热门。
   - 最被低估黑马。
   - 赔率过低不值得碰。
   - 适合小仓高赔率博弈。

## 冠军盘球队映射

已建立本地映射工具：

```bash
python3 tools/polymarket/map_champion_markets.py
```

输出：

- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_champion_market_team_map.csv`
- `/Users/ad/Documents/2026世界杯/data/polymarket/latest_champion_market_team_map_summary.md`
- SQLite 表：`polymarket_champion_team_map`

当前映射结果：

- `mapped`: 48 个参赛队。
- `placeholder`: 9 个占位队。
- `other_bucket`: 1 个 Any Other Team。
- `unmapped_or_not_in_groups`: 2 个非当前 48 队条目。

决策规则：

- 只有 `mapped` 默认进入评分。
- `placeholder` 默认排除。
- `other_bucket` 只能人工分析。
- `unmapped_or_not_in_groups` 默认排除，除非有特殊理由。
