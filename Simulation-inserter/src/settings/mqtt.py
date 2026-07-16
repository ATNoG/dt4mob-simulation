from pydantic import BaseModel


class MqttSettings(BaseModel):
    host: str = "localhost"
    port: int = 1883
    topic: str = "ditto/commands"
    tls: bool = False
    cafile: str | None = None

    device: str | None = None
    tenant: str | None = None
    password: str | None = None

    qos: int = 1
    qos_map: dict[str, int] = {"create": 1, "data": 0, "delete": 1}
    reconnect_interval: int = 150

    @property
    def username(self) -> str | None:
        if self.device and self.tenant:
            return f"{self.device}@{self.tenant}"

    def get_uri(self) -> str:
        uri: list[str] = ["mqtts://"]
        if self.username is not None:
            uri.append(self.username)
            if self.password is not None:
                uri.append(f":{self.password}")
            uri.append("@")

        uri.append(self.host)
        if self.port is not None:
            uri.append(f":{self.port}")

        return "".join(uri)