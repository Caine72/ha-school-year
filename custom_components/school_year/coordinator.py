"""Coordinator for the School Year integration."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_INCLUDE_INFERRED_LONG_BREAKS,
    CONF_PAGE_CHECK_INTERVAL_HOURS,
    CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
    DEFAULT_POLL_HOURS,
    DEFAULT_SCHOOL_DAY_LOOKAHEAD_DAYS,
    DEFAULT_URL,
    DOMAIN,
    LEGACY_CONF_INCLUDE_INFERRED_BREAKS,
    LEGACY_CONF_MENU_LOOKAHEAD_DAYS,
    LEGACY_CONF_POLL_HOURS,
)
from .parser import SchoolYearData, parse_school_year_html

_LOGGER = logging.getLogger(__name__)


class SchoolYearCoordinator(DataUpdateCoordinator[SchoolYearData]):
    """Fetch and parse school-year data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self._session = async_get_clientsession(hass)

        poll_hours = int(
            entry.options.get(
                CONF_PAGE_CHECK_INTERVAL_HOURS,
                entry.options.get(
                    LEGACY_CONF_POLL_HOURS,
                    entry.data.get(
                        CONF_PAGE_CHECK_INTERVAL_HOURS,
                        entry.data.get(LEGACY_CONF_POLL_HOURS, DEFAULT_POLL_HOURS),
                    ),
                ),
            )
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=poll_hours),
            always_update=False,
        )

    @property
    def source_url(self) -> str:
        """Return the configured source URL."""
        return str(
            self.config_entry.options.get(
                CONF_URL,
                self.config_entry.data.get(CONF_URL, DEFAULT_URL),
            )
        )

    @property
    def include_inferred_breaks(self) -> bool:
        """Return whether inferred summer/Christmas breaks should be included."""
        return bool(
            self.config_entry.options.get(
                CONF_INCLUDE_INFERRED_LONG_BREAKS,
                self.config_entry.options.get(
                    LEGACY_CONF_INCLUDE_INFERRED_BREAKS,
                    self.config_entry.data.get(
                        CONF_INCLUDE_INFERRED_LONG_BREAKS,
                        self.config_entry.data.get(LEGACY_CONF_INCLUDE_INFERRED_BREAKS, True),
                    ),
                ),
            )
        )

    @property
    def school_day_lookahead_days(self) -> int:
        """Return how many days ahead generic school-day lookahead should check."""
        return int(
            self.config_entry.options.get(
                CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
                self.config_entry.options.get(
                    LEGACY_CONF_MENU_LOOKAHEAD_DAYS,
                    self.config_entry.data.get(
                        CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
                        self.config_entry.data.get(
                            LEGACY_CONF_MENU_LOOKAHEAD_DAYS,
                            DEFAULT_SCHOOL_DAY_LOOKAHEAD_DAYS,
                        ),
                    ),
                ),
            )
        )

    async def _async_update_data(self) -> SchoolYearData:
        """Fetch and parse data from the configured source."""
        try:
            async with asyncio.timeout(30):
                response = await self._session.get(self.source_url)
                response.raise_for_status()
                html = await response.text()
        except (TimeoutError, ClientError) as err:
            raise UpdateFailed(f"Could not fetch school-year page: {err}") from err

        try:
            return parse_school_year_html(
                html,
                self.source_url,
                include_inferred_breaks=self.include_inferred_breaks,
                fetched_at=dt_util.now(),
            )
        except Exception as err:  # noqa: BLE001 - convert parser errors to HA update errors
            raise UpdateFailed(f"Could not parse school-year page: {err}") from err
