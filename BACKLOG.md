# Backlog: sports-data-ingester

## Active Queue

### Task 001: Initialize Environmental Hardening Base
- **Priority:** 1
- **Goal:** Ensure all core entry files load the global SDK utility `ag_sdk` using absolute pathing to map secrets cleanly from `C:\Dev\Projects\ag-workspace\secrets.json`.

### Task 002: Kalshi Prediction Market Integration Plugin
- **Priority:** 2
- **Goal:** Build a dedicated, lightweight API data-fetching plugin directly within this ingester footprint to harvest regulated prediction market edge metrics.
- **Requirement:** Route the harvested market data directly into the active optimization backends (`sportsbook-optimizer` / `props-optimizer`) without expanding or creating a 10th repository footprint.
