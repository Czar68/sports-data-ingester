import aiosqlite
import logging
from core.settings import settings

logger = logging.getLogger("ingestion.database")

async def init_db():
    """
    Initializes the database by creating tables if they don't exist.
    """
    logger.info("Initializing database...")
    async with aiosqlite.connect(settings.database_file) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                sport_key TEXT NOT NULL,
                sport_title TEXT NOT NULL,
                commence_time TEXT NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS markets (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                key TEXT NOT NULL,
                last_update TEXT NOT NULL,
                FOREIGN KEY (event_id) REFERENCES events (id)
            )
        ''')

        await db.execute('''
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                point REAL,
                FOREIGN KEY (market_id) REFERENCES markets (id)
            )
        ''')

        await db.commit()
    logger.info("Database initialized successfully.")
