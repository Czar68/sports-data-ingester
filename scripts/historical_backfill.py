import argparse
import asyncio
import httpx
import aiosqlite
import json
import logging
import uuid
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("historical_backfill")

DB_FILE = "sports_historical.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS backfill_checkpoints (
                id TEXT PRIMARY KEY,
                sport TEXT UNIQUE,
                last_date TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS historical_games (
                id TEXT PRIMARY KEY,
                sport TEXT,
                date TEXT,
                home_team TEXT,
                away_team TEXT,
                status TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS historical_mlb_boxscores (
                id TEXT PRIMARY KEY,
                game_id TEXT,
                team TEXT,
                player TEXT,
                position TEXT,
                batting_stats TEXT,
                pitching_stats TEXT,
                UNIQUE(game_id, player)
            )
        ''')
        await db.commit()

async def get_checkpoint(sport):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT last_date FROM backfill_checkpoints WHERE sport = ?", (sport,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def update_checkpoint(sport, date_str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            INSERT OR REPLACE INTO backfill_checkpoints (id, sport, last_date)
            VALUES (
                COALESCE((SELECT id FROM backfill_checkpoints WHERE sport = ?), ?),
                ?,
                ?
            )
        ''', (sport, str(uuid.uuid4()), sport, date_str))
        await db.commit()

async def fetch_json(url, client):
    logger.info(f"Fetching {url}")
    response = await client.get(url, timeout=15.0)
    response.raise_for_status()
    await asyncio.sleep(0.5) # Rate limiting
    return response.json()

async def process_mlb_day(date_str, client):
    scoreboard_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"

    try:
        data = await fetch_json(scoreboard_url, client)
    except Exception as e:
        logger.error(f"Failed to fetch scoreboard for {date_str}: {e}")
        return False

    events = data.get('events', [])
    if not events:
        logger.info(f"No games found for {date_str}")
        return True

    async with aiosqlite.connect(DB_FILE) as db:
        for event in events:
            game_id = event['id']
            date = event['date']
            status = event['status']['type']['name']

            competitors = event['competitions'][0]['competitors']
            home_team = next((c['team']['displayName'] for c in competitors if c['homeAway'] == 'home'), "Unknown")
            away_team = next((c['team']['displayName'] for c in competitors if c['homeAway'] == 'away'), "Unknown")

            await db.execute('''
                INSERT OR IGNORE INTO historical_games (id, sport, date, home_team, away_team, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (game_id, 'mlb', date, home_team, away_team, status))

            # Fetch summary
            summary_url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"
            try:
                summary_data = await fetch_json(summary_url, client)
            except Exception as e:
                logger.error(f"Failed to fetch summary for {game_id}: {e}")
                continue

            boxscore = summary_data.get('boxscore', {})
            players_data = boxscore.get('players', [])

            for team_data in players_data:
                team_name = team_data.get('team', {}).get('displayName', 'Unknown')
                statistics = team_data.get('statistics', [])

                for stat_group in statistics:
                    stat_type = stat_group.get('type') # 'batting' or 'pitching'
                    if stat_type not in ['batting', 'pitching']:
                        continue

                    keys = stat_group.get('keys', [])
                    for athlete in stat_group.get('athletes', []):
                        player_id = athlete.get('athlete', {}).get('id', str(uuid.uuid4()))
                        player_name = athlete.get('athlete', {}).get('displayName', 'Unknown')
                        position = athlete.get('position', {}).get('abbreviation', '')
                        stats_values = athlete.get('stats', [])

                        stats_dict = dict(zip(keys, stats_values))
                        stats_json = json.dumps(stats_dict)

                        # We use INSERT OR REPLACE to update stats if we re-run
                        # Alternatively, we can UPSERT based on unique constraints
                        if stat_type == 'batting':
                            await db.execute('''
                                INSERT INTO historical_mlb_boxscores (id, game_id, team, player, position, batting_stats, pitching_stats)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(game_id, player) DO UPDATE SET batting_stats=excluded.batting_stats, position=excluded.position
                            ''', (str(uuid.uuid4()), game_id, team_name, player_name, position, stats_json, None))
                        elif stat_type == 'pitching':
                            await db.execute('''
                                INSERT INTO historical_mlb_boxscores (id, game_id, team, player, position, batting_stats, pitching_stats)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                ON CONFLICT(game_id, player) DO UPDATE SET pitching_stats=excluded.pitching_stats, position=excluded.position
                            ''', (str(uuid.uuid4()), game_id, team_name, player_name, position, None, stats_json))

        await db.commit()
    return True

async def backfill_mlb(start_date, end_date):
    await init_db()
    checkpoint = await get_checkpoint('mlb')

    start_dt = datetime.strptime(start_date, "%Y%m%d")
    end_dt = datetime.strptime(end_date, "%Y%m%d")

    if checkpoint:
        # Resume from next day after checkpoint
        ckpt_dt = datetime.strptime(checkpoint, "%Y%m%d")
        if ckpt_dt >= start_dt:
            logger.info(f"Resuming from checkpoint: {checkpoint}")
            start_dt = ckpt_dt + timedelta(days=1)

    if start_dt > end_dt:
        logger.info("Backfill complete up to end_date.")
        return

    current_dt = start_dt
    async with httpx.AsyncClient() as client:
        while current_dt <= end_dt:
            date_str = current_dt.strftime("%Y%m%d")
            logger.info(f"Processing MLB data for {date_str}...")

            success = await process_mlb_day(date_str, client)
            if success:
                await update_checkpoint('mlb', date_str)
                logger.info(f"Successfully processed and checkpointed {date_str}.")
            else:
                logger.error(f"Failed to process {date_str}. Stopping backfill.")
                break

            current_dt += timedelta(days=1)

def main():
    parser = argparse.ArgumentParser(description="Historical Data Backfill Script")
    parser.add_argument("--sport", required=True, choices=['mlb', 'nfl'], help="Sport to backfill")
    parser.add_argument("--start-date", type=str, default="20240401", help="Start date YYYYMMDD")
    parser.add_argument("--end-date", type=str, default="20240403", help="End date YYYYMMDD")

    args = parser.parse_args()

    if args.sport == 'nfl':
        logger.info("NFL backfill is deferred. Exiting cleanly.")
        exit(0)

    elif args.sport == 'mlb':
        asyncio.run(backfill_mlb(args.start_date, args.end_date))

if __name__ == "__main__":
    main()
