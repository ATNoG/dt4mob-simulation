from enum import Enum
from pydantic import BaseModel

class VType(Enum):
    CAR = "car"
    BUS = "bus"
    TRUCK = "truck"
    LORRY = "lorry"
    MOTORBIKE = "motorbike"
    VAN = "van"
    CAR_WITH_TRAILER = "car_with_trailer"
    LORRY_WITH_TRAILER = "lorry_with_trailer"
    
class TraciVehicle(BaseModel):
    id: str
    length: float
    height: float
    width: float
    vehicle_Type: VType
    accel: float
    speed: float
    angle: float
    latitude: float = 0
    longitude: float = 0
    quadkey: int = 0