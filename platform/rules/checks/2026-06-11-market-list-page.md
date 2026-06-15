# Rule Check: Market List Page

## Scope

Added `site/markets.html` and `site/markets.js` to show all current prediction-market opportunities.

## Checked Rules

- R001 预测市场选题优先: passed.
- R002 选题类型必须分类: passed.
- R003 互斥关系必须进入风控: passed with `neg_risk_unknown` label retained.
- R004 可以给下注方向，但必须有来源标记: passed through opportunity data.
- R005 当前阶段默认只读: passed.
- R006 网站第一屏要以市场机会为主线: not first screen, but the page itself is market-first.
- R009 Polymarket 链接必须带邀请码: passed.
- R010 用户可见标题永远中文: passed.
- R011 必须维护中英文对照知识库: passed.

## Verification

- Page title: `预测市场机会列表`.
- Total rows: 61.
- YES rows: 11.
- Links missing `via=serene77mc-g6kj`: 0.
- Direction filter works.
- Chinese search works: `德国` returns Germany market.
