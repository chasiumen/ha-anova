"""Tests for the Anova Sous Vide water heater entity logic."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_client_path = Path(__file__).resolve().parent.parent / "custom_components" / "anova_sous_vide"
if str(_client_path) not in sys.path:
    sys.path.insert(0, str(_client_path))
from client import AnovaDeviceState  # noqa: E402


@pytest.fixture
def cooking_state() -> AnovaDeviceState:
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


class TestWaterHeaterLogic:
    """Tests for water heater state logic without HA dependencies."""

    def test_cooking_state_detection(self, cooking_state: AnovaDeviceState) -> None:
        assert cooking_state.is_cooking is True

    def test_off_state_detection(self) -> None:
        state = AnovaDeviceState()
        assert state.is_cooking is False

    def test_temperature_reading(self, cooking_state: AnovaDeviceState) -> None:
        assert cooking_state.water_temperature == 52.3
        assert cooking_state.target_temperature == 55.0

    def test_none_temperatures_default(self) -> None:
        state = AnovaDeviceState()
        assert state.water_temperature is None
        assert state.target_temperature is None
