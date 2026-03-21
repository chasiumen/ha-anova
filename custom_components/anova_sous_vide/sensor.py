"""Sensor platform for Anova Sous Vide."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .client import AnovaDeviceState
from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator
from .entity import AnovaSousVideDescriptionEntity

ANOVA_STATES = [
    "cooking",
    "preheating",
    "maintaining",
    "no_state",
    "set_timer",
    "timer_expired",
]

ANOVA_MODES = [
    "cook",
    "idle",
    "low_water",
    "high_temp",
    "device_failure",
    "ota",
    "provisioning",
    "startup",
]


@dataclass(frozen=True, kw_only=True)
class AnovaSousVideSensorDescription(SensorEntityDescription):
    """Describes an Anova Sous Vide sensor."""

    value_fn: Callable[[AnovaDeviceState], StateType]


SENSOR_DESCRIPTIONS: list[AnovaSousVideSensorDescription] = [
    AnovaSousVideSensorDescription(
        key="water_temperature",
        translation_key="water_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.water_temperature,
    ),
    AnovaSousVideSensorDescription(
        key="heater_temperature",
        translation_key="heater_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.heater_temperature,
    ),
    AnovaSousVideSensorDescription(
        key="triac_temperature",
        translation_key="triac_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.triac_temperature,
    ),
    AnovaSousVideSensorDescription(
        key="cook_time",
        translation_key="cook_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.cook_time,
    ),
    AnovaSousVideSensorDescription(
        key="cook_time_remaining",
        translation_key="cook_time_remaining",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: data.cook_time_remaining,
    ),
    AnovaSousVideSensorDescription(
        key="mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=ANOVA_MODES,
        value_fn=lambda data: data.mode,
    ),
    AnovaSousVideSensorDescription(
        key="state",
        translation_key="state",
        device_class=SensorDeviceClass.ENUM,
        options=ANOVA_STATES,
        value_fn=lambda data: data.state,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnovaSousVideConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Anova Sous Vide sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        AnovaSousVideSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class AnovaSousVideSensor(AnovaSousVideDescriptionEntity, SensorEntity):
    """Sensor entity for Anova Sous Vide."""

    entity_description: AnovaSousVideSensorDescription

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
