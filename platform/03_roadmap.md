# 建设路线图

## Phase 0：规划与边界

状态：进行中。

目标：

- 建立平台章程。
- 建立网站原则标准。
- 建立待办库。
- 建立优化库。
- 明确 Polymarket 官方接入优先。

验收：

- `platform/00_platform_charter.md`
- `platform/01_product_plan.md`
- `platform/02_website_principles.md`
- `platform/todos/backlog.md`
- `platform/optimization/optimization_log.md`

## Phase 1：数据发现层

目标：

- Polymarket 只读市场发现稳定运行。
- 输出最新市场 CSV/JSON/Markdown。
- 避免脏数据误抓。
- 建立事件分类。

已完成：

- `tools/polymarket/discover_worldcup_markets.py`
- `data/polymarket/latest_polymarket_worldcup_markets.csv`
- `data/polymarket/latest_polymarket_worldcup_summary.md`

待完成：

- 入库 SQLite。已完成基础导入脚本。
- 市场快照历史对比，用于新增/消失和状态变化。
- 冠军市场球队映射。
- 价格变化榜。低优先级，后续需要时再做。

## Phase 2：机会评分与热度层

目标：

- 建立事件评分器。
- 建立交易量、流动性、热度和回报率解释层。
- 建立明显强队、鱼腩/弱队、摇摆队、高回报观察、过热风险、互斥组异常标签。
- 输出今日三榜。

产物：

- `tools/scoring/event_score_model.py`
- `data/outputs/daily_rankings.csv`

验收：

- 每个事件都有关注度、忽视度、盈亏比、风险分。
- 每个可参与事件都有方向、机会标签、分析理由和取消条件。
- 用户可见层不输出仓位、下注金额或下注单位。

## Phase 3：每日工作流自动化

目标：

- 自动生成每日机会工作台数据。
- 对接赛事列表。
- 追踪新增选题、消失选题、关闭/结算和已结束选题。

产物：

- `tools/daily/daily_brief_generator.py`
- `daily/YYYY-MM-DD.md`

验收：

- 每天一条命令生成今日工作台。
- 今日工作台优先展示：新增/消失选题、最值得关注、最被忽视、高回报观察、买入方向、回避事件、赛程阶段。

## Phase 4：本地网页工作台

目标：

- 构建可用的本地网页。
- 展示市场、赛事、方向分析、热度、复盘、文案。

原则：

- 第一屏就是今日工作台。
- 不做营销页。
- 不接真实交易。

验收：

- 本地可访问。
- 表格和榜单清晰。
- 移动端不重叠。
- 数据更新时间可见。

当前状态（2026-06-14）：

- 今日页、预测事件库、进度纵览已形成三页主线。
- 今日页只保留今日推荐和今日比赛；今日推荐由独立后台维护。
- 前台已加入 Polymarket 注册链接、邀请码、作者 Twitter、作者 Telegram。
- 页面已加入克制的世界杯/足球视觉元素和 favicon。
- Vercel 生产部署已完成，根路径自动进入今日页。
- 今日推荐后台已从浏览器本地草稿逻辑升级为 `/api/recommendations` 线上 API 逻辑。
- 线上 API 已部署，管理口令环境变量已配置。
- 剩余激活条件：Vercel 项目需要连接 KV/Upstash Redis 存储，生成 `KV_REST_API_URL` 和 `KV_REST_API_TOKEN` 后，后台保存内容即可跨浏览器、跨设备共享。

下一步：

- 在 Vercel 项目连接 KV 存储。
- 重新部署生产环境。
- 用后台保存一条今日推荐，验证另一浏览器或无痕窗口能在前台看到同一内容。

## Phase 5：内容系统

目标：

- 每日生成可分享推文。
- 输出赛前、临场、赛后复盘。

验收：

- 每条内容都能追溯到事件和复盘。
- 不出现收益承诺。

## Phase 6：纸上交易与复盘曲线

目标：

- 记录模拟买入/卖出。
- 计算纸上收益。
- 评估策略稳定性。

验收：

- 至少 7 天纸上交易记录。
- 明确哪些策略有效。

## Phase 7：是否启用真实交易评估

只有当前面阶段通过后才讨论。

必须完成：

- 风险审查。
- 私钥方案。
- 订单模拟。
- 人工确认流程。
- 单独授权。
