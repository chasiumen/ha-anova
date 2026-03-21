"""Base entity for the Anova Sous Vide integration."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import AnovaSousVideCoordinator


class AnovaSousVideEntity(CoordinatorEntity[AnovaSousVideCoordinator], Entity):
    """Base entity for Anova Sous Vide."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AnovaSousVideCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.client.connected and super().available


class AnovaSousVideDescriptionEntity(AnovaSousVideEntity):
    """Entity that uses an EntityDescription."""

    def __init__(
        self,
        coordinator: AnovaSousVideCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize with a description."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.cooker_id}_{description.key}"
