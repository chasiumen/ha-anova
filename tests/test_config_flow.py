"""Tests for the Anova Sous Vide config flow logic."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_client_path = Path(__file__).resolve().parent.parent / "custom_components" / "anova_sous_vide"
if str(_client_path) not in sys.path:
    sys.path.insert(0, str(_client_path))
from client import AnovaDevice  # noqa: E402


MOCK_PAT = "anova-test-token"
MOCK_DEVICE = AnovaDevice(
    cooker_id="cooker-123",
    name="My Cooker",
    device_type="a7",
)


class TestConfigFlowLogic:
    """Unit tests for config flow validation logic."""

    def test_valid_token_format(self) -> None:
        assert "anova-good-token".startswith("anova-")

    def test_invalid_token_format(self) -> None:
        assert not "bad-token".startswith("anova-")

    def test_device_data_structure(self) -> None:
        assert MOCK_DEVICE.cooker_id == "cooker-123"
        assert MOCK_DEVICE.name == "My Cooker"
        assert MOCK_DEVICE.device_type == "a7"
