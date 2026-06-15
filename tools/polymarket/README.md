# Polymarket Tools

All tools in this folder are read-only unless explicitly documented otherwise.

## Discover World Cup Markets

Fetch active Polymarket Gamma events, filter World Cup markets, and write CSV/JSON/Markdown snapshots.

```bash
python3 tools/polymarket/discover_worldcup_markets.py --pages 10 --limit 500
```

Outputs:

- `data/polymarket/latest_polymarket_worldcup_markets.csv`
- `data/polymarket/latest_polymarket_worldcup_summary.md`

## Import Markets To SQLite

Import the latest normalized CSV into the project database.

```bash
python3 tools/polymarket/import_markets_to_sqlite.py
```

Output:

- `data/worldcup_prediction.db`

Quick checks:

```bash
sqlite3 data/worldcup_prediction.db "SELECT COUNT(*) FROM polymarket_markets;"
sqlite3 data/worldcup_prediction.db "SELECT event_type, COUNT(*) FROM polymarket_markets GROUP BY event_type;"
```

## Map Champion Markets To Teams

Map Polymarket champion/outright markets to the local World Cup team and group metadata.

```bash
python3 tools/polymarket/map_champion_markets.py
```

Outputs:

- `data/polymarket/latest_champion_market_team_map.csv`
- `data/polymarket/latest_champion_market_team_map_summary.md`
- SQLite table: `polymarket_champion_team_map`

## Update Topic Status

Build the prediction market topic library and write status snapshots. This uses the latest snapshot for current counts and historical snapshots only for change detection.

```bash
python3 tools/polymarket/update_topic_status.py
```

Outputs:

- `data/polymarket/latest_prediction_market_topics.csv`
- `data/polymarket/latest_topic_status_summary.md`
- SQLite table: `prediction_market_topics`
- SQLite table: `market_status_snapshots`

Important status principle:

- Low trading volume does not mean low attention or low value.
- Only closed/resolved/settled markets should be treated as ended.

The current topic CSV and SQLite table include `affiliate_url`; website links should use that field instead of raw `url`.

## Affiliate Links

All Polymarket outbound links must include:

```text
?via=serene77mc-g6kj
```

Helper:

```python
from affiliate_links import with_polymarket_affiliate
```

Self-test:

```bash
python3 tools/polymarket/test_affiliate_links.py
```

## Score Topics

Score current topics with two tracks: conservative opportunities and upside observations.

```bash
python3 tools/polymarket/score_topics.py
```

Outputs:

- `data/polymarket/latest_market_event_scores.csv`
- `data/polymarket/latest_market_event_scores_summary.md`
- SQLite table: `market_event_scores`

## Calculate Stakes

Turn event scores into disciplined stake recommendations.

```bash
python3 tools/polymarket/calculate_stakes.py
```

Outputs:

- `data/polymarket/latest_staking_recommendations.csv`
- `data/polymarket/latest_staking_recommendations_summary.md`
- SQLite table: `staking_recommendations`

Important:

- Recommendations are not orders.
- Upside track stays small by default.
- Long-horizon champion markets are capped conservatively.

## Generate Daily Rankings

Generate the workbench three ranking lists: most watched, most ignored, and best risk-reward.

```bash
python3 tools/polymarket/generate_daily_rankings.py
```

Outputs:

- `data/polymarket/latest_daily_event_rankings.csv`
- `data/polymarket/latest_daily_event_rankings_summary.md`
- SQLite table: `daily_event_rankings`

Important:

- Most watched does not mean best to bet.
- Best risk-reward still obeys staking limits.
- Website links should use `affiliate_url`.

## Classify Market Opportunities

Classify market structures and generate read-only model-side directions.

```bash
python3 tools/polymarket/classify_market_opportunities.py
```

Outputs:

- `data/polymarket/latest_market_opportunities.csv`
- `data/polymarket/latest_market_opportunities_summary.md`
- SQLite table: `market_opportunities`

Important:

- Current World Cup winner markets are binary Yes/No markets inside a multi-market mutually exclusive event group.
- `neg_risk_status` is `neg_risk_unknown` until the official field is captured in the local snapshot.
- Direction labels are read-only: YES / NO / WAIT / AVOID.

## Safety Boundary

These tools do not use:

- API keys.
- Private keys.
- Wallets.
- Order placement.
- Bridge or gasless transaction APIs.
