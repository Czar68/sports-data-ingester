import asyncio
import logging
from typing import List
from ingestion.base import BaseIngestor
from db.repository import EventRepository
from models.events import BaseEvent
from core.settings import settings

logger = logging.getLogger("ingestion.manager")

class IngestionManager:
    """
    Orchestrates the ingestion loop: Fetch -> Normalize/Validate -> Store (Upsert).
    """
    def __init__(self, ingestor: BaseIngestor, repository: EventRepository):
        self.ingestor = ingestor
        self.repository = repository
        self.polling_interval = settings.polling_interval

    async def process_cycle(self):
        """
        Executes a single cycle of the ingestion process.
        """
        try:
            logger.info("Starting ingestion cycle...")

            # 1. Fetch
            raw_data_list = await self.ingestor.fetch_data()

            # 2. Normalize / Validate
            events: List[BaseEvent] = []
            for raw_item in raw_data_list:
                try:
                    event = self.ingestor.normalize(raw_item)
                    events.append(event)
                except Exception as e:
                    logger.error(f"Failed to normalize item: {e}. Raw Data ID: {raw_item.get('id')}")

            # 3. Store (Upsert)
            if events:
                await self.repository.upsert_events(events)
            else:
                logger.info("No valid events to store in this cycle.")

            logger.info("Ingestion cycle completed successfully.")

        except Exception as e:
            logger.error(f"Error during ingestion cycle: {e}")

    async def run_loop(self):
        """
        Runs the ingestion cycle continuously at the configured polling interval.
        Using asyncio.sleep prevents blocking the event loop.
        """
        logger.info(f"Starting ingestion loop with polling interval: {self.polling_interval} seconds")
        while True:
            await self.process_cycle()
            logger.info(f"Sleeping for {self.polling_interval} seconds before next cycle.")
            await asyncio.sleep(self.polling_interval)
