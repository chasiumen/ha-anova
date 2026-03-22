"""Sensor platform for Anova Sous Vide."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

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
    entities: list[SensorEntity] = [
        AnovaSousVideSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    ]
    entities.append(AnovaCookTimeRemainingSensor(coordinator))
    async_add_entities(entities)


class AnovaSousVideSensor(AnovaSousVideDescriptionEntity, SensorEntity):
    """Sensor entity for Anova Sous Vide."""

    entity_description: AnovaSousVideSensorDescription

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)


class AnovaCookTimeRemainingSensor(AnovaSousVideDescriptionEntity, SensorEntity):
    """Sensor that calculates cook time remaining in real-time."""

    entity_description: AnovaSousVideSensorDescription

    def __init__(self, coordinator: AnovaSousVideCoordinator) -> None:
        """Initialize the cook time remaining sensor."""
        description = AnovaSousVideSensorDescription(
            key="cook_time_remaining",
            name="Cook time remaining",
            translation_key="cook_time_remaining",
            icon="mdi:timer-outline",
            value_fn=lambda data: None,
        )
        super().__init__(coordinator, description)

    @property
    def native_value(self) -> StateType:
        """Calculate remaining time on every read, formatted as H:MM:SS."""
        if self.coordinator.data is None:
            return None
        data = self.coordinator.data
        if data.timer_mode == "completed":
            return "0:00:00"
        if data.timer_mode == "running" and data.cook_time and data.timer_started_at:
            try:
                started = datetime.fromisoformat(
                    data.timer_started_at.replace("Z", "+00:00")
                )
                elapsed = (datetime.now(timezone.utc) - started).total_seconds()
                remaining = max(0, int(data.cook_time - elapsed))
                return self._format_duration(remaining)
            except (ValueError, TypeError):
                return None
        if data.timer_mode == "idle" and data.cook_time:
            return self._format_duration(data.cook_time)
        return None

    @staticmethod
    def _format_duration(seconds: int) -> str:
        """Format seconds as H:MM:SS."""
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        return f"{h}:{m:02d}:{s:02d}"
