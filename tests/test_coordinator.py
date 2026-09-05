"""Tests for coordinator fetching and daily refresh behavior."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.school_year.const import DOMAIN
from custom_components.school_year.coordinator import SchoolYearCoordinator


def test_midnight_refresh_has_single_lifecycle(hass: HomeAssistant) -> None:
    """One coordinator callback updates all entities and is cancelled on unload."""
    entry = MockConfigEntry(domain=DOMAIN)
    cancel = MagicMock()

    with patch(
        "custom_components.school_year.coordinator.async_track_time_change",
        return_value=cancel,
    ) as track:
        coordinator = SchoolYearCoordinator(hass, entry)
        coordinator.start_midnight_refresh()
        coordinator.start_midnight_refresh()

    track.assert_called_once()
    with patch.object(coordinator, "async_update_listeners") as update_listeners:
        coordinator._handle_midnight_refresh(datetime.now())
    update_listeners.assert_called_once_with()

    coordinator.stop_midnight_refresh()
    coordinator.stop_midnight_refresh()
    cancel.assert_called_once_with()
