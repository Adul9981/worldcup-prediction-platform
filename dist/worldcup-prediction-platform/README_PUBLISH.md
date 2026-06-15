# 世界杯预测市场平台发布包

生成时间：2026-06-14T05:57:18+00:00

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
{
  "updated_at": "2026-06-12T13:09:17+00:00",
  "status": "ok",
  "fetched_from_polymarket": false,
  "source_snapshot_at": "2026-06-11T09:21:27+00:00",
  "market_rows": 61,
  "topic_rows": 61,
  "opportunity_rows": 61,
  "match_rows": 104,
  "schedule_link_rows": 61,
  "daily_ranking_rows": 15,
  "error": ""
}
```
