"""Tests for the Anova Sous Vide WebSocket client."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import client module directly to avoid HA dependency
_client_path = Path(__file__).resolve().parent.parent / "custom_components" / "anova_sous_vide"
if str(_client_path) not in sys.path:
    sys.path.insert(0, str(_client_path))
from client import AnovaDevice, AnovaDeviceState, AnovaSousVideClient  # noqa: E402


@pytest.fixture
def client_instance() -> AnovaSousVideClient:
    """Return a fresh client instance."""
    return AnovaSousVideClient()


class TestHandleDeviceList:
    """Tests for _handle_device_list."""

    def test_parses_single_device(self, client_instance: AnovaSousVideClient) -> None:
        data = {
            "command": "EVENT_APC_WIFI_LIST",
            "payload": [
                {
                    "cookerId": "cooker-123",
                    "name": "My Cooker",
                    "type": "a7",
                }
            ],
        }
        client_instance._handle_device_list(data)
        assert len(client_instance.discovered_devices) == 1
        assert client_instance.discovered_devices[0].cooker_id == "cooker-123"
        assert client_instance.discovered_devices[0].name == "My Cooker"
        assert client_instance.discovered_devices[0].device_type == "a7"

    def test_skips_duplicate_devices(self, client_instance: AnovaSousVideClient) -> None:
        data = {
            "command": "EVENT_APC_WIFI_LIST",
            "payload": [
                {"cookerId": "cooker-123", "name": "My Cooker", "type": "a7"},
            ],
        }
        client_instance._handle_device_list(data)
        client_instance._handle_device_list(data)
        assert len(client_instance.discovered_devices) == 1

    def test_handles_empty_payload(self, client_instance: AnovaSousVideClient) -> None:
        data = {"command": "EVENT_APC_WIFI_LIST", "payload": []}
        client_instance._handle_device_list(data)
        assert len(client_instance.discovered_devices) == 0


class TestHandleStateUpdate:
    """Tests for _handle_state_update."""

    def test_parses_a7_state(self, client_instance: AnovaSousVideClient) -> None:
        """Test parsing a6/a7 format (Precision Cooker 3.0)."""
        data = {
            "command": "EVENT_APC_STATE",
            "payload": {
                "cookerId": "cooker-123",
                "type": "a7",
                "state": {
                    "systemInfo": {"firmwareVersion": "2.0.0"},
                    "state": {"mode": "cook"},
                    "nodes": {
                        "waterTemperatureSensor": {
                            "current": {"celsius": 52.3},
                            "setpoint": {"celsius": 55.0},
                        },
                        "timer": {"initial": 3600},
                        "lowWater": {"warning": False, "empty": False},
                    },
                },
            },
        }
        client_instance._handle_state_update(data)
        state = client_instance.get_state("cooker-123")
        assert state.is_cooking is True
        assert state.target_temperature == 55.0
        assert state.water_temperature == 52.3
        assert state.cook_time == 3600
        assert state.mode == "cook"

    def test_parses_legacy_state(self, client_instance: AnovaSousVideClient) -> None:
        """Test parsing legacy format with job/job-status."""
        data = {
            "command": "EVENT_APC_STATE",
            "payload": {
                "cookerId": "cooker-123",
                "type": "unknown",
                "state": {
                    "job": {
                        "id": "abc",
                        "cook-time-seconds": 3600,
                        "target-temperature": 55.0,
                        "temperature-unit": "C",
                        "mode": "COOK",
                        "ota-url": "",
                    },
                    "job-status": {
                        "cook-time-remaining": 1800,
                        "state": "COOKING",
                    },
                    "temperature-info": {
                        "water-temperature": 52.3,
                        "heater-temperature": 56.1,
                        "triac-temperature": 45.2,
                    },
                    "pin-info": {},
                },
            },
        }
        client_instance._handle_state_update(data)
        state = client_instance.get_state("cooker-123")
        assert state.is_cooking is True
        assert state.target_temperature == 55.0
        assert state.water_temperature == 52.3
        assert state.heater_temperature == 56.1
        assert state.triac_temperature == 45.2
        assert state.cook_time == 3600
        assert state.cook_time_remaining == 1800

    def test_calls_state_callbacks(self, client_instance: AnovaSousVideClient) -> None:
        callback = MagicMock()
        client_instance.add_state_callback(callback)
        data = {
            "command": "EVENT_APC_STATE",
            "payload": {
                "cookerId": "cooker-123",
                "type": "a7",
                "state": {
                    "state": {"mode": "idle"},
                    "nodes": {
                        "waterTemperatureSensor": {
                            "current": {"celsius": 20.0},
                            "setpoint": {"celsius": 55.0},
                        },
                        "timer": {"initial": 0},
                        "lowWater": {"warning": False, "empty": False},
                    },
                    "systemInfo": {"firmwareVersion": "2.0.0"},
                },
            },
        }
        client_instance._handle_state_update(data)
        callback.assert_called_once()
        assert callback.call_args[0][0] == "cooker-123"

    def test_ignores_missing_cooker_id(self, client_instance: AnovaSousVideClient) -> None:
        data = {"command": "EVENT_APC_STATE", "payload": {}}
        client_instance._handle_state_update(data)
        assert client_instance.get_state("").is_cooking is False


class TestHandleMessage:
    """Tests for _handle_message routing."""

    def test_routes_device_list(self, client_instance: AnovaSousVideClient) -> None:
        data = {"command": "EVENT_APC_WIFI_LIST", "payload": []}
        client_instance._handle_message(data)

    def test_routes_state_update(self, client_instance: AnovaSousVideClient) -> None:
        data = {
            "command": "EVENT_APC_STATE",
            "payload": {"cookerId": "c1", "state": {}},
        }
        client_instance._handle_message(data)

    def test_routes_response(self, client_instance: AnovaSousVideClient) -> None:
        data = {"command": "RESPONSE_APC_START", "payload": {"status": "ok"}}
        client_instance._handle_message(data)


class TestCommands:
    """Tests for command construction."""

    @pytest.mark.asyncio
    async def test_start_cook_sends_correct_payload(
        self, client_instance: AnovaSousVideClient
    ) -> None:
        mock_ws = AsyncMock()
        client_instance._ws = mock_ws
        client_instance._connected = True

        await client_instance.start_cook("cooker-123", "a7", 55.0, 0)

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["command"] == "CMD_APC_START"
        assert sent["payload"]["cookerId"] == "cooker-123"
        assert sent["payload"]["type"] == "a7"
        assert sent["payload"]["targetTemperature"] == 55.0
        assert sent["payload"]["unit"] == "C"
        assert sent["payload"]["timer"] == 0
        assert "requestId" in sent

    @pytest.mark.asyncio
    async def test_stop_cook_sends_correct_payload(
        self, client_instance: AnovaSousVideClient
    ) -> None:
        mock_ws = AsyncMock()
        client_instance._ws = mock_ws
        client_instance._connected = True

        await client_instance.stop_cook("cooker-123", "a7")

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["command"] == "CMD_APC_STOP"
        assert sent["payload"]["cookerId"] == "cooker-123"
        assert sent["payload"]["type"] == "a7"

    @pytest.mark.asyncio
    async def test_send_raises_when_not_connected(
        self, client_instance: AnovaSousVideClient
    ) -> None:
        with pytest.raises(ConnectionError):
            await client_instance.start_cook("cooker-123", "a7", 55.0)
