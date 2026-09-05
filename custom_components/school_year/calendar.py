"""Calendar platform for School Year."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SchoolYearCoordinator
from .entity import SchoolYearEntity
from .parser import SchoolEvent


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up calendar entities."""
    coordinator: SchoolYearCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SchoolClosureCalendar(coordinator)])


class SchoolClosureCalendar(SchoolYearEntity, CalendarEntity):
    """Calendar containing all known school closure events."""

    _attr_translation_key = "school_closures"
    _attr_icon = "mdi:calendar"

    @property
    def icon(self) -> str:
        """Return the calendar icon explicitly for frontends that ignore _attr_icon."""
        return "mdi:calendar"

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the calendar entity."""
        super().__init__(
            coordinator,
            unique_suffix="school_closures",
            name="School closures",
            suggested_object_id="school_closures",
        )

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming calendar event."""
        if self.coordinator.data is None:
            return None

        next_event = self.coordinator.data.next_event_for_day(self.today, closures_only=True)
        if next_event is None:
            return None

        return _to_calendar_event(next_event)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Return closure events in the requested time range."""
        if self.coordinator.data is None:
            return []

        start_day = start_date.date()
        end_day = end_date.date()
        events: list[CalendarEvent] = []

        for event in self.coordinator.data.closure_events:
            if event.calendar_end <= start_day or event.start >= end_day:
                continue
            events.append(_to_calendar_event(event))

        return events


def _to_calendar_event(event: SchoolEvent) -> CalendarEvent:
    """Convert a parsed event to a Home Assistant CalendarEvent."""
    return CalendarEvent(
        summary=event.name,
        start=event.start,
        end=event.calendar_end,
        description=(
            f"Type: {event.event_type}\nSource row: {event.raw}\nInferred: {event.inferred}"
        ),
    )
