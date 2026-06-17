from abc import ABC, abstractmethod
from typing import Any, List
from models.events import BaseEvent

class BaseIngestor(ABC):
    """
    Abstract BaseIngestor class defining the contract for data ingestion.
    """

    @abstractmethod
    async def fetch_data(self) -> List[Any]:
        """
        Fetches raw data from the data source.
        Must be implemented by concrete classes.
        """
        pass

    @abstractmethod
    def normalize(self, raw_data: Any) -> BaseEvent:
        """
        Normalizes and validates raw data into a Pydantic BaseEvent model.
        Must be implemented by concrete classes.
        """
        pass
