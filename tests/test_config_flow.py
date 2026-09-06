"""Tests for the School Year config and options flows."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import config_validation as cv
from pytest_homeassistant_custom_component.common import MockConfigEntry
from voluptuous_serialize import convert

from custom_components.school_year.config_flow import _schema
from custom_components.school_year.const import (
    CONF_INCLUDE_INFERRED_LONG_BREAKS,
    CONF_PAGE_CHECK_INTERVAL_HOURS,
    CONF_SCHOOL_DAY_LOOKAHEAD_DAYS,
    DOMAIN,
)
from custom_components.school_year.coordinator import CannotConnectError, InvalidSourceError

USER_INPUT = {
    CONF_URL: "https://example.com/school-year",
    CONF_PAGE_CHECK_INTERVAL_HOURS: 12,
    CONF_INCLUDE_INFERRED_LONG_BREAKS: True,
    CONF_SCHOOL_DAY_LOOKAHEAD_DAYS: 3,
}


def test_schema_serializes_for_home_assistant_frontend() -> None:
    """The config form can cross Home Assistant's HTTP API boundary."""
    convert(_schema(), custom_serializer=cv.custom_serializer)


@pytest.mark.parametrize(
    "invalid_url",
    ("/tmp/school.html", "file:///tmp/school.html", "ftp://example.com"),
)
async def test_user_flow_rejects_non_http_url(hass: HomeAssistant, invalid_url: str) -> None:
    """Local files and unsupported URL schemes cannot be configured."""
    with patch(
        "custom_components.school_year.config_flow.async_fetch_school_year_data",
        new=AsyncMock(),
    ) as validate:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**USER_INPUT, CONF_URL: invalid_url}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_URL: "invalid_url"}
    validate.assert_not_awaited()


async def test_user_flow_validates_and_creates_entry(hass: HomeAssistant) -> None:
    """A supported reachable source creates the single config entry."""
    with patch(
        "custom_components.school_year.config_flow.async_fetch_school_year_data",
        new=AsyncMock(),
    ) as validate:
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == USER_INPUT
    validate.assert_awaited_once()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (CannotConnectError(), "cannot_connect"),
        (InvalidSourceError(), "invalid_source"),
    ],
)
async def test_user_flow_reports_source_failures(
    hass: HomeAssistant, error: Exception, expected: str
) -> None:
    """Connectivity and parsing failures are reported before entry creation."""
    with patch(
        "custom_components.school_year.config_flow.async_fetch_school_year_data",
        new=AsyncMock(side_effect=error),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}, data=USER_INPUT
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected}


async def test_options_flow_validates_and_reloads(hass: HomeAssistant) -> None:
    """Saving valid options uses Home Assistant's automatic reload flow."""
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data=USER_INPUT)
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.school_year.config_flow.async_fetch_school_year_data",
            new=AsyncMock(),
        ),
        patch.object(hass.config_entries, "async_reload", new=AsyncMock()) as reload_entry,
    ):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {**USER_INPUT, CONF_PAGE_CHECK_INTERVAL_HOURS: 48}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    reload_entry.assert_awaited_once_with(entry.entry_id)
