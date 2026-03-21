"""The Anova Sous Vide integration."""

from __future__ import annotations

import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import AnovaSousVideClient
from .const import CONF_COOKER_ID, CONF_DEVICE_TYPE, CONF_PAT
from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator, AnovaSousVideData

PLATFORMS = [Platform.WATER_HEATER, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: AnovaSousVideConfigEntry
) -> bool:
    """Set up Anova Sous Vide from a config entry."""
    client = AnovaSousVideClient()

    try:
        await client.connect(entry.data[CONF_PAT])
        await client.discover_devices()
    except Exception as err:
        raise ConfigEntryNotReady("Failed to connect to Anova WebSocket") from err

    if not client.discovered_devices:
        raise ConfigEntryNotReady("No devices found on the WebSocket")

    coordinator = AnovaSousVideCoordinator(
        hass,
        entry,
        client,
        entry.data[CONF_COOKER_ID],
        entry.data[CONF_DEVICE_TYPE],
    )

    # Start background listener for ongoing state updates
    await client.start_listening()

    entry.runtime_data = AnovaSousVideData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AnovaSousVideConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.disconnect()
    return unload_ok
