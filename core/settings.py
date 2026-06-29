from pydantic_settings import BaseSettings
import json
import os

class Settings(BaseSettings):
    polling_interval: int = 60
    database_url: str = "sqlite+aiosqlite:///sports_data.db"
    database_file: str = "sports_data.db"

    @property
    def api_key(self) -> str:
        secrets_path = r"C:\Dev\Projects\ag-workspace\secrets.json"
        try:
            with open(secrets_path, "r") as f:
                secrets = json.load(f)
                return secrets.get("odds_api_key", "missing_key")
        except FileNotFoundError:
            return "local_dev_key" # Fallback for sandbox

settings = Settings()
