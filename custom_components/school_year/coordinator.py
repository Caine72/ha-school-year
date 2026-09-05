"""Coordinator for the School Year integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
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


class CannotConnectError(Exception):
    """Raised when the configured source cannot be fetched."""


class InvalidSourceError(Exception):
    """Raised when the configured source does not contain usable school-year data."""


async def async_fetch_school_year_data(
    hass: HomeAssistant,
    source_url: str,
    *,
    include_inferred_breaks: bool,
) -> SchoolYearData:
    """Fetch and parse school-year data from a source URL."""
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(30):
            async with session.get(source_url) as response:
                response.raise_for_status()
                html = await response.text()
    except (TimeoutError, ClientError) as err:
        raise CannotConnectError(f"Could not fetch school-year page: {err}") from err

    try:
        return parse_school_year_html(
            html,
            source_url,
            include_inferred_breaks=include_inferred_breaks,
            fetched_at=dt_util.now(),
        )
    except (TypeError, ValueError) as err:
        raise InvalidSourceError(f"Could not parse school-year page: {err}") from err


class SchoolYearCoordinator(DataUpdateCoordinator[SchoolYearData]):
    """Fetch and parse school-year data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self._cancel_midnight_refresh: Callable[[], None] | None = None

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

    def start_midnight_refresh(self) -> None:
        """Start one daily state refresh shared by all coordinator entities."""
        if self._cancel_midnight_refresh is not None:
            return
        self._cancel_midnight_refresh = async_track_time_change(
            self.hass,
            self._handle_midnight_refresh,
            hour=0,
            minute=0,
            second=5,
        )

    def stop_midnight_refresh(self) -> None:
        """Stop the daily state refresh."""
        if self._cancel_midnight_refresh is not None:
            self._cancel_midnight_refresh()
            self._cancel_midnight_refresh = None

    def _handle_midnight_refresh(self, _now: datetime) -> None:
        """Notify every entity when the local date changes."""
        self.async_update_listeners()

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
            return await async_fetch_school_year_data(
                self.hass,
                self.source_url,
                include_inferred_breaks=self.include_inferred_breaks,
            )
        except (CannotConnectError, InvalidSourceError) as err:
            raise UpdateFailed(str(err)) from err
