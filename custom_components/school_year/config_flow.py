"""Config flow for School Year."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

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
    MAX_POLL_HOURS,
    MAX_SCHOOL_DAY_LOOKAHEAD_DAYS,
    MIN_POLL_HOURS,
    MIN_SCHOOL_DAY_LOOKAHEAD_DAYS,
)
from .coordinator import (
    CannotConnectError,
    InvalidSourceError,
    async_fetch_school_year_data,
)

URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))


def _http_url(value: Any) -> str:
    """Validate and normalize an HTTP(S) source URL."""
    url = str(value).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise vol.Invalid("Expected an HTTP or HTTPS URL")
    return url


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the shared config/options schema."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(CONF_URL, default=defaults.get(CONF_URL, DEFAULT_URL)): URL_SELECTOR,
            vol.Optional(
                CONF_PAGE_CHECK_INTERVAL_HOURS,
                default=defaults.get(
                    CONF_PAGE_CHECK_INTERVAL_HOURS,
                    defaults.get(LEGACY_CONF_POLL_HOURS, DEFAULT_POLL_HOURS),
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_POLL_HOURS, max=MAX_POLL_HOURS)),
            vol.Optional(
                CONF_INCLUDE_INFERRED_LONG_BREAKS,
                default=defaults.get(
                    CONF_INCLUDE_INFERRED_LONG_BREAKS,
                    defaults.get(LEGACY_CONF_INCLUDE_INFERRED_BREAKS, True),
                ),
            ): bool,
            vol.Optional(
                CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
                default=defaults.get(
                    CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
                    defaults.get(
                        LEGACY_CONF_MENU_LOOKAHEAD_DAYS,
                        DEFAULT_SCHOOL_DAY_LOOKAHEAD_DAYS,
                    ),
                ),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(
                    min=MIN_SCHOOL_DAY_LOOKAHEAD_DAYS,
                    max=MAX_SCHOOL_DAY_LOOKAHEAD_DAYS,
                ),
            ),
        }
    )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for School Year."""

    VERSION = 1
    MINOR_VERSION = 5

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            errors = await _async_validate_input(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="School year", data=user_input)

        else:
            errors = {}

        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Handle options for School Year."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage options."""
        if user_input is not None:
            errors = await _async_validate_input(self.hass, user_input)
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        else:
            errors = {}

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(defaults), errors=errors)


async def _async_validate_input(hass: HomeAssistant, user_input: dict[str, Any]) -> dict[str, str]:
    """Validate connectivity and parser compatibility before saving settings."""
    try:
        user_input[CONF_URL] = _http_url(user_input[CONF_URL])
    except vol.Invalid:
        return {CONF_URL: "invalid_url"}

    try:
        await async_fetch_school_year_data(
            hass,
            user_input[CONF_URL],
            include_inferred_breaks=user_input[CONF_INCLUDE_INFERRED_LONG_BREAKS],
        )
    except CannotConnectError:
        return {"base": "cannot_connect"}
    except InvalidSourceError:
        return {"base": "invalid_source"}
    return {}
