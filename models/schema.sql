PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
  team TEXT PRIMARY KEY,
  group_code TEXT,
  confederation TEXT,
  tier TEXT,
  weak_team_level TEXT,
  strong_team_level TEXT,
  swing_level TEXT,
  attention_level TEXT,
  information_gap_level TEXT,
  likely_role TEXT,
  primary_opportunities TEXT,
  key_risks TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS groups_radar (
  group_code TEXT PRIMARY KEY,
  teams TEXT NOT NULL,
  attention_level TEXT,
  trade_volume_estimate TEXT,
  information_gap_level TEXT,
  group_type TEXT,
  key_story TEXT,
  primary_opportunities TEXT,
  primary_risks TEXT
);

CREATE TABLE IF NOT EXISTS matches (
  match_id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  utc_time TEXT,
  local_time TEXT,
  china_time TEXT,
  stage TEXT NOT NULL,
  group_code TEXT,
  home_team TEXT NOT NULL,
  away_team TEXT NOT NULL,
  venue TEXT,
  city TEXT,
  priority TEXT CHECK (priority IN ('A', 'B', 'C')),
  watch_status TEXT,
  home_motivation TEXT,
  away_motivation TEXT,
  lineup_confidence TEXT,
  weather_note TEXT,
  referee_note TEXT,
  market_note TEXT,
  initial_prediction TEXT,
  event_focus TEXT,
  no_bet_reason TEXT,
  review_status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS event_markets (
  event_id TEXT PRIMARY KEY,
  match_id TEXT NOT NULL REFERENCES matches(match_id),
  event_type TEXT NOT NULL,
  market TEXT NOT NULL,
  selection TEXT,
  pre_match_or_live TEXT CHECK (pre_match_or_live IN ('pre', 'live', 'both')),
  book_price REAL,
  implied_probability REAL,
  my_probability REAL,
  edge REAL,
  confidence TEXT CHECK (confidence IN ('low', 'medium', 'high')),
  stake_units REAL DEFAULT 0,
  entry_condition TEXT,
  cancel_condition TEXT,
  result TEXT,
  profit_units REAL,
  review_note TEXT
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  event_id TEXT NOT NULL REFERENCES event_markets(event_id),
  captured_at TEXT NOT NULL,
  book_or_exchange TEXT,
  price REAL,
  implied_probability REAL,
  market_note TEXT
);

CREATE TABLE IF NOT EXISTS polymarket_markets (
  discovered_at TEXT NOT NULL,
  platform TEXT NOT NULL DEFAULT 'polymarket',
  source TEXT,
  event_id TEXT,
  event_slug TEXT,
  event_title TEXT,
  market_id TEXT,
  market_slug TEXT,
  question TEXT NOT NULL,
  event_type TEXT,
  active INTEGER,
  closed INTEGER,
  accepting_orders TEXT,
  end_date TEXT,
  volume REAL DEFAULT 0,
  volume_24hr REAL DEFAULT 0,
  liquidity REAL DEFAULT 0,
  open_interest REAL DEFAULT 0,
  best_bid TEXT,
  best_ask TEXT,
  last_trade_price TEXT,
  outcome_prices TEXT,
  outcomes TEXT,
  url TEXT,
  matched_keywords TEXT,
  notes TEXT,
  PRIMARY KEY (discovered_at, event_id, market_id, question)
);

CREATE TABLE IF NOT EXISTS polymarket_champion_team_map (
  discovered_at TEXT NOT NULL,
  market_id TEXT NOT NULL,
  market_slug TEXT,
  question TEXT NOT NULL,
  extracted_team TEXT,
  canonical_team TEXT,
  mapping_status TEXT,
  group_code TEXT,
  tier TEXT,
  weak_team_level TEXT,
  strong_team_level TEXT,
  swing_level TEXT,
  attention_level TEXT,
  information_gap_level TEXT,
  likely_role TEXT,
  best_bid TEXT,
  best_ask TEXT,
  last_trade_price TEXT,
  implied_yes_probability REAL DEFAULT 0,
  volume REAL DEFAULT 0,
  volume_24hr REAL DEFAULT 0,
  liquidity REAL DEFAULT 0,
  url TEXT,
  notes TEXT,
  PRIMARY KEY (discovered_at, market_id)
);

CREATE TABLE IF NOT EXISTS prediction_market_topics (
  topic_id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,
  market_id TEXT NOT NULL,
  event_slug TEXT,
  market_slug TEXT,
  title TEXT NOT NULL,
  topic_type TEXT,
  canonical_team TEXT,
  group_code TEXT,
  first_seen_at TEXT NOT NULL,
  latest_seen_at TEXT NOT NULL,
  current_status TEXT NOT NULL,
  lifecycle_note TEXT,
  url TEXT,
  affiliate_url TEXT,
  UNIQUE (platform, market_id)
);

CREATE TABLE IF NOT EXISTS market_status_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  topic_id TEXT NOT NULL REFERENCES prediction_market_topics(topic_id),
  captured_at TEXT NOT NULL,
  active INTEGER,
  closed INTEGER,
  accepting_orders TEXT,
  status TEXT NOT NULL,
  best_bid TEXT,
  best_ask TEXT,
  last_trade_price TEXT,
  volume REAL DEFAULT 0,
  volume_24hr REAL DEFAULT 0,
  liquidity REAL DEFAULT 0,
  open_interest REAL DEFAULT 0,
  status_note TEXT
);

CREATE TABLE IF NOT EXISTS market_event_scores (
  scored_at TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES prediction_market_topics(topic_id),
  platform TEXT NOT NULL,
  title TEXT NOT NULL,
  topic_type TEXT,
  canonical_team TEXT,
  group_code TEXT,
  current_status TEXT,
  conservative_score REAL DEFAULT 0,
  upside_score REAL DEFAULT 0,
  attention_score REAL DEFAULT 0,
  ignored_score REAL DEFAULT 0,
  risk_reward_score REAL DEFAULT 0,
  risk_score REAL DEFAULT 0,
  implied_yes_probability REAL DEFAULT 0,
  volume_24hr REAL DEFAULT 0,
  liquidity REAL DEFAULT 0,
  recommendation_track TEXT,
  action_label TEXT,
  rationale TEXT,
  affiliate_url TEXT,
  PRIMARY KEY (scored_at, topic_id)
);

CREATE TABLE IF NOT EXISTS staking_recommendations (
  calculated_at TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES prediction_market_topics(topic_id),
  title TEXT NOT NULL,
  recommendation_track TEXT,
  action_label TEXT,
  recommended_stake_units REAL DEFAULT 0,
  max_allowed_stake_units REAL DEFAULT 0,
  stake_band TEXT,
  risk_rule TEXT,
  entry_condition TEXT,
  cancel_condition TEXT,
  rationale TEXT,
  affiliate_url TEXT,
  PRIMARY KEY (calculated_at, topic_id)
);

CREATE TABLE IF NOT EXISTS market_opportunities (
  analyzed_at TEXT NOT NULL,
  topic_id TEXT NOT NULL REFERENCES prediction_market_topics(topic_id),
  platform TEXT NOT NULL,
  event_slug TEXT,
  market_id TEXT,
  title TEXT NOT NULL,
  topic_type TEXT,
  canonical_team TEXT,
  group_code TEXT,
  market_structure_type TEXT,
  outcome_relation TEXT,
  neg_risk_status TEXT,
  current_status TEXT,
  implied_yes_probability REAL DEFAULT 0,
  volume REAL DEFAULT 0,
  volume_24hr REAL DEFAULT 0,
  liquidity REAL DEFAULT 0,
  open_interest REAL DEFAULT 0,
  recommendation_track TEXT,
  selection_direction TEXT,
  direction_confidence TEXT,
  direction_source TEXT,
  opportunity_segment TEXT,
  schedule_stage TEXT,
  direction_thesis TEXT,
  cancel_condition TEXT,
  affiliate_url TEXT,
  PRIMARY KEY (analyzed_at, topic_id)
);

CREATE TABLE IF NOT EXISTS bet_ledger (
  bet_id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  match_id TEXT NOT NULL REFERENCES matches(match_id),
  event_id TEXT REFERENCES event_markets(event_id),
  stage TEXT,
  market TEXT NOT NULL,
  selection TEXT NOT NULL,
  price REAL NOT NULL,
  stake_units REAL NOT NULL CHECK (stake_units > 0),
  potential_profit_units REAL,
  result TEXT CHECK (result IN ('pending', 'win', 'loss', 'push', 'cashout', 'void')),
  profit_units REAL DEFAULT 0,
  reason TEXT NOT NULL,
  entry_time TEXT,
  exit_time TEXT,
  review_tag TEXT
);

CREATE TABLE IF NOT EXISTS daily_event_rankings (
  date TEXT NOT NULL,
  rank_type TEXT NOT NULL CHECK (rank_type IN ('most_watched', 'most_ignored', 'best_risk_reward')),
  rank INTEGER NOT NULL,
  topic_id TEXT REFERENCES prediction_market_topics(topic_id),
  platform TEXT,
  match_id TEXT REFERENCES matches(match_id),
  event_id TEXT REFERENCES event_markets(event_id),
  event_title TEXT NOT NULL,
  category TEXT,
  current_status TEXT,
  importance_score REAL,
  attention_score REAL,
  ignored_score REAL,
  risk_reward_score REAL,
  risk_score REAL DEFAULT 0,
  implied_yes_probability REAL DEFAULT 0,
  recommendation_track TEXT,
  recommended_action TEXT,
  recommended_stake_units REAL DEFAULT 0,
  cancel_condition TEXT,
  copy_angle TEXT,
  affiliate_url TEXT,
  PRIMARY KEY (date, rank_type, rank)
);

CREATE TABLE IF NOT EXISTS content_posts (
  post_id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  post_type TEXT,
  title TEXT NOT NULL,
  hook TEXT,
  key_points TEXT,
  risk_disclaimer TEXT,
  source_event_ids TEXT,
  status TEXT DEFAULT 'draft'
);

CREATE TABLE IF NOT EXISTS daily_reviews (
  date TEXT PRIMARY KEY,
  total_stake_units REAL DEFAULT 0,
  total_profit_units REAL DEFAULT 0,
  best_decision TEXT,
  worst_decision TEXT,
  discipline_score INTEGER CHECK (discipline_score BETWEEN 1 AND 5),
  next_day_adjustment TEXT
);
