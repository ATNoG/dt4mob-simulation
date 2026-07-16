from amqtt.errors import ClientError, AMQTTError
import asyncio
import logging
from asyncio import Task

from amqtt.client import ClientConfig, MQTTClient
from amqtt.contexts import ConnectionConfig

from src.settings.mqtt import MqttSettings


class MqttConnectionError(Exception):
    """Exception for MQTT connection errors"""
    pass


class MqttClient:
    def __init__(self, mqtt_settings: MqttSettings, cert_service=None):
        self._settings = mqtt_settings
        self._reconnect_task: Task | None = None
        self._certfile: str | None = None
        self._keyfile: str | None = None
        self._cert_service = cert_service
        self._reconnect_lock = asyncio.Lock()

    def _build_client(self) -> MQTTClient:
        logging.debug(f"Building MQTT client with URI: {self._settings.get_uri()}")
        logging.debug(f"MQTT TLS settings: cafile={self._settings.cafile}, certfile={self._certfile}, keyfile={self._keyfile}")
        return MQTTClient(
            config=ClientConfig(
                reconnect_retries=-1,
                connection=ConnectionConfig(
                    uri=self._settings.get_uri(),
                    cafile=self._settings.cafile,
                    certfile=self._certfile,
                    keyfile=self._keyfile,
                ),
            ),
        )

    def set_tls(self, certfile: str, keyfile: str) -> None:
        self._certfile = certfile
        self._keyfile = keyfile
        logging.info(f"TLS material updated: cert={certfile}")

    async def _force_reconnect(self) -> None:
        """Forcibly disconnects and reconnects the client safely."""
        async with self._reconnect_lock:
            logging.warning("Initiating forced MQTT reconnection due to publish failure...")
            try:
                # 1. Gracefully try to disconnect the old instance if possible
                try:
                    await asyncio.wait_for(self.mqttc.disconnect(), timeout=3.0)
                except Exception:
                    logging.debug("Forced disconnect timeout or error (expected during zombie states)")

                # 2. Check if a cert reissue is required while we are at it
                if self._cert_service and self._cert_service.needs_reissue():
                    logging.info("Certificate expiring during forced reconnect, reissuing...")
                    cert_path, key_path = await self._cert_service.issue()
                    self.set_tls(cert_path, key_path)

                # 3. Build a fresh client instance to clear internal amqtt backpressure states
                self.mqttc = self._build_client()
                await self.mqttc.connect()
                logging.info("Successfully re-established MQTT connection.")
            except Exception as e:
                logging.error(f"Forced reconnection failed: {e}. Will retry in the background loop.")
                # We don't raise here, letting the background loop attempt to heal it later

    async def _reconnect_loop(self):
        while True:
            await asyncio.sleep(self._settings.reconnect_interval)
            logging.debug("MQTT manual reconnection attempt")
            try:
                if self._cert_service and self._cert_service.needs_reissue():
                    logging.info("Certificate expiring, reissuing...")
                    cert_path, key_path = await self._cert_service.issue()
                    self.set_tls(cert_path, key_path)
                    self.mqttc = self._build_client()

                    async with self._reconnect_lock:
                        await self.mqttc.disconnect()
                        self.mqttc = self._build_client()
                        await self.mqttc.connect()
            except Exception as e:
                logging.warning(f"MQTT reconnect failed: {e}")

    async def start(self) -> None:
        self.mqttc = self._build_client()
        uri = self._settings.get_uri()
        try:
            await self.mqttc.connect()
        except Exception as e:
            raise MqttConnectionError(
                f"Failed to connect to MQTT broker at {uri}: {e}"
            )
        logging.info(f"Connected to MQTT broker at {uri}")
        self._reconnect_task = asyncio.create_task(
            self._reconnect_loop()
        )

    async def stop(self) -> None:
        if self._reconnect_task:
            self._reconnect_task.cancel()
            self._reconnect_task = None
        await self.mqttc.disconnect()
        logging.info("MQTT client disconnected")

    async def publish(self, envelope_str: str, qos: int | None = None):
            try:
                payload = envelope_str.encode("utf-8")
                await self.mqttc.publish(
                    self._settings.topic,
                    payload,
                    qos=qos,
                )
                logging.debug(f"Published message to {self._settings.topic} (qos={qos})")
            except (ClientError, AMQTTError, asyncio.TimeoutError) as e:
                logging.error(f"Failed to publish MQTT message (Timeout/Error): {e}")
                
                # Spin up the background task to reset the zombie connection
                asyncio.create_task(self._force_reconnect())
                
                raise MqttConnectionError(f"Publish failed, connection designated as unstable: {e}")
            except Exception as e:
                # Catch-all for any other unexpected system errors
                logging.error(f"Unexpected error during MQTT publish: {e}")
                raise
