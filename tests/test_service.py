"""Tests for the anova_sous_vide services (start_cook, stop_cook)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Import client module directly to avoid HA dependency
_client_path = Path(__file__).resolve().parent.parent / "custom_components" / "anova_sous_vide"
if str(_client_path) not in sys.path:
    sys.path.insert(0, str(_client_path))
from client import AnovaSousVideClient  # noqa: E402


class TestStartCookWithTimer:
    """Tests for start_cook command with timer parameter."""

    @pytest.mark.asyncio
    async def test_start_cook_with_timer(self) -> None:
        client = AnovaSousVideClient()
        mock_ws = AsyncMock()
        client._ws = mock_ws
        client._connected = True

        await client.start_cook("cooker-123", "a7", 55.0, 3600)

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["command"] == "CMD_APC_START"
        assert sent["payload"]["cookerId"] == "cooker-123"
        assert sent["payload"]["targetTemperature"] == 55.0
        assert sent["payload"]["timer"] == 3600

    @pytest.mark.asyncio
    async def test_start_cook_without_timer(self) -> None:
        client = AnovaSousVideClient()
        mock_ws = AsyncMock()
        client._ws = mock_ws
        client._connected = True

        await client.start_cook("cooker-123", "a7", 68.0)

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["command"] == "CMD_APC_START"
        assert sent["payload"]["targetTemperature"] == 68.0
        assert sent["payload"]["timer"] == 0

    @pytest.mark.asyncio
    async def test_start_cook_zero_timer(self) -> None:
        client = AnovaSousVideClient()
        mock_ws = AsyncMock()
        client._ws = mock_ws
        client._connected = True

        await client.start_cook("cooker-123", "a7", 55.0, 0)

        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["payload"]["timer"] == 0


class TestStopCook:
    """Tests for stop_cook command."""

    @pytest.mark.asyncio
    async def test_stop_cook_sends_correct_payload(self) -> None:
        client = AnovaSousVideClient()
        mock_ws = AsyncMock()
        client._ws = mock_ws
        client._connected = True

        await client.stop_cook("cooker-123", "a7")

        mock_ws.send.assert_called_once()
        sent = json.loads(mock_ws.send.call_args[0][0])
        assert sent["command"] == "CMD_APC_STOP"
        assert sent["payload"]["cookerId"] == "cooker-123"
        assert sent["payload"]["type"] == "a7"
        assert "requestId" in sent

    @pytest.mark.asyncio
    async def test_stop_cook_raises_when_not_connected(self) -> None:
        client = AnovaSousVideClient()
        with pytest.raises(ConnectionError):
            await client.stop_cook("cooker-123", "a7")
