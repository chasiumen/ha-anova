"""WebSocket client for Anova Precision Cooker communication."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import websockets
from websockets.asyncio.client import ClientConnection

_LOGGER = logging.getLogger(__name__)

WS_URL = "wss://devices.anovaculinary.io"
SUPPORTED_ACCESSORIES = "APC"
RECONNECT_BACKOFF_BASE = 1
RECONNECT_BACKOFF_MAX = 60
DISCOVERY_TIMEOUT = 10
RECEIVE_TIMEOUT = 30


@dataclass
class AnovaDevice:
    """Represents a discovered Anova device."""

    cooker_id: str
    name: str
    device_type: str


@dataclass
class AnovaDeviceState:
    """Current state of an Anova Precision Cooker."""

    is_cooking: bool = False
    target_temperature: float | None = None
    water_temperature: float | None = None
    heater_temperature: float | None = None
    triac_temperature: float | None = None
    cook_time: int | None = None
    cook_time_remaining: int | None = None
    mode: str | None = None
    state: str | None = None


class AnovaSousVideClient:
    """WebSocket client for Anova Precision Cooker."""

    def __init__(self) -> None:
        """Initialize the client."""
        self._ws: ClientConnection | None = None
        self._pat: str | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._state: dict[str, AnovaDeviceState] = {}
        self._state_callbacks: list[Callable[[str, AnovaDeviceState], None]] = []
        self._discovery_event: asyncio.Event = asyncio.Event()
        self._discovered_devices: list[AnovaDevice] = []
        self._connected: bool = False
        self._should_reconnect: bool = True

    @property
    def connected(self) -> bool:
        """Return whether the client is connected."""
        return self._connected

    @property
    def discovered_devices(self) -> list[AnovaDevice]:
        """Return discovered devices."""
        return self._discovered_devices

    def get_state(self, cooker_id: str) -> AnovaDeviceState:
        """Get the current state for a device."""
        return self._state.get(cooker_id, AnovaDeviceState())

    def add_state_callback(
        self, callback: Callable[[str, AnovaDeviceState], None]
    ) -> Callable[[], None]:
        """Register a callback for state updates. Returns a callable to remove it."""
        self._state_callbacks.append(callback)

        def remove() -> None:
            self._state_callbacks.remove(callback)

        return remove

    async def connect(self, pat: str) -> None:
        """Connect to the Anova WebSocket and start listening."""
        self._pat = pat
        self._should_reconnect = True
        await self._connect()

    async def _connect(self) -> None:
        """Establish the WebSocket connection."""
        uri = f"{WS_URL}?token={self._pat}&supportedAccessories={SUPPORTED_ACCESSORIES}"
        self._ws = await websockets.connect(uri)
        self._connected = True
        _LOGGER.debug("Connected to Anova WebSocket")

    async def discover_devices(self) -> list[AnovaDevice]:
        """Wait for device discovery after connecting."""
        self._discovery_event.clear()
        self._discovered_devices.clear()

        # Start listener to capture discovery messages
        self._listener_task = asyncio.create_task(self._listen_loop())

        try:
            await asyncio.wait_for(
                self._discovery_event.wait(), timeout=DISCOVERY_TIMEOUT
            )
        except TimeoutError:
            _LOGGER.warning("Device discovery timed out after %ss", DISCOVERY_TIMEOUT)

        return self._discovered_devices

    async def start_listening(self) -> None:
        """Start the background listener (after config flow discovery is done)."""
        if self._listener_task is None or self._listener_task.done():
            self._listener_task = asyncio.create_task(self._listen_loop())

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket."""
        self._should_reconnect = False
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
            self._ws = None
        self._connected = False
        _LOGGER.debug("Disconnected from Anova WebSocket")

    async def start_cook(
        self,
        cooker_id: str,
        device_type: str,
        target_temp_c: float,
        timer_seconds: int = 0,
    ) -> None:
        """Send CMD_APC_START to begin cooking."""
        command = {
            "command": "CMD_APC_START",
            "requestId": str(uuid.uuid4()),
            "payload": {
                "cookerId": cooker_id,
                "type": device_type,
                "targetTemperature": target_temp_c,
                "unit": "C",
                "timer": timer_seconds,
            },
        }
        await self._send(command)

    async def stop_cook(self, cooker_id: str, device_type: str) -> None:
        """Send CMD_APC_STOP to stop cooking."""
        command = {
            "command": "CMD_APC_STOP",
            "requestId": str(uuid.uuid4()),
            "payload": {
                "cookerId": cooker_id,
                "type": device_type,
            },
        }
        await self._send(command)

    async def _send(self, command: dict[str, Any]) -> None:
        """Send a JSON command over the WebSocket."""
        if not self._ws:
            raise ConnectionError("Not connected to Anova WebSocket")
        payload = json.dumps(command)
        _LOGGER.debug("Sending command: %s", command["command"])
        await self._ws.send(payload)

    async def _listen_loop(self) -> None:
        """Background loop that receives and processes messages."""
        backoff = RECONNECT_BACKOFF_BASE
        while self._should_reconnect:
            try:
                await self._receive_messages()
            except websockets.exceptions.ConnectionClosed:
                self._connected = False
                _LOGGER.warning("WebSocket connection closed")
            except Exception:
                self._connected = False
                _LOGGER.exception("Error in WebSocket listener")

            if not self._should_reconnect:
                break

            _LOGGER.info("Reconnecting in %s seconds", backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, RECONNECT_BACKOFF_MAX)

            try:
                await self._connect()
                backoff = RECONNECT_BACKOFF_BASE
            except Exception:
                _LOGGER.exception("Reconnection failed")

    async def _receive_messages(self) -> None:
        """Receive and process messages until disconnection."""
        assert self._ws is not None
        while True:
            try:
                raw = await asyncio.wait_for(
                    self._ws.recv(), timeout=RECEIVE_TIMEOUT
                )
            except TimeoutError:
                continue

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                _LOGGER.warning("Received non-JSON message: %s", raw[:200])
                continue

            self._handle_message(data)

    def _handle_message(self, data: dict[str, Any]) -> None:
        """Route an incoming message to the appropriate handler."""
        command = data.get("command", "")

        if command == "EVENT_APC_WIFI_LIST":
            self._handle_device_list(data)
        elif command == "EVENT_APC_STATE":
            self._handle_state_update(data)
        elif command.startswith("RESPONSE"):
            _LOGGER.debug("Received response: %s", data)

    def _handle_device_list(self, data: dict[str, Any]) -> None:
        """Process EVENT_APC_WIFI_LIST."""
        payload = data.get("payload", [])
        for device_data in payload:
            cooker_id = device_data.get("cookerId", "")
            if not any(d.cooker_id == cooker_id for d in self._discovered_devices):
                self._discovered_devices.append(
                    AnovaDevice(
                        cooker_id=cooker_id,
                        name=device_data.get("name", "Anova Precision Cooker"),
                        device_type=device_data.get("type", "unknown"),
                    )
                )
        if self._discovered_devices:
            self._discovery_event.set()

    def _handle_state_update(self, data: dict[str, Any]) -> None:
        """Process EVENT_APC_STATE and update device state."""
        payload = data.get("payload", {})
        cooker_id = payload.get("cookerId", "")
        if not cooker_id:
            return

        body = payload.get("state", payload)

        state = AnovaDeviceState(
            is_cooking=body.get("is-cooking", body.get("is_cooking", False)),
            target_temperature=body.get(
                "target-temperature", body.get("target_temperature")
            ),
            water_temperature=body.get(
                "water-temperature", body.get("water_temperature")
            ),
            heater_temperature=body.get(
                "heater-temperature", body.get("heater_temperature")
            ),
            triac_temperature=body.get(
                "triac-temperature", body.get("triac_temperature")
            ),
            cook_time=body.get("cook-time", body.get("cook_time")),
            cook_time_remaining=body.get(
                "cook-time-remaining", body.get("cook_time_remaining")
            ),
            mode=body.get("mode"),
            state=body.get("state"),
        )

        self._state[cooker_id] = state

        for callback in self._state_callbacks:
            try:
                callback(cooker_id, state)
            except Exception:
                _LOGGER.exception("Error in state callback")
