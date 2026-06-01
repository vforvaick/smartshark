from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./smartshark.db"
    secret_key: str = "change-me-in-production-use-a-long-random-key"
    access_token_expire_minutes: int = 60 * 8  # 8 hours
    admin_default_password: str = "admin"
    capture_storage_path: Path = Path("./captures")

    model_config = {"env_prefix": "SMARTSHARK_"}


def get_settings() -> Settings:
    return Settings()
