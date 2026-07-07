from pydantic import BaseModel

class SimulatorSettings(BaseModel):
    config_file: str = ".sumocfg"
    zoom_level: int = 18