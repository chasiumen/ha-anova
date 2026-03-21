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
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .client import AnovaDeviceState
from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator
from .entity import AnovaSousVideDescriptionEntity

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
        name="Water temperature",
        translation_key="water_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.water_temperature,
    ),
    AnovaSousVideSensorDescription(
        key="target_temperature",
        name="Target temperature",
        translation_key="target_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.target_temperature,
    ),
    AnovaSousVideSensorDescription(
        key="cook_time",
        name="Cook time",
        translation_key="cook_time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.cook_time,
    ),
    AnovaSousVideSensorDescription(
        key="mode",
        name="Mode",
        translation_key="mode",
        device_class=SensorDeviceClass.ENUM,
        options=ANOVA_MODES,
        value_fn=lambda data: data.mode,
    ),
    AnovaSousVideSensorDescription(
        key="cook_time_remaining",
        name="Cook time remaining",
        translation_key="cook_time_remaining",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        value_fn=lambda data: data.cook_time_remaining,
    ),
    AnovaSousVideSensorDescription(
        key="timer_mode",
        name="Timer mode",
        translation_key="timer_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["idle", "running", "completed"],
        value_fn=lambda data: data.timer_mode,
    ),
    AnovaSousVideSensorDescription(
        key="active_stage_mode",
        name="Cook stage",
        translation_key="active_stage_mode",
        device_class=SensorDeviceClass.ENUM,
        options=["running", "waiting"],
        value_fn=lambda data: data.active_stage_mode,
    ),
    AnovaSousVideSensorDescription(
        key="cook_started",
        name="Cook started",
        translation_key="cook_started",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: data.cook_started_timestamp,
    ),
    AnovaSousVideSensorDescription(
        key="online",
        name="Online",
        translation_key="online",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.online,
    ),
    AnovaSousVideSensorDescription(
        key="firmware_version",
        name="Firmware version",
        translation_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.firmware_version,
    ),
    AnovaSousVideSensorDescription(
        key="temperature_unit",
        name="Temperature unit",
        translation_key="temperature_unit",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENUM,
        options=["C", "F"],
        value_fn=lambda data: data.temperature_unit,
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
