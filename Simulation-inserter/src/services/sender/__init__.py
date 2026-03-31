from .mqtt import MQTTSender
from src.settings import settings


mqtt_sender = MQTTSender(
    mqtt_settings=settings.mqtt
)
