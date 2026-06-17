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
            for event in events:
                # Insert or Ignore for events
                await db.execute('''
                    INSERT OR IGNORE INTO events (id, sport_key, sport_title, commence_time, home_team, away_team)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    event.id,
                    event.sport_key,
                    event.sport_title,
                    event.commence_time.isoformat(),
                    event.home_team,
                    event.away_team
                ))

                for market in event.markets:
                    market_id = f"{event.id}_{market.key}"

                    # Insert or Replace for markets as they might update over time
                    await db.execute('''
                        INSERT OR REPLACE INTO markets (id, event_id, key, last_update)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        market_id,
                        event.id,
                        market.key,
                        market.last_update.isoformat()
                    ))

                    # For outcomes, we delete existing ones for the market and re-insert
                    # to keep it simple and handle changing outcomes accurately.
                    await db.execute('''
                        DELETE FROM outcomes WHERE market_id = ?
                    ''', (market_id,))

                    for outcome in market.outcomes:
                        await db.execute('''
                            INSERT INTO outcomes (market_id, name, price, point)
                            VALUES (?, ?, ?, ?)
                        ''', (
                            market_id,
                            outcome.name,
                            outcome.price,
                            outcome.point
                        ))

            # Commit all changes as a single transaction
            await db.commit()
            logger.info(f"Successfully upserted {len(events)} events into the database.")
