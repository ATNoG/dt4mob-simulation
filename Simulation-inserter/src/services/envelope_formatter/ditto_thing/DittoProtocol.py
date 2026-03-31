import uuid
from datetime import datetime,timedelta

from src.Models.ditto import (
    DittoProtocolEnvelope,
    Headers, 
    BaseEmptyVehicle, 
    VehicleAttributes,
    VehicleFeatures,
    State,
)
from src.Models.vehicle_message import (
    VehicleDataMessage,
    VehicleDeleteMessage,
    VehicleMessage,
    VehicleCreateMessage,
)
from src.settings import settings


class DittoThingEnvelopeFormatter():

    def __init__(self) -> None:
        pass

    def _handle_data(self, data_message: VehicleDataMessage) -> DittoProtocolEnvelope:

        correlation_id = str(uuid.uuid4())
        
        attributes = VehicleAttributes(expiry_ts=self._get_car_expire())
        state = State(properties=data_message.extra)
        features = VehicleFeatures(state=state)
        vehicle = BaseEmptyVehicle(attributes=attributes,features=features)


        update_envelope = DittoProtocolEnvelope(
            topic=f"{settings.ditto.traci_namespace}/{settings.ditto.with_prefix(data_message.id)}/things/twin/commands/merge",
            headers=Headers(correlation_id=correlation_id,content_type="application/merge-patch+json"),
            path="/",
            value=vehicle.model_dump(exclude_none=True,by_alias=True),
        )

        return update_envelope

    def _handle_delete(self, delete_message: VehicleDeleteMessage) -> DittoProtocolEnvelope:
        correlation_id = str(uuid.uuid4())
        return DittoProtocolEnvelope(
                topic=f"{settings.ditto.traci_namespace}/{settings.ditto.with_prefix(delete_message.id)}/things/twin/commands/delete",
                headers=Headers(correlation_id=correlation_id),
                path="/",
            )

    def _handle_create(self, create_message: VehicleCreateMessage) -> DittoProtocolEnvelope:
        correlation_id = str(uuid.uuid4())
        atributes = VehicleAttributes(
            length=create_message.length,
            width=create_message.width,
            height=create_message.height,
            vehicle_Type=create_message.vehicle_Type,
            expiry_ts=self._get_car_expire()
        )
        base = BaseEmptyVehicle(
            policyId=settings.ditto.traci_policy_id,
            attributes=atributes
        )
        return DittoProtocolEnvelope(
            topic=f"{settings.ditto.traci_namespace}/{settings.ditto.with_prefix(create_message.id)}/things/twin/commands/create",
            headers=Headers(correlation_id=correlation_id),
            path="/",
            value= base.model_dump(),
        )
    
    def _get_car_expire(self) -> str:
        expire = datetime.now() + timedelta(minutes=settings.ditto.ttl_traci_car)
        return expire.isoformat()

    def format(self, vehicle_message: VehicleMessage) -> DittoProtocolEnvelope:
        match vehicle_message:
            case VehicleDataMessage():
                return self._handle_data(vehicle_message)
            case VehicleDeleteMessage():
                return self._handle_delete(vehicle_message)
            case VehicleCreateMessage():
                return self._handle_create(vehicle_message)