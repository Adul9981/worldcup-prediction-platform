# Rule Check: Market Opportunity Core

## Context

User explicitly required the platform to focus on existing prediction-market topics, classify topic structures, identify mutual exclusivity/non-exclusivity, and provide model-side betting direction when possible.

## Checked Rules

- R001 预测市场选题优先: passed.
- R002 选题类型必须分类: passed.
- R003 互斥关系必须进入风控: partially passed; current data marks `neg_risk_unknown`.
- R004 可以给下注方向，但必须有来源标记: passed.
- R005 当前阶段默认只读: passed.
- R006 网站第一屏要以市场机会为主线: passed.
- R007 后续明确要求必须入库: passed.
- R008 优化前后必须做规则对照: passed.

## Current Outputs

- `data/polymarket/latest_market_opportunities.csv`
- `data/polymarket/latest_market_opportunities_summary.md`
- SQLite table: `market_opportunities`

## Current Counts

- Total topics: 61.
- `multi_market_mutually_exclusive_group`: 60.
- `special_event_binary`: 1.
- `YES`: 11.
- `WAIT`: 38.
- `AVOID`: 12.

## Remaining Gap

Need capture official Polymarket `neg_risk` field or equivalent market metadata in future discovery snapshots. Until then, mutual-exclusion logic is inferred from `event_slug` and topic type, and `neg_risk_status` must remain `neg_risk_unknown`.
