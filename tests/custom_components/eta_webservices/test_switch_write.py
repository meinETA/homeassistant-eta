"""Tests that a switch does not jump back after it was switched."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.eta_webservices.switch import WRITE_HOLD_SECONDS, EtaSwitch
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant

_URL = "/112/10101/0/0/12080"
_TIME = "custom_components.eta_webservices.switch.time"


@pytest.fixture
def switch(hass: HomeAssistant):
    """A switch that is off, with a terminal accepting every write."""
    coordinator = MagicMock()
    coordinator.data = {_URL: False}
    endpoint = {
        "url": _URL,
        "value": False,
        "valid_values": {"on_value": 1803, "off_value": 1802},
        "friendly_name": "Heizkreis > Ein/Aus Taste",
        "unit": "",
        "endpoint_type": "DEFAULT",
    }
    with patch("custom_components.eta_webservices.entity.async_get_clientsession"):
        entity = EtaSwitch(
            {CONF_HOST: "eta", CONF_PORT: 8080}, hass, "uid", endpoint, coordinator
        )
    client = MagicMock()
    client.set_switch_state = AsyncMock(return_value=True)
    entity._create_eta_client = MagicMock(return_value=client)
    entity.async_write_ha_state = MagicMock()
    return entity


def _poll(entity: EtaSwitch, value) -> None:
    entity.coordinator.data = {_URL: value}
    entity._handle_coordinator_update()


async def test_stale_poll_right_after_switching_is_ignored(switch):
    """A poll that still reads the old state does not flip the switch back."""
    with patch(_TIME) as clock:
        clock.monotonic.return_value = 100.0
        await switch.async_turn_on()
        switch._create_eta_client().set_switch_state.assert_awaited_with(_URL, 1803)
        clock.monotonic.return_value = 101.0
        _poll(switch, False)
    assert switch._attr_is_on is True


async def test_confirming_poll_ends_the_hold(switch):
    """Once a poll agrees, later polls are taken as they are again."""
    with patch(_TIME) as clock:
        clock.monotonic.return_value = 100.0
        await switch.async_turn_on()
        _poll(switch, True)
        clock.monotonic.return_value = 102.0
        _poll(switch, False)  # switched off at the terminal
    assert switch._attr_is_on is False


async def test_poll_wins_after_the_hold(switch):
    """If the terminal really did not switch, the poll corrects it."""
    with patch(_TIME) as clock:
        clock.monotonic.return_value = 100.0
        await switch.async_turn_on()
        clock.monotonic.return_value = 100.0 + WRITE_HOLD_SECONDS + 1
        _poll(switch, False)
    assert switch._attr_is_on is False


async def test_failed_write_keeps_polling_as_before(switch):
    """A refused write changes nothing and holds nothing."""
    switch._create_eta_client().set_switch_state.return_value = False
    await switch.async_turn_on()
    assert switch._attr_is_on is False
    _poll(switch, False)
    assert switch._attr_is_on is False
    switch.async_write_ha_state.assert_called_once()  # from the poll only
