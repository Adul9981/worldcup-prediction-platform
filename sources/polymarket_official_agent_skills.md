# Polymarket Official Agent Skills

Status: downloaded locally on 2026-06-10.

Local path:

- `/Users/ad/Documents/2026世界杯/integrations/agent-skills`

Remote:

- https://github.com/Polymarket/agent-skills

Verified HEAD:

- `91ee44ae113e958affd20cd505c6e9d9d6100e0b`

## Decision

Use `Polymarket/agent-skills` as the primary Polymarket integration reference.

Community repositories remain optional references only. The current project should not depend on community skills unless we later find a specific missing feature in the official repository.

## What The Official Skill Covers

The official skill is intended for AI agents and includes:

- Authentication.
- Order placement and cancellation.
- Market data.
- Real-time WebSocket data.
- Position management.
- Conditional token operations.
- Bridge flows.
- Gasless transactions.

## What We Use First

First phase is read-only:

- Gamma API events and markets.
- CLOB orderbook reads.
- Price, midpoint, spread, and last trade price.
- WebSocket market data only if needed later.
- World Cup event discovery and normalization.
- Paper-trade candidates and risk scoring.

## What We Do Not Use Yet

Blocked until explicit user approval:

- API credentials.
- Private keys.
- Wallet setup.
- Real order placement.
- Bridge.
- Gasless transactions.
- Automated trading.

## Relevant Official Files

- `README.md`: overview, installation, SDKs, endpoint list.
- `SKILL.md`: quick reference and core integration patterns.
- `market-data.md`: Gamma API, Data API, CLOB orderbook, price history, pagination.
- `websocket.md`: real-time streams.
- `authentication.md`: credentials and signing, not needed for read-only phase.
- `order-patterns.md`: order behavior, not needed until live or paper-trade simulation.

## Read-Only API Endpoints From Official Skill

- Gamma API: `https://gamma-api.polymarket.com`
- CLOB read API: `https://clob.polymarket.com`
- Data API: `https://data-api.polymarket.com`
- Market WebSocket: `wss://ws-subscriptions-clob.polymarket.com/ws/market`
- Sports WebSocket: `wss://sports-api.polymarket.com/ws`

## Implementation Note

The first tool to build should be `polymarket_market_discovery`:

1. Fetch active Polymarket events.
2. Search / filter World Cup related events.
3. Normalize event and market fields.
4. Count currently actionable prediction events.
5. Classify them into event types:
   - champion / outright
   - group qualification
   - single match winner
   - match props
   - player props
   - multi-leg / parlay
   - unclear / low quality
6. Save snapshots for daily review.
