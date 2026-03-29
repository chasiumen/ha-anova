"""The Anova Sous Vide integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

from .client import AnovaSousVideClient
from .const import CONF_COOKER_ID, CONF_DEVICE_TYPE, CONF_PAT, DOMAIN, MAX_TEMP_C, MIN_TEMP_C
from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator, AnovaSousVideData

PLATFORMS = [Platform.WATER_HEATER, Platform.SENSOR, Platform.NUMBER, Platform.SELECT]

SERVICE_START_COOK = "start_cook"
SERVICE_STOP_COOK = "stop_cook"
SERVICE_RESET_TIMER = "reset_timer"
SERVICE_SET_TIMER = "set_timer"
SERVICE_START_SELECTED = "start_selected_recipe"
SERVICE_CANCEL_SELECTED = "cancel_selected_recipe"
ATTR_TEMPERATURE = "temperature"
ATTR_TIMER = "timer"

SERVICE_START_COOK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEMPERATURE): vol.All(
            vol.Coerce(float), vol.Range(min=MIN_TEMP_C, max=MAX_TEMP_C)
        ),
        vol.Optional(ATTR_TIMER, default=0): vol.All(
            vol.Coerce(int), vol.Range(min=0)
        ),
    }
)

SERVICE_SET_TIMER_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TIMER): vol.All(
            vol.Coerce(int), vol.Range(min=0)
        ),
    }
)

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

    async def handle_start_cook(call: ServiceCall) -> None:
        """Handle the start_cook service call."""
        temperature = call.data[ATTR_TEMPERATURE]
        timer = call.data[ATTR_TIMER]
        await coordinator.client.start_cook(
            coordinator.cooker_id,
            coordinator.device_type,
            temperature,
            timer,
        )

    async def handle_stop_cook(call: ServiceCall) -> None:
        """Handle the stop_cook service call."""
        await coordinator.client.stop_cook(
            coordinator.cooker_id,
            coordinator.device_type,
        )

    async def handle_set_timer(call: ServiceCall) -> None:
        """Handle the set_timer service call."""
        timer = call.data[ATTR_TIMER]
        await coordinator.client.set_timer(
            coordinator.cooker_id,
            coordinator.device_type,
            timer,
        )

    async def handle_reset_timer(call: ServiceCall) -> None:
        """Handle the reset_timer service call."""
        await coordinator.client.reset_timer(
            coordinator.cooker_id,
            coordinator.device_type,
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_COOK,
        handle_start_cook,
        schema=SERVICE_START_COOK_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_COOK,
        handle_stop_cook,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIMER,
        handle_set_timer,
        schema=SERVICE_SET_TIMER_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_RESET_TIMER,
        handle_reset_timer,
    )

    async def _get_selected_automation_id() -> str | None:
        """Return the automation entity_id for the currently selected recipe."""
        select_entity = coordinator.recipe_select
        if select_entity:
            return select_entity.selected_automation_id
        return None

    async def handle_start_selected(call: ServiceCall) -> None:
        """Trigger the currently selected recipe automation."""
        automation_id = await _get_selected_automation_id()
        if automation_id:
            await hass.services.async_call(
                "automation", "trigger",
                {"entity_id": automation_id},
                blocking=True,
            )

    async def handle_cancel_selected(call: ServiceCall) -> None:
        """Cancel the currently selected recipe automation."""
        automation_id = await _get_selected_automation_id()
        if automation_id:
            await hass.services.async_call(
                "automation", "turn_off",
                {"entity_id": automation_id, "stop_actions": True},
                blocking=True,
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_START_SELECTED,
        handle_start_selected,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_SELECTED,
        handle_cancel_selected,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AnovaSousVideConfigEntry
) -> bool:
    """Unload a config entry."""
    hass.services.async_remove(DOMAIN, SERVICE_START_COOK)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_COOK)
    hass.services.async_remove(DOMAIN, SERVICE_SET_TIMER)
    hass.services.async_remove(DOMAIN, SERVICE_RESET_TIMER)
    hass.services.async_remove(DOMAIN, SERVICE_START_SELECTED)
    hass.services.async_remove(DOMAIN, SERVICE_CANCEL_SELECTED)
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.client.disconnect()
    return unload_ok
