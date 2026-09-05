"""Binary sensor platform for School Year."""

from __future__ import annotations

from datetime import date

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_SCHOOL_DAY
from .coordinator import SchoolYearCoordinator
from .entity import SchoolYearEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities."""
    coordinator: SchoolYearCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SchoolDayBinarySensor(coordinator),
            SchoolDayInLookaheadBinarySensor(coordinator),
        ]
    )


class SchoolDayBinarySensor(SchoolYearEntity, BinarySensorEntity):
    """Binary sensor that is on when today is a school day."""

    _attr_translation_key = "school_day"
    _attr_icon = "mdi:school"

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            coordinator,
            unique_suffix="school_day",
            name="School day",
            suggested_object_id="school_day",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true when today is a school day."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.status_for_day(self.today).state == STATE_SCHOOL_DAY

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return useful status attributes."""
        if self.coordinator.data is None:
            return None
        status = self.coordinator.data.status_for_day(self.today)
        return status.as_dict()


class SchoolDayInLookaheadBinarySensor(SchoolYearEntity, BinarySensorEntity):
    """Binary sensor that is on when a school day is within the lookahead window."""

    _attr_translation_key = "school_day_in_lookahead"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, coordinator: SchoolYearCoordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(
            coordinator,
            unique_suffix="school_day_in_lookahead",
            name="School day in lookahead",
            suggested_object_id="school_day_in_lookahead",
        )

    @property
    def is_on(self) -> bool | None:
        """Return true when a school day exists within the lookahead window."""
        return self._target_date is not None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return school-day lookahead details."""
        if self.coordinator.data is None:
            return None

        target_date = self._target_date
        today_status = self.coordinator.data.status_for_day(self.today)
        today_is_school_day = today_status.state == STATE_SCHOOL_DAY

        if target_date is None:
            return {
                "reason": "no school day within lookahead window",
                "today_is_school_day": today_is_school_day,
                "today_status": today_status.state,
                "lookahead_days": self.coordinator.school_day_lookahead_days,
                "target_date": None,
                "days_until_target": None,
            }

        days_until_target = (target_date - self.today).days
        return {
            "reason": (
                "today is a school day"
                if days_until_target == 0
                else "upcoming school day is within lookahead window"
            ),
            "today_is_school_day": today_is_school_day,
            "today_status": today_status.state,
            "lookahead_days": self.coordinator.school_day_lookahead_days,
            "target_date": target_date.isoformat(),
            "days_until_target": days_until_target,
        }

    @property
    def _target_date(self) -> date | None:
        """Return the next school day within the configured lookahead window."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.next_school_day_on_or_after(
            self.today,
            max_days_ahead=self.coordinator.school_day_lookahead_days,
        )
