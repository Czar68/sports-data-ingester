from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    api_key: str = "your_api_key_here"
    polling_interval: int = 60
    database_url: str = "sqlite+aiosqlite:///sports_data.db"
    database_file: str = "sports_data.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
