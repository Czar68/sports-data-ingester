# Repository Context: sports-data-ingester

## Purpose
An automated B2B sports statistics ingestion engine designed to fetch real-time player statistics, prop lines, and market odds data to feed downstream optimization platforms.

## Architecture & Environment
- **Runtime:** Python 3.11+ / Node.js native execution layer.
- **Environment Context:** Strictly tied to the localized `C:\Dev\` workspace.
- **Network Profile:** Optimizes data-harvesting tasks utilizing local 1Gbps symmetric fiber parameters via the Netgear RAX50v2 router network topology.

## Token & Secret Integrity
- All credential extraction (API Tokens, Session Keys) must strictly parse from the centralized configuration matrix located at `C:\Dev\Projects\ag-workspace\secrets.json`.
- Naked strings, hardcoded keys, and `.env` dependencies are explicitly barred from production modules.
