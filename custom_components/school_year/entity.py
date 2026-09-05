"""Base entity helpers for School Year."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SUPPORTED_SCHOOL_FORM, SUPPORTED_SOURCE
from .coordinator import SchoolYearCoordinator


class SchoolYearEntity(CoordinatorEntity[SchoolYearCoordinator]):
    """Base entity for this integration."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SchoolYearCoordinator,
        *,
        unique_suffix: str,
        name: str,
        suggested_object_id: str,
    ) -> None:
        """Initialize base entity."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_suffix}"
        self._suggested_object_id = suggested_object_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            manufacturer=SUPPORTED_SOURCE,
            model=SUPPORTED_SCHOOL_FORM,
            name="School year",
            configuration_url=coordinator.source_url,
        )

    @property
    def suggested_object_id(self) -> str:
        """Return a clearer initial entity object ID."""
        return self._suggested_object_id

    @property
    def today(self):
        """Return today's date in the Home Assistant timezone."""
        return dt_util.now().date()
