from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class Outcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    price: float
    point: Optional[float] = None

class Market(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    last_update: datetime
    outcomes: List[Outcome] = Field(default_factory=list)

class BaseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    sport_key: str
    sport_title: str
    commence_time: datetime
    home_team: str
    away_team: str
    markets: List[Market] = Field(default_factory=list)
