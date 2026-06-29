import logging
import httpx
from typing import Any, List, Dict
from ingestion.base import BaseIngestor
from models.events import BaseEvent, Market, Outcome
from core.settings import settings
from core.logger import observe_api_call
from datetime import datetime

logger = logging.getLogger("ingestion.odds_api")

class OddsAPIIngestor(BaseIngestor):
    """
    Concrete ingestor for fetching sports data from an Odds API.
    Uses httpx and asyncio for non-blocking network I/O.
    """
    def __init__(self):
        self.api_key = settings.api_key
        # Example API endpoint - adjust as needed based on the actual Odds API you use
        self.base_url = "https://api.the-odds-api.com/v4/sports/upcoming/odds"

    @observe_api_call
    async def fetch_data(self) -> List[Dict[str, Any]]:
        """
        Fetches upcoming odds from the API.
        """
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "decimal"
        }

        async with httpx.AsyncClient() as client:
            logger.info(f"Fetching data from Odds API...")
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data

    def normalize(self, raw_data: Dict[str, Any]) -> BaseEvent:
        """
        Normalizes a single event payload into the BaseEvent Pydantic model.
        Includes nested structures (Markets, Outcomes).
        """
        markets_list = []

        # In a real OddsAPI response, "bookmakers" contains the markets
        bookmakers = raw_data.get("bookmakers", [])
        for bookmaker in bookmakers:
            for market in bookmaker.get("markets", []):
                outcomes_list = []
                for outcome in market.get("outcomes", []):
                    outcomes_list.append(Outcome(
                        name=outcome.get("name"),
                        price=outcome.get("price"),
                        point=outcome.get("point")
                    ))

                # We use the bookmaker's last_update for the market
                last_update_str = bookmaker.get("last_update")
                # Handle ISO formatting that might contain Z
                if last_update_str and isinstance(last_update_str, str) and last_update_str.endswith('Z'):
                    last_update_str = last_update_str[:-1] + '+00:00'
                last_update = datetime.fromisoformat(last_update_str) if last_update_str else datetime.utcnow()

                markets_list.append(Market(
                    key=f"{bookmaker.get('key')}_{market.get('key')}",
                    last_update=last_update,
                    outcomes=outcomes_list
                ))

        # Parse commence time
        commence_time_str = raw_data.get("commence_time")
        if commence_time_str and isinstance(commence_time_str, str) and commence_time_str.endswith('Z'):
            commence_time_str = commence_time_str[:-1] + '+00:00'
        commence_time = datetime.fromisoformat(commence_time_str) if commence_time_str else datetime.utcnow()

        event = BaseEvent(
            id=raw_data.get("id"),
            sport_key=raw_data.get("sport_key"),
            sport_title=raw_data.get("sport_title", "Unknown"),
            commence_time=commence_time,
            home_team=raw_data.get("home_team"),
            away_team=raw_data.get("away_team"),
            markets=markets_list
        )
        return event
