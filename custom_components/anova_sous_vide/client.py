"""WebSocket client for Anova Precision Cooker communication."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    active_stage_mode: str | None = None
    cook_started_timestamp: str | None = None
    online: bool | None = None
    firmware_version: str | None = None
    temperature_unit: str | None = None
    timer_mode: str | None = None
    timer_started_at: str | None = None


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

    async def set_timer(self, cooker_id: str, device_type: str, timer_seconds: int) -> None:
        """Set the cook timer while keeping the current target temperature."""
        state = self._state.get(cooker_id)
        target_temp = state.target_temperature if state and state.target_temperature else 55.0
        await self.start_cook(cooker_id, device_type, target_temp, timer_seconds=timer_seconds)

    async def reset_timer(self, cooker_id: str, device_type: str) -> None:
        """Reset the cook timer by re-sending start with timer=0 at current target temp."""
        await self.set_timer(cooker_id, device_type, 0)

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
        _LOGGER.debug("Received message: command=%s payload_keys=%s", command, list(data.get("payload", {}).keys()) if isinstance(data.get("payload"), dict) else "non-dict")
        _LOGGER.debug("Full message: %s", json.dumps(data)[:2000])

        if command == "EVENT_APC_WIFI_LIST":
            self._handle_device_list(data)
        elif command == "EVENT_APC_STATE":
            self._handle_state_update(data)
        elif command.startswith("RESPONSE"):
            _LOGGER.debug("Received response: %s", data)
        else:
            # Log unhandled commands so we can discover state event names
            _LOGGER.info("Unhandled command: %s", command)

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
        """Process EVENT_APC_STATE and update device state.

        Supports multiple device types:
        - a6/a7: nested structure with nodes.waterTemperatureSensor, state.mode, etc.
        - a3: flat structure with camelCase keys (currentTemperature, targetTemperature, etc.)
        - legacy: flat structure with hyphenated keys (water-temperature, job, job-status, etc.)
        """
        payload = data.get("payload", {})
        cooker_id = payload.get("cookerId", "")
        if not cooker_id:
            return

        device_type = payload.get("type", "")
        body = payload.get("state", {})

        if device_type in ("a6", "a7"):
            state = self._parse_a6_a7_state(body)
        elif device_type == "a3":
            state = self._parse_a3_state(body)
        elif "job" in body:
            state = self._parse_legacy_state(body)
        else:
            _LOGGER.warning(
                "Unknown state format for device type %s: %s",
                device_type,
                list(body.keys()),
            )
            return

        self._state[cooker_id] = state

        for callback in self._state_callbacks:
            try:
                callback(cooker_id, state)
            except Exception:
                _LOGGER.exception("Error in state callback")

    def _parse_a6_a7_state(self, body: dict[str, Any]) -> AnovaDeviceState:
        """Parse a6/a7 state format (Precision Cooker 3.0)."""
        nodes = body.get("nodes", {})
        water_temp_sensor = nodes.get("waterTemperatureSensor", {})
        timer_node = nodes.get("timer", {})
        state_obj = body.get("state", {})
        mode = state_obj.get("mode", "")
        system_info = body.get("systemInfo", {})
        cook = body.get("cook", {})

        timer_mode = timer_node.get("mode", "idle")
        timer_initial = _safe_int(timer_node.get("initial"))
        cook_time_remaining = _calc_timer_remaining(
            timer_mode, timer_initial, timer_node.get("startedAtTimestamp")
        )

        return AnovaDeviceState(
            is_cooking=mode == "cook",
            target_temperature=_safe_float(
                water_temp_sensor.get("setpoint", {}).get("celsius")
            ),
            water_temperature=_safe_float(
                water_temp_sensor.get("current", {}).get("celsius")
            ),
            heater_temperature=None,
            triac_temperature=None,
            cook_time=timer_initial,
            cook_time_remaining=cook_time_remaining,
            mode=mode if mode else None,
            state=None,
            active_stage_mode=cook.get("activeStageMode"),
            cook_started_timestamp=cook.get("startedTimestamp"),
            online=system_info.get("online"),
            firmware_version=system_info.get("firmwareVersion"),
            temperature_unit=state_obj.get("temperatureUnit"),
            timer_mode=timer_mode if timer_mode else None,
            timer_started_at=timer_node.get("startedAtTimestamp"),
        )

    def _parse_a3_state(self, body: dict[str, Any]) -> AnovaDeviceState:
        """Parse a3 state format."""
        is_cooking = body.get("isCooking", False)
        return AnovaDeviceState(
            is_cooking=bool(is_cooking),
            target_temperature=_safe_float(body.get("targetTemperature")),
            water_temperature=_safe_float(body.get("currentTemperature")),
            heater_temperature=None,
            triac_temperature=None,
            cook_time=None,
            cook_time_remaining=_safe_int(body.get("timerInSeconds")),
            mode="cook" if is_cooking else "idle",
            state=None,
        )

    def _parse_legacy_state(self, body: dict[str, Any]) -> AnovaDeviceState:
        """Parse legacy state format with job/job-status/temperature-info."""
        job = body.get("job", {})
        job_status = body.get("job-status", {})
        temp_info = body.get("temperature-info", {})
        mode = job.get("mode", "")

        return AnovaDeviceState(
            is_cooking=mode == "COOK",
            target_temperature=_safe_float(job.get("target-temperature")),
            water_temperature=_safe_float(temp_info.get("water-temperature")),
            heater_temperature=_safe_float(temp_info.get("heater-temperature")),
            triac_temperature=_safe_float(temp_info.get("triac-temperature")),
            cook_time=_safe_int(job.get("cook-time-seconds")),
            cook_time_remaining=_safe_int(job_status.get("cook-time-remaining")),
            mode=mode.lower() if mode else None,
            state=job_status.get("state", "").lower() or None,
        )


def _calc_timer_remaining(
    timer_mode: str, initial: int | None, started_at: str | None
) -> int | None:
    """Calculate remaining timer seconds from mode, initial duration, and start time."""
    if timer_mode == "completed":
        return 0
    if timer_mode == "running" and initial and started_at:
        try:
            started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            return max(0, int(initial - elapsed))
        except (ValueError, TypeError):
            return None
    if timer_mode == "idle" and initial:
        return initial
    return None


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
