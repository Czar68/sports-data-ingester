# Sports Data Ingester - Context

## Objectives

1. Ingest live NFL scores, schedules, betting odds from free/cheap sources
2. Normalize and cache for sub-second access by internal APIs
3. Serve via internal REST API to sportsbook-optimizer, props-optimizer, arbitrage-scanner
4. Expose simple public API (rate-limited, free tier) for bettors

## Data Sources

| Source | Cost | Latency | Use Case |
|--------|------|---------|----------|
| ESPN Hidden API | Free | ~30s | Live scores, schedules, rosters |
| The Odds API | $99/mo | ~60s | Mainline odds from 40+ books |
| nflverse | Free | Nightly | Historical play-by-play, stats |

## Architecture