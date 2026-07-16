from .mqtt_client import MqttClient

from src.settings import settings
from src.services.certificate import certificate_service


def _new_instance() -> MqttClient:
    return MqttClient(mqtt_settings=settings.mqtt, cert_service=certificate_service)


mqtt_client: MqttClient = _new_instance()
