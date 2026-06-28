# Historical Backfill Workflow

This document outlines the process for running and validating historical data backfills for the Sports Data Ingester. Currently, the workflow is designed around an MLB-first implementation.

## MLB Backfill Script

The historical backfill script is used to ingest historical games and boxscores. It currently supports MLB, with NFL deferred to a later phase.

### How to Run

To execute the MLB backfill, run the following command from the repository root:

```bash
python scripts/historical_backfill.py --sport mlb --start-date YYYY-MM-DD --end-date YYYY-MM-DD --chunk-size N
```

**Arguments:**
- `--sport`: Currently, `mlb` is the only supported target. `nfl` acts as a placeholder that safely exits.
- `--start-date` and `--end-date`: Defines the backfill window.
- `--chunk-size`: Controls how many days will be processed per run. Defaults to 30.
- `--delay`: Adds sleep to rate limit API requests. Defaults to 1.0 second.

## Import Strategy & Best Practices

To ensure data integrity, always use the following strategy when running new backfills:

### 1. One-Day Validation First
Before processing a large timeframe, test a **single day** first:
```bash
python scripts/historical_backfill.py --sport mlb --start-date 2024-04-01 --end-date 2024-04-01 --chunk-size 1
```
After the run completes, halt and validate the database directly. Check that the script gracefully created and populated the tables without errors or anomalies.

### 2. Idempotency Check
Once the single day completes, **re-run the exact same command**. The script should report that the day was skipped because it is already completed. This proves the idempotency and checkpointing feature is working properly.

### 3. Chunking the Remainder
Once validated, you may expand the date range to the intended window. Keep the `--chunk-size` argument reasonable to ensure smooth checkpointing during large multi-season backfills.

## Validation Steps

After running the backfill script, you must validate the data integrity. Open an interactive sqlite shell to `sports_historical.db` and ensure the following conditions are met:

1. **Checkpointing (`backfill_checkpoints` table)**:
   - Run `SELECT * FROM backfill_checkpoints;`
   - Verify that the processed dates have a `completed` status and accurate `games_found` counts.
2. **`historical_games`**:
   - Run `SELECT count(*) FROM historical_games;`
   - Confirm the count roughly aligns with the number of games expected in the provided timeframe.
3. **`historical_mlb_boxscores`**:
   - Run `SELECT count(*) FROM historical_mlb_boxscores;`
   - Ensure the detailed boxscore data corresponding to the historical games has been inserted. Both `batter` and `pitcher` roles should be present in this single table.
4. **`sports_data.db` Integrity**: Confirm that the primary live ingestion database (`sports_data.db`) remains completely unchanged. The historical backfill must isolate its data in `sports_historical.db` so it does not interfere with the live state.

## NFL Phase 2 Prerequisites & Decisions

The NFL historical backfill is currently deferred. Before implementing the NFL phase, the following prerequisites and architectural decisions must be resolved:

- **Schema Differences**: Determine how the NFL data model (e.g., player stats, positions, game phases) maps to the existing historical schema or if a distinct `historical_nfl_boxscores` structure is needed.
- **Data Source & API Limits**: Identify the data source (e.g., ESPN Hidden API, nflverse) for historical NFL data and document its rate limits or budget constraints.
- **Entity Aliasing**: Decide how NFL team IDs and player IDs will be normalized and mapped through the `entity_aliases` table.
- **Season Structure**: Determine how to handle the specific structure of NFL seasons (preseason, regular season, playoffs) versus the MLB structure when chunking and fetching historical data.
- **Checkpointing Strategy**: Verify if the MLB checkpointing mechanism is generic enough to support NFL, or if a specialized approach is required.