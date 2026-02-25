"""
Settings management using Pydantic Settings.
Unified configuration from environment variables.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, ConfigDict


class Settings(BaseSettings):
    # Telegram
    BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TG_LOG_GROUP: Optional[str] = None
    TG_PAYMENT_GROUP: Optional[str] = None
    TG_REFERRAL_GROUP: Optional[str] = None
    TG_SECURITY_GROUP: Optional[str] = None

    # Database
    DATABASE_URL: str = "sqlite:///./test.db"
    TON_NETWORK: str = "testnet"
    MANH_PRICE_ILS: float = 5.2
    TON_ILS_MANUAL: str = "5.2"
    MIN_WITHDRAWAL: float = 0.000001

    # Admin
    ADMIN_IDS: List[int] = []

    @field_validator("ADMIN_IDS", mode="before")
    def parse_admin_ids(cls, v):
        # If it's already a list, return as is (after converting each item to int)
        if isinstance(v, list):
            return [int(x) for x in v]
        # If it's a single integer, wrap it in a list
        if isinstance(v, int):
            return [v]
        # If it's a string, split by commas and convert each to int
        if isinstance(v, str):
            # Remove brackets if present (sometimes env vars include [])
            v = v.strip().strip('[]')
            if not v:
                return []
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        # Fallback: return empty list
        return []

    # Build info
    APP_BUILD_STAMP: str = ""
    RAILWAY_GIT_COMMIT_SHA: str = ""
    LOG_LEVEL: str = "INFO"

    model_config = ConfigDict(env_file=".env", case_sensitive=True, extra="allow")


settings = Settings()
