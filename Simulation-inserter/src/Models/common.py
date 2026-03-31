from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat

Latitude = Annotated[float, Field(ge=-90.0, le=90.0)]

Longitude = Annotated[float, Field(ge=-180.0, le=180.0)]


class LocalCoordinates(BaseModel):
    x: float
    y: float


class GlobalCoordinates(BaseModel):
    latitude: Latitude
    longitude: Longitude


class Dimensions(BaseModel):
    width: PositiveFloat
    length: PositiveFloat
    height: PositiveFloat


class Empty(BaseModel):
    model_config = ConfigDict(extra="forbid")
