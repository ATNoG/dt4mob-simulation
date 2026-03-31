from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class SimulatorSettings(BaseSettings):
    config_file: str = Field(default=".sumocfg",validation_alias="sumo_config_file")
    zoom_level: int = Field(default=18, validation_alias="geotiles_zoom_level")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )