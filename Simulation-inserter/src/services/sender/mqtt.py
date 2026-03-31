import ssl
import asyncio
import logging

from gmqtt import Client as MQTTClient

from src.settings import settings
from src.settings.sender import MQTTSenderSettings


class MQTTSender:
    def __init__(self, mqtt_settings :MQTTSenderSettings):
        self._client = MQTTClient(client_id="sim-producer")
        self._settings = mqtt_settings
        self._connected = asyncio.Event()

    def _on_connect(self, client, flags, rc, properties):
        logging.info(f"Connected with result code: {rc}")
        self._connected.set()

    def _on_disconnect(self, client, packet, exc=None):
        logging.warning("MQTT Disconnected")
        self._connected.clear()

    async def connect(self):
        ssl_context = None
        if self._settings.tls:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            if settings.ca_cert:
                ssl_context.load_verify_locations(settings.ca_cert)
            # TODO
            ssl_context.check_hostname = False 

        if self._settings.username and self._settings.password:
            self._client.set_auth_credentials(
                self._settings.username, 
                self._settings.password.get_secret_value()
            )

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect

        try:
            await self._client.connect(
                host=self._settings.host,
                port=self._settings.port,
                ssl=ssl_context,
                keepalive=60
            )

            await asyncio.wait_for(self._connected.wait(), timeout=20.0)
        except Exception as e:
            logging.error(f"Failed to connect to {self._settings.host}: {e}")
            raise

    async def disconnect(self):
        await self._client.disconnect()

    async def send(self, payload: bytes):
        self._client.publish("telemetry", payload, qos=0)

        await asyncio.sleep(0)
