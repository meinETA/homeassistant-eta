"""Unit tests for EtaTime."""

from datetime import time
from unittest.mock import MagicMock, patch

import pytest

from custom_components.eta_webservices.const import (
    ADVANCED_OPTIONS_IGNORE_DECIMAL_PLACES_RESTRICTION,
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
)
from custom_components.eta_webservices.time import EtaTime
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_URL = "/user/var/12345"


def _make_endpoint_info(url=_URL, value="19:00"):
    return {
        "url": url,
        "value": value,
        "valid_values": None,
        "friendly_name": "ETA > Heating Start Time",
        "unit": CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
        "endpoint_type": "DEFAULT",
    }


def _make_config():
    return {
        CONF_HOST: "192.168.0.25",
        CONF_PORT: 9091,
        ADVANCED_OPTIONS_IGNORE_DECIMAL_PLACES_RESTRICTION: [],
    }


def _make_coordinator(url=_URL, value="19:00"):
    coordinator = MagicMock()
    coordinator.data = {url: value}
    return coordinator


@pytest.fixture
def make_time_entity(hass: HomeAssistant):
    """Factory that builds an EtaTime entity with a mocked HTTP session."""

    def _make(endpoint_info=None, coordinator=None):
        endpoint_info = endpoint_info or _make_endpoint_info()
        coordinator = coordinator or _make_coordinator(endpoint_info["url"])
        with patch("custom_components.eta_webservices.entity.async_get_clientsession"):
            return EtaTime(
                _make_config(), hass, "test_time_entity", endpoint_info, coordinator
            )

    return _make


# ---------------------------------------------------------------------------
# Valid values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("00:00", time(hour=0, minute=0)),
        ("19:00", time(hour=19, minute=0)),
        ("23:59", time(hour=23, minute=59)),
        ("07:05", time(hour=7, minute=5)),
        ("12", time(hour=12)),  # fromisoformat also accepts a bare hour
    ],
)
def test_valid_values_are_parsed(make_time_entity, raw_value, expected):
    """Well-formed `HH:MM` strings must be parsed into the corresponding time object."""
    entity = make_time_entity()

    entity.handle_data_updates(raw_value)

    assert entity._attr_native_value == expected


# ---------------------------------------------------------------------------
# Invalid values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_value",
    [
        "",
        "xxx",
    ],
)
def test_invalid_values_are_handled_silently(make_time_entity, raw_value):
    """Malformed values must not raise; the entity should fall back to None."""
    entity = make_time_entity()

    entity.handle_data_updates(raw_value)

    assert entity._attr_native_value is None
