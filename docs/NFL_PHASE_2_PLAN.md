# NFL Phase 2 Implementation Plan: Historical Backfill Pipeline

## Scope
This document outlines the implementation strategy for Phase 2 of the NFL historical backfill pipeline.

### NFL Querying Strategy
- Focus on efficient retrieval of historical boxscores, play-by-play, and player stats.
- **Data Sources:**
  - nflverse (CSV/Parquet nightly data loads for historical play-by-play and stats)
  - ESPN Hidden API (for legacy missing schedules/rosters if nflverse is incomplete)
- **Ingestion Methodology:** Batch ingestion script designed to run incrementally to avoid rate limits on any supplementary APIs. Bulk data will be sourced from static flat files provided by nflverse to ensure speed and cost-effectiveness.
- **Handling Updates:** Append-only pattern for statistical accumulation. If retro-active stat corrections occur (common in NFL on Tuesdays/Wednesdays post-game), update existing records matching `game_id` and `player_id`.

### `historical_nfl_boxscores` Schema
The schema will be tailored to NFL-specific metrics while maintaining a structure similar to our general event patterns.

```sql
CREATE TABLE IF NOT EXISTS historical_nfl_boxscores (
    id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    team_id TEXT NOT NULL,
    season_year INTEGER NOT NULL,
    week INTEGER NOT NULL,
    -- Passing Stats
    passing_yards INTEGER DEFAULT 0,
    passing_touchdowns INTEGER DEFAULT 0,
    interceptions INTEGER DEFAULT 0,
    passing_attempts INTEGER DEFAULT 0,
    passing_completions INTEGER DEFAULT 0,
    -- Rushing Stats
    rushing_yards INTEGER DEFAULT 0,
    rushing_touchdowns INTEGER DEFAULT 0,
    rushing_attempts INTEGER DEFAULT 0,
    -- Receiving Stats
    receiving_yards INTEGER DEFAULT 0,
    receiving_touchdowns INTEGER DEFAULT 0,
    receptions INTEGER DEFAULT 0,
    targets INTEGER DEFAULT 0,
    -- General/Fantasy
    fumbles_lost INTEGER DEFAULT 0,
    two_point_conversions INTEGER DEFAULT 0,
    -- Metadata
    scraped_at TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES historical_games (id)
);

CREATE INDEX idx_nfl_boxscore_game_id ON historical_nfl_boxscores (game_id);
CREATE INDEX idx_nfl_boxscore_player_id ON historical_nfl_boxscores (player_id);
CREATE INDEX idx_nfl_boxscore_season_week ON historical_nfl_boxscores (season_year, week);
```

### Season Scope
- **Target Range:** 2018 Season to Present.
- **Reasoning:** 2018 represents the start of modern offensive trends, and is widely accepted as the standard cutoff for robust predictive modeling without introducing obsolete scheme biases.
- Data will encompass regular season and post-season games. Pre-season games will be excluded.

### Player Name Normalization Rules
Player name normalization is critical to mapping odds data to statistical outputs. We will leverage an `entity_aliases` table approach (as noted in Task-001).
- Strip all punctuation (e.g., "O'Dell" -> "Odell", "T.J." -> "TJ").
- Standardize suffixes (e.g., "Jr.", "Sr.", "II", "III", "IV" must be mapped to a canonical format, preferably omitted or stored in a separate canonical field, but we will omit suffixes for the core matching key).
- Convert all to lowercase.
- Truncate middle initials if inconsistently applied across sources.
- Examples:
  - "Patrick Mahomes II" -> `patrick mahomes`
  - "A.J. Brown" -> `aj brown`
  - "D.K. Metcalf" -> `dk metcalf`
  - "Travis Etienne Jr." -> `travis etienne`

### Reuse of `backfill_checkpoints` and `historical_games`
We will reuse existing pipeline structures to avoid duplication of effort.
- **`historical_games`:**
  - We will continue to use the `historical_games` table to store the overarching game metadata (Home Team, Away Team, Date, Score, Status).
  - The `sport_key` field will differentiate NFL games (`americanfootball_nfl`).
- **`backfill_checkpoints`:**
  - We will register our NFL ingestion runs in the `backfill_checkpoints` table.
  - This allows the pipeline to resume from the last successfully parsed week/season in case of a crash.
  - Keys will be structured like: `nfl_boxscore_season_2021_week_4`.
