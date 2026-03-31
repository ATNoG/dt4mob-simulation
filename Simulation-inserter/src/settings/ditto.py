from pydantic import Field

from pydantic_settings import BaseSettings, SettingsConfigDict


class DittoSettings(BaseSettings):
    ttl_traci_car: int = Field(
        default=2,
        ge=0,
        validation_alias="ditto_ttl_traci_car"
    )
    traci_namespace: str = Field(
        default="traci", 
        validation_alias="ditto_traci_namespace"
    )
    traci_policy_id: str = Field(
        default="traciCar:policy", 
        validation_alias="ditto_traci_policy_id"
    )
    traci_prefix: str = Field(
        default="Car-", 
        validation_alias="ditto_traci_prefix"
    )
    
    api_url: str = Field(
        default="localhost:8080", 
        validation_alias="ditto_api_url"
    )
    base_api_path: str = Field(
        default="/api/2", 
        validation_alias="ditto_base_api_path"
    )
    
    # Credentials
    dev_ops_username: str = Field(
        default="devops", 
        validation_alias="ditto_dev_ops_username"
    )
    
    main_auth_username: str = Field(
        default="ditto", 
        validation_alias="ditto_main_auth_username"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    def get_base_url(self) -> str:
        base_url = "http://" + self.api_url
        stripped_url = base_url.rstrip("/")
        stripped_base_path = self.base_api_path.strip("/")
        return f"{stripped_url}/{stripped_base_path}"

    def with_prefix(self, object_id: int | str) -> str:
        return f"{self.traci_prefix}{object_id}"