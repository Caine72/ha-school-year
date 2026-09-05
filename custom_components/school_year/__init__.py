"""School Year integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_INCLUDE_INFERRED_LONG_BREAKS,
    CONF_PAGE_CHECK_INTERVAL_HOURS,
    CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
    DOMAIN,
    LEGACY_CONF_INCLUDE_INFERRED_BREAKS,
    LEGACY_CONF_MENU_LOOKAHEAD_DAYS,
    LEGACY_CONF_POLL_HOURS,
)
from .coordinator import SchoolYearCoordinator

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate legacy config/options keys to readable config keys."""
    data = dict(entry.data)
    options = dict(entry.options)
    changed = False

    for store in (data, options):
        if LEGACY_CONF_POLL_HOURS in store and CONF_PAGE_CHECK_INTERVAL_HOURS not in store:
            store[CONF_PAGE_CHECK_INTERVAL_HOURS] = store.pop(LEGACY_CONF_POLL_HOURS)
            changed = True
        elif LEGACY_CONF_POLL_HOURS in store:
            store.pop(LEGACY_CONF_POLL_HOURS)
            changed = True

        if (
            LEGACY_CONF_INCLUDE_INFERRED_BREAKS in store
            and CONF_INCLUDE_INFERRED_LONG_BREAKS not in store
        ):
            store[CONF_INCLUDE_INFERRED_LONG_BREAKS] = store.pop(
                LEGACY_CONF_INCLUDE_INFERRED_BREAKS
            )
            changed = True
        elif LEGACY_CONF_INCLUDE_INFERRED_BREAKS in store:
            store.pop(LEGACY_CONF_INCLUDE_INFERRED_BREAKS)
            changed = True

        if LEGACY_CONF_MENU_LOOKAHEAD_DAYS in store and CONF_SCHOOL_DAY_LOOKAHEAD_DAYS not in store:
            store[CONF_SCHOOL_DAY_LOOKAHEAD_DAYS] = store.pop(LEGACY_CONF_MENU_LOOKAHEAD_DAYS)
            changed = True
        elif LEGACY_CONF_MENU_LOOKAHEAD_DAYS in store:
            store.pop(LEGACY_CONF_MENU_LOOKAHEAD_DAYS)
            changed = True

    if changed or entry.minor_version < 5:
        hass.config_entries.async_update_entry(entry, data=data, options=options, minor_version=5)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up School Year from a config entry."""
    coordinator = SchoolYearCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_midnight_refresh()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        coordinator: SchoolYearCoordinator = hass.data[DOMAIN][entry.entry_id]
        coordinator.stop_midnight_refresh()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
