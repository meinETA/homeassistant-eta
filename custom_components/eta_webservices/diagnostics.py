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
from .topology import async_get_topology
from .utils.raw_data import async_get_raw_data

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
    api_version = await eta_client.get_api_version()

    topology = next(
        (t for t in async_get_topology(hass) if t["entry_id"] == entry.entry_id),
        None,
    )

    return {
        "config": async_redact_data(
            {k: v for k, v in config.items() if k != REQUEST_SEMAPHORE}, TO_REDACT
        ),
        "api_version": str(api_version),
        "topology": topology,
        "raw_responses": await async_get_raw_data(hass, entry),
    }
