"""
Settings management using Pydantic Settings.
Unified configuration from environment variables.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TG_LOG_GROUP: Optional[str] = None
    TG_PAYMENT_GROUP: Optional[str] = None
    TG_REFERRAL_GROUP: Optional[str] = None
    TG_SECURITY_GROUP: Optional[str] = None
    DATABASE_URL: str = "sqlite:///./test.db"
    TON_TREASURY_ADDRESS: str = ""
    TON_API_KEY: str = ""
    TON_NETWORK: str = "testnet"
    TONCENTER_BASE_URL: str = "https://toncenter.com/api/v2"
    TON_PAYMENT_PROVIDER: str = "manual"
    MANH_PRICE_ILS: float = 5.2
    TON_ILS_MANUAL: str = "5.2"
    MIN_WITHDRAWAL: float = 0.000001
    ADMIN_IDS: List[int] = []

    @field_validator("ADMIN_IDS", mode="before")
    def parse_admin_ids(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        return v

    APP_BUILD_STAMP: str = ""
    RAILWAY_GIT_COMMIT_SHA: str = ""
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
