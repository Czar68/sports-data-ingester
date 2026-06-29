import aiosqlite
import logging
from typing import List
from models.events import BaseEvent
from core.settings import settings

logger = logging.getLogger("ingestion.db.repository")

class EventRepository:
    """
    Repository pattern for Database interactions.
    Separates SQL queries from business logic.
    Provides async SQLite inserts using upsert/insert-ignore logic for idempotency.
    """
    def __init__(self, db_file: str = settings.database_file):
        self.db_file = db_file

    async def upsert_events(self, events: List[BaseEvent]):
        """
        Upserts a list of events into the database.
        Checks for existing records based on ID to ensure idempotent data ingestion,
        preventing database bloat.
        """
        if not events:
            return

        # Asynchronous context manager ensures the connection is properly managed
        async with aiosqlite.connect(self.db_file) as db:
            events_data = []
            markets_data = []
            outcomes_delete_data = []
            outcomes_insert_data = []

            for event in events:
                events_data.append((
                    event.id,
                    event.sport_key,
                    event.sport_title,
                    event.commence_time.isoformat(),
                    event.home_team,
                    event.away_team
                ))

                for market in event.markets:
                    market_id = f"{event.id}_{market.key}"
                    markets_data.append((
                        market_id,
                        event.id,
                        market.key,
                        market.last_update.isoformat()
                    ))

                    outcomes_delete_data.append((market_id,))

                    for outcome in market.outcomes:
                        outcomes_insert_data.append((
                            market_id,
                            outcome.name,
                            outcome.price,
                            outcome.point
                        ))

            await db.executemany('''
                INSERT OR IGNORE INTO events (id, sport_key, sport_title, commence_time, home_team, away_team)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', events_data)

            await db.executemany('''
                INSERT OR REPLACE INTO markets (id, event_id, key, last_update)
                VALUES (?, ?, ?, ?)
            ''', markets_data)

            await db.executemany('''
                DELETE FROM outcomes WHERE market_id = ?
            ''', outcomes_delete_data)

            await db.executemany('''
                INSERT INTO outcomes (market_id, name, price, point)
                VALUES (?, ?, ?, ?)
            ''', outcomes_insert_data)

            # Commit all changes as a single transaction
            await db.commit()
            logger.info(f"Successfully upserted {len(events)} events into the database.")
