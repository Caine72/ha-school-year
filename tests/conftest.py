"""Shared test configuration for School Year."""

import pytest

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def automatically_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to discover the integration in this repository."""
