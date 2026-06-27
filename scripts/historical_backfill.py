import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger("historical_backfill")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sports_historical.db')

def init_db():
    """Initializes the historical database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create backfill_checkpoints table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backfill_checkpoints (
            date TEXT,
            sport TEXT,
            status TEXT,
            games_found INTEGER DEFAULT 0,
            games_processed INTEGER DEFAULT 0,
            PRIMARY KEY (date, sport)
        )
    ''')

    # Create historical_games table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_games (
            game_id TEXT PRIMARY KEY,
            date TEXT,
            sport TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT
        )
    ''')

    # Create historical_mlb_boxscores table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_mlb_boxscores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT,
            game_date TEXT,
            player_id TEXT,
            player_name TEXT,
            team TEXT,
            role TEXT,
            hits INTEGER,
            rbi INTEGER,
            home_runs INTEGER,
            strikeouts INTEGER,
            walks INTEGER,
            earned_runs INTEGER,
            FOREIGN KEY (game_id) REFERENCES historical_games(game_id)
        )
    ''')

    conn.commit()
    conn.close()
    logger.info(f"Initialized database schema at {DB_PATH}")

def get_checkpoint(date: str, sport: str):
    """Gets the checkpoint status for a specific date and sport."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT status, games_found, games_processed FROM backfill_checkpoints WHERE date = ? AND sport = ?', (date, sport))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {'status': row[0], 'games_found': row[1], 'games_processed': row[2]}
    return None

def update_checkpoint(date: str, sport: str, status: str, games_found: int = 0, games_processed: int = 0):
    """Updates or inserts a checkpoint record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO backfill_checkpoints (date, sport, status, games_found, games_processed)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date, sport) DO UPDATE SET
            status=excluded.status,
            games_found=excluded.games_found,
            games_processed=excluded.games_processed
    ''', (date, sport, status, games_found, games_processed))
    conn.commit()
    conn.close()

import requests
import time

def fetch_espn_mlb_scoreboard(date: str) -> list:
    """Fetches MLB scoreboard for a given date (YYYY-MM-DD)."""
    date_str = date.replace('-', '')
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard?dates={date_str}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json().get('events', [])
    except Exception as e:
        logger.error(f"Failed to fetch scoreboard for {date}: {e}")
        return []

def fetch_espn_mlb_summary(game_id: str) -> dict:
    """Fetches full game summary/boxscore for a given game ID."""
    url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/summary?event={game_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch summary for game {game_id}: {e}")
        return {}

def parse_mlb_boxscore(summary_data: dict, game_id: str, game_date: str) -> list:
    """Parses MLB boxscore data into standard rows."""
    boxscore = summary_data.get('boxscore', {})
    players = boxscore.get('players', [])
    parsed_rows = []

    for team_data in players:
        team_info = team_data.get('team', {})
        team_abbrev = team_info.get('abbreviation', 'UNK')

        for stat_block in team_data.get('statistics', []):
            stat_type = stat_block.get('type') # 'batting' or 'pitching'
            keys = stat_block.get('keys', [])

            for athlete_data in stat_block.get('athletes', []):
                athlete = athlete_data.get('athlete', {})
                stats = athlete_data.get('stats', [])

                # Default stats
                hits, rbi, home_runs, strikeouts, walks, earned_runs = 0, 0, 0, 0, 0, 0

                try:
                    if stat_type == 'batting':
                        hits = int(stats[keys.index('hits')]) if 'hits' in keys else 0
                        rbi = int(stats[keys.index('RBIs')]) if 'RBIs' in keys else 0
                        home_runs = int(stats[keys.index('homeRuns')]) if 'homeRuns' in keys else 0
                        strikeouts = int(stats[keys.index('strikeouts')]) if 'strikeouts' in keys else 0
                        walks = int(stats[keys.index('walks')]) if 'walks' in keys else 0
                        role = 'batter'
                    elif stat_type == 'pitching':
                        hits = int(stats[keys.index('hits')]) if 'hits' in keys else 0
                        earned_runs = int(stats[keys.index('earnedRuns')]) if 'earnedRuns' in keys else 0
                        strikeouts = int(stats[keys.index('strikeouts')]) if 'strikeouts' in keys else 0
                        walks = int(stats[keys.index('walks')]) if 'walks' in keys else 0
                        home_runs = int(stats[keys.index('homeRuns')]) if 'homeRuns' in keys else 0
                        role = 'pitcher'
                    else:
                        continue # Skip fielding etc.
                except (ValueError, IndexError):
                    logger.debug(f"Skipping incomplete stat line for {athlete.get('displayName')}")
                    continue

                parsed_rows.append({
                    'game_id': game_id,
                    'game_date': game_date,
                    'player_id': str(athlete.get('id', '')),
                    'player_name': athlete.get('displayName', 'Unknown'),
                    'team': team_abbrev,
                    'role': role,
                    'hits': hits,
                    'rbi': rbi,
                    'home_runs': home_runs,
                    'strikeouts': strikeouts,
                    'walks': walks,
                    'earned_runs': earned_runs
                })

    return parsed_rows

def process_mlb_date(date: str, delay: float = 1.0) -> bool:
    """Processes a single date for MLB."""
    logger.info(f"Processing MLB date: {date}")

    events = fetch_espn_mlb_scoreboard(date)
    if not events:
        logger.info(f"No MLB games found for {date}.")
        update_checkpoint(date, 'mlb', 'completed', 0, 0)
        return True

    update_checkpoint(date, 'mlb', 'pending', len(events), 0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    games_processed = 0

    try:
        for event in events:
            game_id = event['id']
            status_desc = event.get('status', {}).get('type', {}).get('description', 'Unknown')

            # Get basic game info from scoreboard
            competitions = event.get('competitions', [{}])[0]
            competitors = competitions.get('competitors', [])
            home_team, away_team = "UNK", "UNK"
            home_score, away_score = 0, 0

            for comp in competitors:
                if comp.get('homeAway') == 'home':
                    home_team = comp.get('team', {}).get('abbreviation', 'UNK')
                    home_score = int(comp.get('score', 0))
                else:
                    away_team = comp.get('team', {}).get('abbreviation', 'UNK')
                    away_score = int(comp.get('score', 0))

            # Atomic commit per game


            # Check if game already processed
            cursor.execute("SELECT 1 FROM historical_games WHERE game_id = ?", (game_id,))
            if cursor.fetchone():
                games_processed += 1
                continue

            cursor.execute('''
                INSERT OR IGNORE INTO historical_games
                (game_id, date, sport, home_team, away_team, home_score, away_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (game_id, date, 'mlb', home_team, away_team, home_score, away_score, status_desc))

            if status_desc in ['Final', 'Postponed', 'Canceled']: # Don't parse live games if backfilling
                summary_data = fetch_espn_mlb_summary(game_id)
                boxscore_rows = parse_mlb_boxscore(summary_data, game_id, date)

                for row in boxscore_rows:
                    cursor.execute('''
                        INSERT INTO historical_mlb_boxscores
                        (game_id, game_date, player_id, player_name, team, role,
                         hits, rbi, home_runs, strikeouts, walks, earned_runs)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row['game_id'], row['game_date'], row['player_id'], row['player_name'],
                        row['team'], row['role'], row['hits'], row['rbi'], row['home_runs'],
                        row['strikeouts'], row['walks'], row['earned_runs']
                    ))

            cursor.execute("COMMIT")
            games_processed += 1

            # Rate limiting
            time.sleep(delay)

        update_checkpoint(date, 'mlb', 'completed', len(events), games_processed)
        return True

    except Exception as e:
        cursor.execute("ROLLBACK")
        logger.error(f"Error processing MLB date {date}: {e}")
        update_checkpoint(date, 'mlb', 'failed', len(events), games_processed)
        return False
    finally:
        conn.close()

import argparse
from datetime import timedelta

def process_nfl_date(date: str, delay: float = 1.0) -> bool:
    """Placeholder for NFL date processing."""
    logger.info(f"NFL date processing for {date} is deferred to Phase 2.")
    print("\n[INFO] NFL backfill is intentionally deferred until querying and schema decisions are finalized.")
    print("Exiting cleanly.\n")
    return False

def main():
    parser = argparse.ArgumentParser(description="Historical Data Backfill Script")
    parser.add_argument('--sport', type=str, required=True, choices=['mlb', 'nfl'], help='Sport to backfill (mlb, nfl)')
    parser.add_argument('--start-date', type=str, required=True, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, required=True, help='End date (YYYY-MM-DD)')
    parser.add_argument('--chunk-size', type=int, default=30, help='Max number of dates to process in this run')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between API calls (seconds)')

    args = parser.parse_args()

    # Configure logging for CLI
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    init_db()

    start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d')

    if start_date > end_date:
        logger.error("Start date must be before or equal to end date.")
        return

    # Handle NFL placeholder exit
    if args.sport == 'nfl':
        process_nfl_date(args.start_date)
        return

    dates_processed = 0
    current_date = start_date

    while current_date <= end_date and dates_processed < args.chunk_size:
        date_str = current_date.strftime('%Y-%m-%d')

        # Check state
        checkpoint = get_checkpoint(date_str, args.sport)
        if checkpoint and checkpoint['status'] == 'completed':
            logger.info(f"Skipping {date_str} - already completed.")
            current_date += timedelta(days=1)
            continue

        logger.info(f"Starting processing for {date_str}...")

        if args.sport == 'mlb':
            success = process_mlb_date(date_str, args.delay)
            if success:
                dates_processed += 1
            else:
                logger.error(f"Failed to process {date_str}. Halting chunk.")
                break

        current_date += timedelta(days=1)

    if dates_processed == 0 and current_date > end_date:
        logger.info("No pending dates to process.")
    else:
        logger.info(f"Finished processing chunk of {dates_processed} dates.")

if __name__ == "__main__":
    main()
