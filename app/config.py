from functools import lru_cache
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    database_url: str = "mysql+pymysql://root:101704@localhost:3306/asset_management?charset=utf8mb4"
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    app_title: str = "企业资产管理后台系统"
    app_version: str = "1.0.0"
    debug: bool = True

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.secret_key == "your-super-secret-key-change-in-production":
        logger.warning("SECURITY: secret_key 使用默认值，请在 .env 中设置 SECRET_KEY")
    return s