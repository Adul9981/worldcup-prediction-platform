# Polymarket Codex Integration Notes

Saved from user-provided research on 2026-06-10.

## Scope Decision

Current implementation priority:

1. Polymarket first.
2. Official Polymarket repository first: `Polymarket/agent-skills`.
3. Community repositories remain optional references only.
4. Other prediction markets stay as future interface placeholders only.
5. No live trading integration until data discovery, paper tracking, and risk controls are stable.

## Official Update

The preferred official repository is now:

- https://github.com/Polymarket/agent-skills

Local downloaded path:

- `/Users/ad/Documents/2026世界杯/integrations/agent-skills`

Verified HEAD:

- `91ee44ae113e958affd20cd505c6e9d9d6100e0b`

This supersedes the earlier community-first recommendation below. Keep the community list as backup/reference only.

## User-Provided Notes

是的，有对应的 GitHub 仓库。

“Codex” 这里指的是 OpenAI 的 Codex AI 编码代理工具（2026 年初推出的类似 Claude Code 的 AI 编码/Agent 工具），很多开发者在用它来构建 Polymarket 交易机器人、获取市场数据、执行技能等。Polymarket 本身没有官方的 “Codex 专用接入” 仓库，但社区已经出了好几个 Codex 兼容的 Skills / Agent 集成仓库，可以直接让 Codex 接入 Polymarket（支持下单、查市场、交易技能等）。

## Recommended GitHub Repositories

### 1. mjunaidca/polymarket-skills

- Most recommended in the provided notes.
- Built for Polymarket Composable Agent Skills.
- Explicitly supports Codex, Claude Code, Cursor, and similar coding agents.
- Includes paper-trading-first and safety-audited skills.
- Can be placed under `~/.codex/skills/`.
- GitHub: https://github.com/mjunaidca/polymarket-skills

### 2. chainstacklabs/polymarket-alpha-bot

- Polymarket alpha discovery and position management bot.
- Mentions installing skills into Codex CLI under `~/.codex/skills/`.
- Supports Codex, Cursor, and similar agents.
- GitHub: https://github.com/chainstacklabs/polymarket-alpha-bot

### 3. celer-network/x402-polymarket-agentpay-buyer

- Buyer-side access for paid Polymarket data through Codex / Claude Code agents.
- Includes one-click installer with a `--codex` parameter.
- GitHub: https://github.com/celer-network/x402-polymarket-agentpay-buyer

### 4. Other Related Repositories

- Trading-codex organization: `polymarket-arbitrage-trading-bot`.
- Polymarket official SDKs can be used with Codex, but are not Codex-specific.
- Polymarket GitHub organization: https://github.com/Polymarket

## Expected Fast-Start Path

1. Use official `Polymarket/agent-skills` first.
2. Use `Polymarket/py-clob-client` as the Python SDK reference when needed.
3. Only install skills globally after a separate explicit approval.
4. Keep initial implementation read-only:
   - search markets
   - fetch events
   - normalize markets
   - track prices
   - rank World Cup prediction events
   - record paper-trade candidates

## Safety Boundary

Do not implement live order execution in the first phase.

Allowed first phase:

- Market discovery.
- Event normalization.
- Odds / probability capture.
- Paper-trade tracking.
- Risk scoring.
- Content and recap generation.

Blocked until explicit user approval:

- API key storage.
- Wallet/private key handling.
- Real order placement.
- Automated trading.
- Any fund transfer or settlement workflow.
