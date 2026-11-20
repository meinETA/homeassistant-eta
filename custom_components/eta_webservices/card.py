"""Dashboard card: static files, frontend registration and topology API."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN
from .topology import async_get_report, async_get_topology

CARD_URL_BASE = f"/{DOMAIN}_static"
CARD_FILE = "eta-plant-card.js"
CARD_JS_URL = f"{DOMAIN}_card_js_url"
_WWW = Path(__file__).parent / "www"


async def async_setup_card(hass: HomeAssistant, version: str) -> None:
    """Serve the card bundle and load it in every dashboard."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_BASE, str(_WWW), cache_headers=False)]
    )
    # Content hash in the URL: browsers reload the card whenever it changes.
    digest = await hass.async_add_executor_job(_file_digest, _WWW / CARD_FILE)
    hass.data[CARD_JS_URL] = f"{CARD_URL_BASE}/{CARD_FILE}?v={version}-{digest}"
    add_extra_js_url(hass, hass.data[CARD_JS_URL])
    websocket_api.async_register_command(hass, ws_topology)
    websocket_api.async_register_command(hass, ws_report)


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:8]


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/topology"})
@callback
def ws_topology(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the detected plant topology of all ETA entries."""
    connection.send_result(msg["id"], async_get_topology(hass))


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/report",
        vol.Optional("entry_id"): str,
        vol.Optional("manual", default=[]): [[str]],
    }
)
@callback
def ws_report(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the anonymized plant report (no names, ids or values)."""
    connection.send_result(
        msg["id"], async_get_report(hass, msg.get("entry_id"), msg["manual"])
    )
