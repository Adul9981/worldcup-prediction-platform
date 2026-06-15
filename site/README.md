# 网站 MVP

本目录是世界杯预测市场工作台的第一版只读网站。

## 运行

在项目根目录运行：

```bash
python3 -m http.server 4173
```

打开：

```text
http://127.0.0.1:4173/site/index.html
```

## 当前功能

- 今日三榜：最值得关注、最被忽视、最大盈亏比。
- 预测市场机会卡片。
- 选题结构分类。
- 模型下注方向：YES / WAIT / AVOID。
- 世界杯赛事阶段。
- 近期赛程。
- 高关注小组。
- 世界杯进度纵览页面。
- 全部市场机会列表页。
- 用户可见标题中文化。
- 中英文术语表转换。
- 当前市场选题数量。
- 方向分布。
- 市场状态分布。
- 榜单筛选。
- 关键词搜索。
- Polymarket 联盟链接跳转。

## 边界

- 只读。
- 不登录。
- 不连接钱包。
- 不下单。
- 不保存私钥。
- 不做订阅付费墙。

## 数据来源

页面直接读取本地 CSV：

- `data/polymarket/latest_daily_event_rankings.csv`
- `data/polymarket/latest_prediction_market_topics.csv`
- `data/polymarket/latest_market_opportunities.csv`
- `data/templates/glossary_cn_en.csv`
