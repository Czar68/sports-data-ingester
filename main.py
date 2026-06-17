import asyncio
import logging
from core.database import init_db
from ingestion.odds_api import OddsAPIIngestor
from db.repository import EventRepository
from ingestion.manager import IngestionManager

logger = logging.getLogger("main")

async def main():
    """
    Main entry point for the Sports Data Ingestion Service.
    Initializes components and starts the async ingestion loop.
    """
    logger.info("Starting up Sports Data Ingestion Service...")

    # Initialize Database
    await init_db()

    # Initialize Dependencies
    ingestor = OddsAPIIngestor()
    repository = EventRepository()
    manager = IngestionManager(ingestor=ingestor, repository=repository)

    # Start the ingestion loop
    try:
        await manager.run_loop()
    except asyncio.CancelledError:
        logger.info("Ingestion loop cancelled.")
    except Exception as e:
        logger.critical(f"Critical failure in ingestion loop: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
