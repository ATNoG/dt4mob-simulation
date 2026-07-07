import json
import asyncio
import logging
import ssl

import httpx
import websockets.exceptions
from websockets.asyncio.client import connect as ws_connect

from src.settings.ditto import DittoSettings
from src.services.auth import AuthenticationService


class DittoConnectionError(Exception):
    """Exception for websocket error"""
    pass


class DittoClient:
    def __init__(
        self,
        client: httpx.Client,
        auth_service: AuthenticationService,
        ditto_settings: DittoSettings,
    ):
        self._ws = None
        self._client = client
        self._auth_service = auth_service
        self._ditto_settings = ditto_settings

        self._search_things_url = ditto_settings.get_base_url() + "/search/things"
        self._things_url = ditto_settings.get_base_url() + "/things"
        self._responses = {}
        
        # NEW: Bounded event queue to absorb raw websocket message streams
        self._message_queue = asyncio.Queue(maxsize=5000)
        self._listen_task = None
        self._refresh_task = None
        self._consumer_task = None
        self._reconnect_task = None
        self._running = False

    async def _get_auth_header(self) -> str:
        token = await self._auth_service.get_token()
        return f"Bearer {token}"

    async def connect(self):
        self._running = True
        uri = self._ditto_settings.get_base_ws()
        logging.debug(f"URI Target: {uri}")
        auth_header = await self._get_auth_header()
        
        ssl_context = None
        if uri.startswith("wss://"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        try:
            self._ws = await ws_connect(
                uri, additional_headers={"Authorization": auth_header}, ssl=ssl_context
            )
        except Exception as e:
            self._ws = None
            raise DittoConnectionError(f"Failed to connect to {uri}: {e}")

        logging.info(f"Connected to ditto at {uri}")
        
        self._listen_task = asyncio.create_task(self.listen_loop())
        self._consumer_task = asyncio.create_task(self._message_consumer_worker())

        await self.send_control_message("START-SEND-MESSAGES")

        self._refresh_task = asyncio.create_task(self._token_refresh_loop())

        if not self._reconnect_task or self._reconnect_task.done():
            self._reconnect_task = asyncio.create_task(self._reconnect_loop())

    async def _token_refresh_loop(self):
        """Background task that maintains the WebSocket authorization state without blocking."""
        logging.info("Starting background WebSocket token lifecycle supervisor.")
        try:
            while self._running:
                if self._ws is None:
                    await asyncio.sleep(1)
                    continue

                time_left = self._auth_service.seconds_until_expiration()

                buffer_time = 10.0
                sleep_interval = time_left - buffer_time

                if sleep_interval > 0:
                    logging.debug(
                        f"Token has {time_left:.1f}s left. Supervisor sleeping for {sleep_interval:.1f}s"
                    )
                    await asyncio.sleep(sleep_interval)
                else:
                    logging.warning(
                        f"Token expiring imminently ({time_left:.1f}s left). Skipping sleep interval."
                    )

                logging.info("Refreshing token...")
                try:
                    fresh_token = await self._auth_service.refresh()
                except Exception as e:
                    logging.error(f"Keycloak token refresh failed: {e}", exc_info=True)
                    await asyncio.sleep(5)
                    continue

                logging.info("Sending JWT-TOKEN control message...")
                try:
                    await self._ws.send(f"JWT-TOKEN?jwtToken={fresh_token}")
                    logging.info("JWT-TOKEN sent successfully")
                except Exception as e:
                    logging.error(
                        f"JWT-TOKEN send failed: {type(e).__name__}: {e}",
                        exc_info=True,
                    )

        except asyncio.CancelledError:
            logging.debug("Token supervisor loop task cleanly cancelled.")

    async def _reconnect_loop(self):
        """Background task that reconnects the WebSocket when it drops unexpectedly."""
        delay = 1.0
        max_delay = 30.0
        attempt = 0
        while self._running:
            if self._ws is None:
                attempt += 1
                logging.warning(
                    f"WebSocket disconnected. Reconnect attempt #{attempt} in {delay:.0f}s..."
                )
                await asyncio.sleep(delay)
                if not self._running:
                    break
                try:
                    await self.connect()
                    logging.info(
                        f"Reconnection successful after {attempt} attempt(s)"
                    )
                    delay = 1.0
                    attempt = 0
                except Exception as e:
                    logging.error(
                        f"Reconnect attempt #{attempt} failed: {type(e).__name__}: {e}",
                        exc_info=True,
                    )
                    delay = min(delay * 2, max_delay)
            else:
                await asyncio.sleep(1)

    async def listen_loop(self):
        """Fast Producer loop. Extracts messages from network buffers instantly."""
        if self._ws is None:
            raise DittoConnectionError("No Websocket connection available.")

        try:
            async for message in self._ws:
                if isinstance(message, str) and message.endswith(":ACK"):
                    future = self._responses.pop(message, None)
                    if future and not future.done():
                        future.set_result(True)
                    continue

                try:
                    self._message_queue.put_nowait(message)
                except asyncio.QueueFull:
                    logging.warning("Internal message queue flooded! Dropping oldest frame to preserve buffer health.")
                    self._message_queue.get_nowait()
                    self._message_queue.put_nowait(message)

        except websockets.exceptions.ConnectionClosed as e:
            logging.error(
                f"WebSocket closed by server: code={e.code}, reason={e.reason}"
            )
        except Exception as e:
            logging.error(
                f"WebSocket listen loop failed: {type(e).__name__}: {e}",
                exc_info=True,
            )
        finally:
            logging.warning("WebSocket network reader dropped out. Clearing handlers.")
            current = asyncio.current_task()
            to_cancel = []
            for t in [self._refresh_task, self._consumer_task]:
                if t and t is not current and not t.done():
                    t.cancel()
                    to_cancel.append(t)
            if to_cancel:
                await asyncio.gather(*to_cancel, return_exceptions=True)
            await self._close_connection()

    async def _message_consumer_worker(self):
        """Dedicated consumer worker loop. Processes message data at application speed."""
        logging.info("Starting message consumer worker pipeline.")
        while True:
            try:
                message = await self._message_queue.get()
                
                try:
                    data = json.loads(message)
                except (json.JSONDecodeError, TypeError) as e:
                    logging.warning(f"Received malformed frame: {e}")
                    self._message_queue.task_done()
                    continue

                corr_id = data.get("headers", {}).get("correlation-id")
                if corr_id and corr_id in self._responses:
                    future = self._responses.pop(corr_id, None)
                    if future and not future.done():
                        future.set_result(data)
                    self._message_queue.task_done()
                    continue

                # Core Application Processing Logic Execution Context
                logging.info(f"Processing streamed event topic: {data.get('topic')}")
                logging.debug(f"Current backpressure queue depth: {self._message_queue.qsize()}")
                
                # Yield control briefly to ensure event-loop balance
                await asyncio.sleep(0)
                self._message_queue.task_done()

            except asyncio.CancelledError:
                logging.debug("Consumer worker task cleanly cancelled.")
                break
            except Exception as e:
                logging.error(f"Error while processing consumer pipeline frame: {e}", exc_info=True)

    async def _close_connection(self):
        """Close WS and clean up orphaned futures. Does NOT cancel tasks."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

        await asyncio.sleep(0)

        for future in self._responses.values():
            if not future.done():
                future.cancel()
        self._responses.clear()

    async def close(self):
        """Full shutdown — stops reconnection loop too."""
        self._running = False
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except Exception:
                pass

        current = asyncio.current_task()
        to_cancel = []
        for t in [self._listen_task, self._refresh_task, self._consumer_task]:
            if t and t is not current and not t.done():
                t.cancel()
                to_cancel.append(t)
        if to_cancel:
            await asyncio.gather(*to_cancel, return_exceptions=True)

        await self._close_connection()

    async def send_control_message(self, command: str, timeout: float = 20.0) -> bool:
        if not self._ws:
            raise DittoConnectionError("Websocket is not connected")

        base_command = command.split('?')[0]
        expected_ack = f"{base_command}:ACK"

        ack_future = asyncio.get_running_loop().create_future()
        self._responses[expected_ack] = ack_future

        try:
            logging.debug(f"Sending Ditto control command: {command}")
            await self._ws.send(command)
            
            await asyncio.wait_for(ack_future, timeout=timeout)
            logging.info(f"Successfully subscribed via control command: {base_command}")
            return True

        except asyncio.TimeoutError:
            logging.error(f"Timeout waiting for control ACK: {expected_ack}")
            return False
        finally:
            self._responses.pop(expected_ack, None)

    async def send_envelope(self, envelope_str: str):
        if not self._ws:
            raise DittoConnectionError("Websocket is not connected")
            
        try:
            logging.debug("Streaming envelope frame over WebSocket...")
            await self._ws.send(envelope_str)
            logging.debug("Envelope pushed into network buffer successfully.")
        except Exception as e:
            logging.error(f"Failed to stream envelope string: {e}")
            raise DittoConnectionError(e)