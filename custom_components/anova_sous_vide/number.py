"""Number platform for Anova Sous Vide."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator
from .entity import AnovaSousVideEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnovaSousVideConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Sous Vide number entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([AnovaTimerNumber(coordinator)])


class AnovaTimerNumber(AnovaSousVideEntity, NumberEntity):
    """Number entity for setting cook timer in hours."""

    _attr_native_min_value = 0
    _attr_native_max_value = 72
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_mode = NumberMode.SLIDER
    _attr_translation_key = "cook_timer"

    def __init__(self, coordinator: AnovaSousVideCoordinator) -> None:
        """Initialize the timer number."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.cooker_id}_cook_timer"
        self._attr_native_value = 0

    async def async_set_native_value(self, value: float) -> None:
        """Set the timer value."""
        self._attr_native_value = value
        self.async_write_ha_state()
