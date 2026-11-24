"""Tests for the button platform."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.eta_webservices import button
from custom_components.eta_webservices.const import STABLE_ID
from homeassistant.const import CONF_HOST, CONF_PORT, EntityCategory
from homeassistant.exceptions import HomeAssistantError

CONFIG = {CONF_HOST: "1.2.3.4", CONF_PORT: 8080, STABLE_ID: "boiler"}


def _store_api_responses_button(hass, entry):
    with patch.object(button, "generate_entity_id", return_value="button.test"):
        entity = button.EtaStoreApiResponsesButton(CONFIG, hass, entry)
    # Set by Home Assistant when the entity is added.
    entity.hass = hass
    return entity


def test_store_api_responses_button_attributes():
    """The button is a disabled-by-default diagnostic entity."""
    entity = _store_api_responses_button(MagicMock(), MagicMock())

    assert entity.unique_id == "eta_boiler_8080_store_api_responses_btn"
    assert entity.translation_key == "store_api_responses_btn"
    assert entity.entity_category is EntityCategory.DIAGNOSTIC
    assert entity.entity_registry_enabled_default is False


async def test_store_api_responses_button_forces_collection():
    """Pressing the button forces a new raw data collection."""
    hass = MagicMock()
    entry = MagicMock()
    entity = _store_api_responses_button(hass, entry)

    with patch.object(button, "async_start_raw_data_collection", AsyncMock()) as start:
        await entity.async_press()

    start.assert_awaited_once_with(hass, entry, CONFIG, force=True)


async def test_store_api_responses_button_reports_running_collection():
    """The error of an already running collection reaches the user."""
    entity = _store_api_responses_button(MagicMock(), MagicMock())

    with (
        patch.object(
            button,
            "async_start_raw_data_collection",
            AsyncMock(side_effect=HomeAssistantError("running")),
        ),
        pytest.raises(HomeAssistantError),
    ):
        await entity.async_press()
