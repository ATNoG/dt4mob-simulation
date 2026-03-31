from typing import Annotated, Optional
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MQTTSenderSettings(BaseSettings):

    host: Annotated[str, Field(
        min_length=1, 
        validation_alias="mqtt_host"
    )] = "localhost"
    
    port: Annotated[int, Field(
        ge=0, le=65535, 
        validation_alias="mqtt_port"
    )] = 1883

    # Credentials
    username: Optional[str] = Field(
        default=None, 
        validation_alias="mqtt_username"
    )
    password: Optional[SecretStr] = Field(
        default=None, 
        validation_alias="mqtt_password"
    )

    tls: bool = Field(
        default=False, 
        validation_alias="mqtt_tls"
    )

    publish_topic: str = Field(
        default="telemetry", 
        validation_alias="mqtt_publish_topic"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_uri(self) -> str:
        url = ["mqtt"]

        if self.tls:
            url.append("s")

        url.append("://")

        if self.username and self.password:
            url.append(f"{self.username}:{self.password.get_secret_value()}@")

        url.append(f"{self.host}:{self.port}")
        return "".join(url)