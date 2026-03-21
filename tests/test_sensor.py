"""Tests for the Anova Sous Vide sensor value mappings."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_client_path = Path(__file__).resolve().parent.parent / "custom_components" / "anova_sous_vide"
if str(_client_path) not in sys.path:
    sys.path.insert(0, str(_client_path))
from client import AnovaDeviceState  # noqa: E402


@pytest.fixture
def state() -> AnovaDeviceState:
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


class TestDeviceStateValues:
    """Tests for AnovaDeviceState field access."""

    def test_water_temperature(self, state: AnovaDeviceState) -> None:
        assert state.water_temperature == 52.3

    def test_heater_temperature(self, state: AnovaDeviceState) -> None:
        assert state.heater_temperature == 56.1

    def test_triac_temperature(self, state: AnovaDeviceState) -> None:
        assert state.triac_temperature == 45.2

    def test_cook_time(self, state: AnovaDeviceState) -> None:
        assert state.cook_time == 3600

    def test_cook_time_remaining(self, state: AnovaDeviceState) -> None:
        assert state.cook_time_remaining == 1800

    def test_mode(self, state: AnovaDeviceState) -> None:
        assert state.mode == "cook"

    def test_state_field(self, state: AnovaDeviceState) -> None:
        assert state.state == "cooking"

    def test_all_none_defaults(self) -> None:
        state = AnovaDeviceState()
        assert state.is_cooking is False
        assert state.target_temperature is None
        assert state.water_temperature is None
        assert state.heater_temperature is None
        assert state.triac_temperature is None
        assert state.cook_time is None
        assert state.cook_time_remaining is None
        assert state.mode is None
        assert state.state is None
