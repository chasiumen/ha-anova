"""Coordinator for Anova Sous Vide integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .client import AnovaDeviceState, AnovaSousVideClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class AnovaSousVideData:
    """Runtime data for the integration."""

    client: AnovaSousVideClient
    coordinator: AnovaSousVideCoordinator


type AnovaSousVideConfigEntry = ConfigEntry[AnovaSousVideData]


class AnovaSousVideCoordinator(DataUpdateCoordinator[AnovaDeviceState]):
    """Coordinator that receives push updates from the WebSocket client."""

    config_entry: AnovaSousVideConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: AnovaSousVideConfigEntry,
        client: AnovaSousVideClient,
        cooker_id: str,
        device_type: str,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            config_entry=config_entry,
            name="Anova Sous Vide",
            logger=_LOGGER,
        )
        self.client = client
        self.cooker_id = cooker_id
        self.device_type = device_type

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, cooker_id)},
            name="Anova Precision Cooker 3.0",
            manufacturer="Anova",
            model="Precision Cooker 3.0",
        )

        self.recipe_select = None  # Set by AnovaRecipeSelect on init
        self.active_recipe_sensor = None  # Set by AnovaActiveRecipeSensor on init
        self.time_at_temp_start: datetime | None = None
        self._prev_stage_mode: str | None = None

        # Register for state updates from the client
        self._remove_callback = client.add_state_callback(self._on_state_update)

    def _on_state_update(self, cooker_id: str, state: AnovaDeviceState) -> None:
        """Handle a state update from the WebSocket client."""
        if cooker_id == self.cooker_id:
            self._track_time_at_temperature(state)
            self.async_set_updated_data(state)

    def _track_time_at_temperature(self, state: AnovaDeviceState) -> None:
        """Track when the cooker reaches and stays at target temperature."""
        stage = state.active_stage_mode
        mode = state.mode

        if mode != "cook":
            # Not cooking — reset
            self.time_at_temp_start = None
            self._prev_stage_mode = None
            return

        if stage == "running" and self.time_at_temp_start is None:
            # Just reached target temperature
            self.time_at_temp_start = datetime.now(timezone.utc)
        elif stage != "running":
            # Lost target temperature (e.g. entering/waiting)
            self.time_at_temp_start = None

        self._prev_stage_mode = stage
