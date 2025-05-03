from pydantic_settings import BaseSettings
from typing import ClassVar

class Settings(BaseSettings):
    TOKEN: str = "MTM1NTk4MTY3MDY0NTUwMTk3Mg.GOVmV6.FO9dNZU_EUwW-IXe0W4Q_2dM-i2sSonrciR1vY"
    
settings = Settings()