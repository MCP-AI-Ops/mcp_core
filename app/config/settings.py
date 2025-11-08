# from pydantic import BaseModel
# import os

# class Settings(BaseModel):
#     ENV: str = os.getenv("ENV", "dev")
#     DISCORD_WEBHOOK: str | None = os.getenv("DISCORD_WEBHOOK")

# settings = Settings()

# app/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl
from typing import Optional

class Settings(BaseSettings):
    # 일반
    ENV: str = "dev"
    LOG_LEVEL: str = "INFO"

    # MCP 모델 서버
    MCP_URL: AnyHttpUrl = "http://localhost:8000/estimate"

    # OpenStack
    OS_AUTH_URL: AnyHttpUrl = "http://172.32.0.244:5000/v3"
    OS_USERNAME: str = "admin"
    OS_PASSWORD: str
    OS_USER_DOMAIN_NAME: str = "Default"
    OS_PROJECT_NAME: str = "admin"
    OS_PROJECT_DOMAIN_NAME: str = "Default"
    OS_REGION_NAME: str = "RegionOne"
    OS_PUBLIC_NETWORK: str = "public"
    OS_PRIVATE_NETWORK: str = "private"
    OS_IMAGE_ID: str  # Glance 이미지 ID (Ubuntu cloud 등)
    OS_SSH_KEYPAIR: str = "mcp-key"

    # DB (선택)
    DB_URL: Optional[str] = None

    # 알림(선택)
    DISCORD_WEBHOOK: Optional[AnyHttpUrl] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
