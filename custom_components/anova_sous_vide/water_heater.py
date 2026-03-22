"""Water heater platform for Anova Sous Vide."""

from __future__ import annotations

from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MAX_TEMP_C, MIN_TEMP_C
from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator
from .entity import AnovaSousVideEntity

OPERATION_OFF = "off"
OPERATION_COOKING = "cooking"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnovaSousVideConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Anova Sous Vide water heater."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([AnovaSousVideWaterHeater(coordinator)])


class AnovaSousVideWaterHeater(AnovaSousVideEntity, WaterHeaterEntity):
    """Water heater entity for Anova Precision Cooker."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = MIN_TEMP_C
    _attr_max_temp = MAX_TEMP_C
    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.ON_OFF
        | WaterHeaterEntityFeature.OPERATION_MODE
    )
    _attr_operation_list = [OPERATION_OFF, OPERATION_COOKING]

    def __init__(self, coordinator: AnovaSousVideCoordinator) -> None:
        """Initialize the water heater entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.cooker_id}_water_heater"
        self._target_temp: float = 55.0  # Default target temp

    @property
    def current_temperature(self) -> float | None:
        """Return the current water temperature."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.water_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        if self.coordinator.data is not None and self.coordinator.data.target_temperature is not None:
            return self.coordinator.data.target_temperature
        return self._target_temp

    @property
    def current_operation(self) -> str:
        """Return the current operation mode."""
        if self.coordinator.data is not None and self.coordinator.data.is_cooking:
            return OPERATION_COOKING
        return OPERATION_OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set the target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return
        self._target_temp = temperature
        # If currently cooking, update the cooker with the new temperature
        if self.coordinator.data is not None and self.coordinator.data.is_cooking:
            await self.coordinator.client.start_cook(
                self.coordinator.cooker_id,
                self.coordinator.device_type,
                temperature,
            )

    def _get_timer_seconds(self) -> int:
        """Read timer value from the cook timer number entity."""
        timer_unique_id = f"{self.coordinator.cooker_id}_cook_timer"
        registry = er.async_get(self.hass)
        entity_id = registry.async_get_entity_id("number", DOMAIN, timer_unique_id)
        if entity_id:
            state = self.hass.states.get(entity_id)
            if state and state.state not in ("unknown", "unavailable"):
                return int(float(state.state) * 3600)
        return 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the cooker (start cooking)."""
        await self.coordinator.client.start_cook(
            self.coordinator.cooker_id,
            self.coordinator.device_type,
            self._target_temp,
            self._get_timer_seconds(),
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the cooker (stop cooking)."""
        await self.coordinator.client.stop_cook(
            self.coordinator.cooker_id,
            self.coordinator.device_type,
        )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set the operation mode."""
        if operation_mode == OPERATION_COOKING:
            await self.async_turn_on()
        else:
            await self.async_turn_off()
