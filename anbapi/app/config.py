from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    ENV_STATE: Optional[str] = "DEV"
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )


class GlobalConfig(BaseConfig):
    DATABASE_URL: Optional[str] = None
    DB_FORCE_ROLL_BACK: bool = False
    RABBIT_URL: Optional[str] = None
    ACCESS_TOKEN_EXPIRE_MINUTES: Optional[int] = None
    SECRET_KEY: Optional[str] = None
    UPLOAD_DIR: Optional[str] = "/data/uploads"
    PROCESSED_DIR: Optional[str] = "/data/processed"
    INTRO_SECONDS: Optional[float] = 2.5
    OUTRO_SECONDS: Optional[float] = 2.5
    ASSETS_DIR: Optional[str] = "/assets"


class DevConfig(GlobalConfig):
    pass


class ProdConfig(GlobalConfig):
    pass


class TestConfig(GlobalConfig):
    DB_FORCE_ROLL_BACK: bool = True


@lru_cache
def get_config(env_state: str):
    configs = {"DEV": DevConfig, "PROD": ProdConfig, "TEST": TestConfig}
    return configs[env_state]()


config = get_config(BaseConfig().ENV_STATE or "DEV")
