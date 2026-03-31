from enum import Enum
from typing import Annotated, Any, Dict, Literal

from pydantic import BaseModel, Field


class VehicleMessageType(str, Enum):
    DATA = "data"
    DELETE = "delete"
    CREATE = "create"
    EXPIRACY = "expiracy"



class BaseVehicleMessage(BaseModel):
    pass


class VehicleDataMessage(BaseVehicleMessage):
    msg_type: Literal[VehicleMessageType.DATA] = VehicleMessageType.DATA
    id: str
    extra: Dict[str, Any]

class VehicleDeleteMessage(BaseVehicleMessage):
    msg_type: Literal[VehicleMessageType.DELETE] = VehicleMessageType.DELETE
    id: str

class VehicleCreateMessage(BaseVehicleMessage):
    msg_type: Literal[VehicleMessageType.CREATE] = VehicleMessageType.CREATE
    id: str
    length: float
    width: float
    height: float
    vehicle_Type: str



type VehicleMessage = Annotated[
    VehicleDataMessage
    | VehicleDeleteMessage
    | VehicleCreateMessage,
    Field(discriminator="msg_type"),
]