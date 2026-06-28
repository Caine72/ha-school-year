"""Sensor platform for School Year."""

from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    STATE_OUTSIDE_TERM,
    STATE_SCHOOL_CLOSED,
    STATE_SCHOOL_DAY,
    STATE_UNKNOWN,
    STATE_WEEKEND,
    SUPPORTED_PARSER,
    SUPPORTED_SCHOOL_FORM,
    SUPPORTED_SOURCE,
)
from .coordinator import SchoolYearCoordinator
from .entity import SchoolYearEntity
from .parser import SchoolEvent

STATUS_DISPLAY: dict[str, str] = {
    STATE_SCHOOL_DAY: "School Day",
    STATE_SCHOOL_CLOSED: "School Closed",
    STATE_WEEKEND: "Weekend",
    STATE_OUTSIDE_TERM: "Outside School Term",
    STATE_UNKNOWN: "Unknown",
}

STATUS_OPTIONS = list(STATUS_DISPLAY.values())
NO_ACTIVE_CLOSURE = "No Active Closure"
NO_UPCOMING_CLOSURE = "No Upcoming Closure"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities."""
    coordinator: SchoolYearCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SchoolStatusSensor(coordinator),
            CurrentClosureSensor(coordinator),
            NextClosureSensor(coordinator),
            NextSchoolDaySensor(coordinator),
            SourceUpdatedSensor(coordinator),
        ]
    )


class SchoolStatusSensor(SchoolYearEntity, SensorEntity):
    """Sensor with the evaluated school status for today."""

    _attr_translation_key = "school_year_status"
    _attr_icon = "mdi:school-outline"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUS_OPTIONS

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            unique_suffix="status",
            name="School year status",
            suggested_object_id="status",
        )

    @property
    def native_value(self) -> str | None:
        """Return today's school status as a display-friendly value."""
        if self.coordinator.data is None:
            return None
        raw_state = self.coordinator.data.status_for_day(self.today).state
        return STATUS_DISPLAY.get(raw_state, STATUS_DISPLAY[STATE_UNKNOWN])

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return parsed school-year data as attributes."""
        if self.coordinator.data is None:
            return None

        attributes = self.coordinator.data.as_attributes(self.today)
        attributes["raw_status"] = attributes.pop("status", None)
        attributes["status"] = self.native_value
        return attributes


class CurrentClosureSensor(SchoolYearEntity, SensorEntity):
    """Sensor exposing the active school closure, if any."""

    _attr_translation_key = "current_school_closure"
    _attr_icon = "mdi:calendar-alert"

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            unique_suffix="current_closure",
            name="Current school closure",
            suggested_object_id="current_closure",
        )

    @property
    def native_value(self) -> str | None:
        """Return the active closure name, or a clear empty state."""
        event = self._event
        return event.name if event else NO_ACTIVE_CLOSURE

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return current closure details."""
        event = self._event
        if event is None:
            return {"active": False}

        attributes = event.as_dict()
        attributes["active"] = True
        attributes["days_until_end"] = max((event.end - self.today).days, 0)
        return attributes

    @property
    def _event(self) -> SchoolEvent | None:
        """Return the current closure event."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.current_event_for_day(self.today, closures_only=True)


class NextClosureSensor(SchoolYearEntity, SensorEntity):
    """Sensor exposing the next upcoming school closure."""

    _attr_translation_key = "next_school_closure"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            unique_suffix="next_closure",
            name="Next school closure",
            suggested_object_id="next_closure",
        )

    @property
    def native_value(self) -> str | None:
        """Return the next closure name, or a clear empty state."""
        event = self._event
        return event.name if event else NO_UPCOMING_CLOSURE

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return next closure details."""
        event = self._event
        if event is None:
            return {"active": False, "days_until_start": None}

        attributes = event.as_dict()
        attributes["active"] = False
        attributes["days_until_start"] = (event.start - self.today).days
        return attributes

    @property
    def _event(self) -> SchoolEvent | None:
        """Return the next future closure event."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.next_future_event_for_day(self.today, closures_only=True)


class NextSchoolDaySensor(SchoolYearEntity, SensorEntity):
    """Sensor exposing the next known school day."""

    _attr_translation_key = "next_school_day"
    _attr_icon = "mdi:calendar-today"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            unique_suffix="next_school_day",
            name="Next school day",
            suggested_object_id="next_school_day",
        )

    @property
    def native_value(self) -> date | None:
        """Return the next school day on or after today."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.next_school_day_on_or_after(self.today)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return details about the next school day and configured lookahead."""
        if self.coordinator.data is None:
            return None

        target_date = self.native_value
        status = self.coordinator.data.status_for_day(self.today)
        if target_date is None:
            return {
                "within_lookahead": False,
                "reason": "no known upcoming school day",
                "today_status": status.state,
                "lookahead_days": self.coordinator.school_day_lookahead_days,
                "days_until_target": None,
            }

        return {
            "within_lookahead": (target_date - self.today).days <= self.coordinator.school_day_lookahead_days,
            "reason": (
                "today is a school day"
                if target_date == self.today
                else "upcoming school day found"
            ),
            "today_status": status.state,
            "lookahead_days": self.coordinator.school_day_lookahead_days,
            "days_until_target": (target_date - self.today).days,
        }


class SourceUpdatedSensor(SchoolYearEntity, SensorEntity):
    """Diagnostic sensor exposing the official page's last-updated date."""

    _attr_translation_key = "source_updated"
    _attr_icon = "mdi:web-refresh"
    _attr_device_class = SensorDeviceClass.DATE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator,
            unique_suffix="source_updated",
            name="Source updated",
            suggested_object_id="source_updated",
        )

    @property
    def native_value(self) -> date | None:
        """Return the source page's last-updated date."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.source_updated

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return source diagnostics."""
        if self.coordinator.data is None:
            return None
        return {
            "source_url": self.coordinator.data.source_url,
            "fetched_at": self.coordinator.data.fetched_at.isoformat(),
            "source": SUPPORTED_SOURCE,
            "school_form": SUPPORTED_SCHOOL_FORM,
            "parser": SUPPORTED_PARSER,
        }
