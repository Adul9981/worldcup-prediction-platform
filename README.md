# 2026 World Cup Prediction Ops

This workspace is a daily operating library for World Cup match prediction, event tracking, staking discipline, and post-match review.

Core idea: build a "match event radar" instead of only predicting champion / finalists. Every match can expose different opportunities: pre-match markets, in-play triggers, team motivation, qualification math, rotation, cards, set pieces, weather, venue, and market movement.

## Workspace Map

- `docs/00_project_brief.md` - project objective, operating principles, and deliverables.
- `docs/01_prediction_event_radar.md` - what events are worth predicting or tracking.
- `docs/02_daily_workflow.md` - daily routine before, during, and after matches.
- `docs/03_staking_strategy.md` - unit sizing, add/reduce rules, and risk guardrails.
- `docs/04_presentation_design.md` - how the project should be presented visually.
- `knowledge/01_idea_bank.md` - idea bank and missing angles to keep expanding.
- `knowledge/02_team_group_radar.md` - team strength tiers, weak-team radar, swing teams, group attention map.
- `knowledge/03_strategy_playbook.md` - actionable betting/prediction strategies derived from the radar.
- `knowledge/04_content_copy_system.md` - daily recap and social post copy system.
- `knowledge/05_platform_blueprint.md` - prediction platform product modules.
- `knowledge/06_polymarket_market_layer.md` - Polymarket read-only market discovery and strategy role.
- `knowledge/07_prediction_market_topic_library.md` - prediction market topic library and status update rules.
- `knowledge/08_event_scoring_model.md` - dual-track event scoring model.
- `knowledge/09_staking_calculator.md` - unit-based staking recommendation rules.
- `knowledge/10_daily_three_rankings.md` - workbench rankings for most watched, most ignored, and best risk-reward events.
- `knowledge/11_cn_en_glossary.md` - Chinese-English terminology glossary for user-facing display.
- `platform/00_platform_charter.md` - platform principles, scope, and decision rules.
- `platform/01_product_plan.md` - product plan and MVP scope.
- `platform/02_website_principles.md` - non-negotiable website and product standards.
- `platform/03_roadmap.md` - phased build roadmap.
- `platform/rules/system_rules.md` - non-negotiable system-building rules from explicit user requirements.
- `platform/todos/backlog.md` - todo library.
- `platform/optimization/optimization_log.md` - optimization and issue log.
- `site/index.html` - first read-only local website MVP.
- `site/markets.html` - full prediction-market opportunity list.
- `site/progress.html` - World Cup progress overview.
- `data/templates/matches.csv` - match-level data template.
- `data/templates/teams.csv` - team-level classification template.
- `data/templates/groups.csv` - group-level attention and opportunity template.
- `data/templates/event_markets.csv` - event/market tracking template.
- `data/templates/daily_event_rankings.csv` - daily most important / most ignored / best risk-reward events.
- `data/templates/content_posts.csv` - daily content production tracker.
- `ledger/bet_ledger.csv` - staking and result ledger.
- `models/schema.sql` - database schema for a future SQLite project database.
- `data/worldcup_prediction.db` - local SQLite database generated from current snapshots.
- `reviews/README.md` - post-match and daily review structure.
- `tools/README.md` - tools to build next.
- `daily/2026-06-11.md` - first matchday watch sheet.
- `sources/source_register.md` - source priorities and refresh rules.
- `sources/polymarket_official_agent_skills.md` - official Polymarket agent skills reference and local download notes.

## Daily Operating Rule

Each match should be processed in this order:

1. Motivation and tournament context.
2. Team news and lineup confidence.
3. Market price / probability comparison.
4. Event radar selection.
5. Stake sizing.
6. In-play triggers.
7. Result and learning review.

This is not a guarantee system. It is a decision journal that forces discipline, protects bankroll, and makes the prediction process improvable.
