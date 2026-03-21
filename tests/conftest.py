"""Shared fixtures for Anova Sous Vide tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Import client module directly to avoid triggering __init__.py (which needs homeassistant)
_client_path = Path(__file__).resolve().parent.parent / "custom_components" / "anova_sous_vide"
sys.path.insert(0, str(_client_path))
import client as _client_mod  # noqa: E402
sys.path.pop(0)

AnovaDevice = _client_mod.AnovaDevice
AnovaDeviceState = _client_mod.AnovaDeviceState
AnovaSousVideClient = _client_mod.AnovaSousVideClient

MOCK_PAT = "anova-test-token-12345"
MOCK_COOKER_ID = "test-cooker-id-abc"
MOCK_DEVICE_TYPE = "a7"


@pytest.fixture
def mock_device_state() -> AnovaDeviceState:
    """Return a mock device state."""
    return AnovaDeviceState(
        is_cooking=True,
        target_temperature=55.0,
        water_temperature=52.3,
        heater_temperature=56.1,
        triac_temperature=45.2,
        cook_time=3600,
        cook_time_remaining=1800,
        mode="cook",
        state="cooking",
    )


@pytest.fixture
def mock_device() -> AnovaDevice:
    """Return a mock discovered device."""
    return AnovaDevice(
        cooker_id=MOCK_COOKER_ID,
        name="Anova Precision Cooker",
        device_type=MOCK_DEVICE_TYPE,
    )


@pytest.fixture
def mock_client(mock_device, mock_device_state):
    """Return a mock client with a discovered device and state."""
    client = MagicMock(spec=AnovaSousVideClient)
    client.connected = True
    client.discovered_devices = [mock_device]
    client.get_state.return_value = mock_device_state
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.discover_devices = AsyncMock(return_value=[mock_device])
    client.start_listening = AsyncMock()
    client.start_cook = AsyncMock()
    client.stop_cook = AsyncMock()
    client.add_state_callback = MagicMock(return_value=lambda: None)
    return client
