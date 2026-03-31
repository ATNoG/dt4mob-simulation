import logging

from typing import Literal, Optional
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)

from src.settings.simulator import SimulatorSettings
from src.settings.sender import MQTTSenderSettings
from src.settings.ditto import DittoSettings

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

class Settings(BaseSettings):

    log_level: LogLevel = Field(validation_alias="log_level",default="INFO")

    ca_cert: Optional[str] = Field(validation_alias="ca_cert",default=None)
    sumo: SimulatorSettings = SimulatorSettings()
    mqtt: MQTTSenderSettings = MQTTSenderSettings()
    ditto: DittoSettings = DittoSettings()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

logging.basicConfig(level=settings.log_level)

logging.debug(settings)