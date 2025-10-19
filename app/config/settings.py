from pydantic import BaseModel
import os

class Settings(BaseModel):
    ENV: str = os.getenv("ENV", "dev")
    DISCORD_WEBHOOK: str | None = os.getenv("DISCORD_WEBHOOK")

settings = Settings()
