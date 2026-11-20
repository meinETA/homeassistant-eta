"""Diagnostics support for ETA Sensors."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtaAPI
from .const import (
    DEFAULT_MAX_PARALLEL_REQUESTS,
    DOMAIN,
    MAX_PARALLEL_REQUESTS,
    REQUEST_SEMAPHORE,
)
from .plant_file import async_terminal_info
from .topology import async_get_report, async_get_topology

# the terminal address and anything that could identify the owner
TO_REDACT = {CONF_HOST, "username", "password", "token", REQUEST_SEMAPHORE}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    config = hass.data[DOMAIN][entry.entry_id]

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    session = async_get_clientsession(hass)

    eta_client = EtaAPI(
        session,
        host,
        port,
        max_concurrent_requests=config.get(
            MAX_PARALLEL_REQUESTS, DEFAULT_MAX_PARALLEL_REQUESTS
        ),
        request_semaphore=config.get(REQUEST_SEMAPHORE),
    )
    user_menu = await eta_client.get_menu()
    api_version = await eta_client.get_api_version()

    topology = next(
        (t for t in async_get_topology(hass) if t["entry_id"] == entry.entry_id),
        None,
    )

    plant_file = async_get_report(hass, entry.entry_id, full=True)
    plant_file.pop("entry_id", None)
    plant_file["terminal"] = await async_terminal_info(
        hass, entry.entry_id, {row["uri"] for row in plant_file.get("tree", [])}
    )

    return {
        "config": async_redact_data(
            {k: v for k, v in config.items() if k != REQUEST_SEMAPHORE}, TO_REDACT
        ),
        "api_version": str(api_version),
        "menu": user_menu,
        "topology": topology,
        # same content as the plant file of the card (report, every endpoint)
        "plant_file": plant_file,
    }
