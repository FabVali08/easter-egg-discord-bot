from pydantic_settings import BaseSettings
from typing import ClassVar

class Settings(BaseSettings):
    TOKEN: str = "DISCORD_BOT_TOKEN"
    
settings = Settings()
