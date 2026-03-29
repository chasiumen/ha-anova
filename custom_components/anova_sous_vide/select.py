"""Select platform for Anova Sous Vide — recipe selector."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import AnovaSousVideConfigEntry, AnovaSousVideCoordinator
from .entity import AnovaSousVideEntity

_LOGGER = logging.getLogger(__name__)

RECIPE_LABEL = "sous_vide"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AnovaSousVideConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Anova recipe selector."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([AnovaRecipeSelect(coordinator)])


class AnovaRecipeSelect(AnovaSousVideEntity, SelectEntity):
    """Select entity that auto-discovers recipe automations by label."""

    _attr_translation_key = "recipe_selector"
    _attr_icon = "mdi:book-open-variant"

    def __init__(self, coordinator: AnovaSousVideCoordinator) -> None:
        """Initialize the recipe selector."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.cooker_id}_recipe_selector"
        self._attr_options: list[str] = []
        self._attr_current_option: str | None = None
        self._recipe_map: dict[str, str] = {}
        coordinator.recipe_select = self

    async def async_added_to_hass(self) -> None:
        """Register for entity registry updates when added to HA."""
        await super().async_added_to_hass()
        self._update_recipe_list()
        self.async_on_remove(
            self.hass.bus.async_listen(
                er.EVENT_ENTITY_REGISTRY_UPDATED, self._on_registry_updated
            )
        )

    @callback
    def _on_registry_updated(self, event) -> None:
        """Handle entity registry changes."""
        self._update_recipe_list()
        self.async_write_ha_state()
        if self.coordinator.active_recipe_sensor:
            self.coordinator.active_recipe_sensor._update_tracked_automations()
            self.coordinator.active_recipe_sensor.async_write_ha_state()

    @callback
    def _update_recipe_list(self) -> None:
        """Scan entity registry for automations labeled 'sous_vide'."""
        registry = er.async_get(self.hass)
        entries = er.async_entries_for_label(registry, RECIPE_LABEL)
        self._recipe_map = {}
        for entry in entries:
            if entry.entity_id.startswith("automation."):
                name = entry.name or entry.original_name or entry.entity_id
                self._recipe_map[name] = entry.entity_id
        self._attr_options = sorted(self._recipe_map.keys())
        if self._attr_current_option not in self._attr_options:
            self._attr_current_option = (
                self._attr_options[0] if self._attr_options else None
            )

    async def async_select_option(self, option: str) -> None:
        """Set the selected recipe."""
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def selected_automation_id(self) -> str | None:
        """Return the entity_id of the currently selected automation."""
        return self._recipe_map.get(self._attr_current_option)
