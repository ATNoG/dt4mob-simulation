import logging

from typing import Literal
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)

from src.settings.auth import AuthSettings
from src.settings.simulator import SimulatorSettings
from src.settings.ditto import DittoSettings
from src.settings.mqtt import MqttSettings
from src.settings.certificate import CertificateSettings

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

class Settings(BaseSettings):

    log_level: LogLevel = Field(validation_alias="log_level",default="INFO")
    transport: Literal["ws", "mqtt"] = "ws"

    sumo: SimulatorSettings = SimulatorSettings.model_construct()
    auth: AuthSettings = AuthSettings.model_construct()
    ditto: DittoSettings = DittoSettings.model_construct()
    mqtt: MqttSettings = MqttSettings.model_construct()
    certificate: CertificateSettings = CertificateSettings.model_construct()
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )


settings = Settings()

logging.basicConfig(level=settings.log_level)
logging.debug(settings)