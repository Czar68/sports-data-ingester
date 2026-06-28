# Historical Backfill Workflow

This document outlines the process for running and validating historical data backfills for the Sports Data Ingester. Currently, the workflow is designed around an MLB-first implementation.

## MLB Backfill Script

The MLB historical backfill script is used to ingest historical games and boxscores.

### How to Run

To execute the MLB backfill, run the following command from the repository root:

```bash
python scripts/mlb_backfill.py
```
*(Note: Adjust the script path if the MLB backfill script is located elsewhere.)*

## Validation Steps

After running the backfill script, you must validate the data integrity. Ensure the following conditions are met:

1. **Checkpointing**: Verify that the backfill script correctly created and updated checkpoints so that partial runs can be resumed without duplicating work. Check the designated checkpoint file or database table.
2. **`historical_games`**: Confirm that the `historical_games` table contains the expected number of records for the targeted backfill period.
3. **`historical_mlb_boxscores`**: Confirm that the `historical_mlb_boxscores` table contains the detailed boxscore data corresponding to the historical games. Check for completeness and proper schema mapping.
4. **`sports_data.db` Integrity**: Confirm that the primary live ingestion database (`sports_data.db`) remains completely unchanged. The historical backfill must isolate its data (e.g., using a separate `historical_data.db` or specific historical tables that do not interfere with the live `sports_data.db` state).

## NFL Phase 2 Prerequisites & Decisions

The NFL historical backfill is currently deferred. Before implementing the NFL phase, the following prerequisites and architectural decisions must be resolved:

- **Schema Differences**: Determine how the NFL data model (e.g., player stats, positions, game phases) maps to the existing historical schema or if a distinct `historical_nfl_boxscores` structure is needed.
- **Data Source & API Limits**: Identify the data source (e.g., ESPN Hidden API, nflverse) for historical NFL data and document its rate limits or budget constraints.
- **Entity Aliasing**: Decide how NFL team IDs and player IDs will be normalized and mapped through the `entity_aliases` table.
- **Season Structure**: Determine how to handle the specific structure of NFL seasons (preseason, regular season, playoffs) versus the MLB structure when chunking and fetching historical data.
- **Checkpointing Strategy**: Verify if the MLB checkpointing mechanism is generic enough to support NFL, or if a specialized approach is required.
