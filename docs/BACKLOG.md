# Sports Data Ingester - Task Backlog

## Context
Live NFL data platform powering sportsbook-optimizer, props-optimizer, arbitrage-scanner. MVP 3 weeks before NFL season start (Sept 5, 2026).

## Queued Tasks (001-008)

### Task-001: PostgreSQL Schema Design
- Tables: games, teams, players, odds_snapshots, player_props, entity_aliases
- Indexes: game_id, bookmaker_id, player_id, scraped_at
- Append-only odds snapshots for line movement history
- Status: QUEUED TO JULES

### Task-002: ESPN Hidden API Ingestion Worker
- Poll scoreboard every 30 seconds during active season
- Parse games, scores, schedules, teams, players
- Normalize IDs using entity_aliases table
- Handle schema drift gracefully (log warnings, continue)
- Status: QUEUED TO JULES

### Task-003: The Odds API Ingestion Worker
- Poll mainlines (spreads, totals, moneylines) every 60 seconds
- Budget tracking: 20k calls/month on $99 tier
- Implement exponential backoff on 429
- Status: QUEUED TO JULES

### Task-004: Redis Caching Layer
- Mirror odds_snapshots to Redis (TTL 60s)
- Cache live scores (TTL 10s)
- Invalidate on database writes
- Status: QUEUED TO JULES

### Task-005: Internal REST API (FastAPI)
- GET /internal/odds/latest?game_id=...&market=...
- GET /internal/player-props?game_id=...&player_id=...&stat=...
- GET /internal/scores/live
- GET /internal/schedule?week=...
- Implement sharp-weighted consensus (Pinnacle + retail blend)
- Status: QUEUED TO JULES

### Task-006: Sportsbook-Optimizer Integration
- Wire internal API to sportsbook-optimizer
- Feed normalized decimal odds to EV/Kelly pipeline
- Status: DEFERRED (depends on Task-005)

### Task-007: Props-Optimizer Integration
- Wire internal API to props-optimizer
- Provide player prop lines + basic stats
- Status: DEFERRED (depends on Task-005)

### Task-008: Arbitrage-Scanner Integration
- Scan all games' h2h odds via internal API
- Detect cross-book arbs (arbitrage index < 1.0)
- Store in arb_opportunities table
- Status: DEFERRED (depends on Task-005)

## Deferred (Post-MVP, Aug 1+)

### Task-009: Play-by-Play Ingestion
- Load nflfastR CSVs for historical training data
- Status: DEFERRED

### Task-010: Player Stats Ingestion
- ESPN box scores + stat aggregates
- Status: DEFERRED

### Task-011: Public API (Rate-Limited)
- GET /api/games, /api/odds, /api/arbitrage
- Rate limit: 60 req/min per IP
- Serve from Redis cache
- Status: DEFERRED

### Task-012: Monitoring & Alerting
- Track ingestion success rates
- Alert on stale data (>5min old)
- Monitor provider usage vs budget
- Status: DEFERRED