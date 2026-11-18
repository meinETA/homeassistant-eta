"""Optional sidebar entry per plant showing the plant card full screen."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import frontend, websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store

from .card import CARD_JS_URL
from .const import DOMAIN, SIDEBAR_PANEL, STABLE_ID

_STORE = f"{DOMAIN}_panel_store"
_DATA = f"{DOMAIN}_panel_data"


async def async_setup_panels(hass: HomeAssistant) -> None:
    """Load the panel settings and register the websocket commands."""
    store: Store[dict[str, Any]] = Store(hass, 1, f"{DOMAIN}.panel")
    hass.data[_STORE] = store
    hass.data[_DATA] = await store.async_load() or {}
    websocket_api.async_register_command(hass, ws_panel_get)
    websocket_api.async_register_command(hass, ws_panel_save)


def panel_url(entry: ConfigEntry) -> str:
    """Return the sidebar url of an entry, based on its frozen stable id."""
    stable = entry.data.get(STABLE_ID) or str(entry.data.get(CONF_HOST, ""))
    return "eta-" + "".join(c if c.isalnum() else "-" for c in stable.lower())


def sidebar_enabled(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Return whether the entry shows a sidebar entry."""
    stored = hass.data[_DATA].get(entry.entry_id, {})
    return stored.get("sidebar", bool(entry.data.get(SIDEBAR_PANEL, False)))


def _save(hass: HomeAssistant) -> None:
    hass.data[_STORE].async_delay_save(lambda: hass.data[_DATA], 1)


@callback
def async_set_sidebar(hass: HomeAssistant, entry: ConfigEntry, enabled: bool) -> None:
    """Store the sidebar setting and apply it right away."""
    hass.data[_DATA].setdefault(entry.entry_id, {})["sidebar"] = enabled
    _save(hass)
    async_update_panel(hass, entry)


@callback
def async_update_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Register or remove the sidebar entry of a config entry."""
    url = panel_url(entry)
    frontend.async_remove_panel(hass, url, warn_if_unknown=False)
    if not sidebar_enabled(hass, entry):
        return
    # the plant name set via the gear wins over the entry title
    title = hass.data[_DATA].get(entry.entry_id, {}).get("card", {}).get("title")
    frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title=title or entry.title,
        sidebar_icon="mdi:fire",
        frontend_url_path=url,
        config={
            "_panel_custom": {
                "name": "eta-plant-panel",
                "js_url": hass.data[CARD_JS_URL],
                "embed_iframe": False,
                "trust_external": False,
            },
            "entry_id": entry.entry_id,
        },
        require_admin=False,
    )


@callback
def async_remove_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the sidebar entry (entry unloaded)."""
    frontend.async_remove_panel(hass, panel_url(entry), warn_if_unknown=False)


@callback
def async_forget_entry(hass: HomeAssistant, entry_id: str) -> None:
    """Drop the stored settings of a deleted config entry."""
    if hass.data.get(_DATA, {}).pop(entry_id, None) is not None:
        _save(hass)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/panel_config", vol.Required("entry_id"): str}
)
@callback
def ws_panel_get(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return the card settings of the sidebar panel."""
    stored = hass.data[_DATA].get(msg["entry_id"], {})
    connection.send_result(msg["id"], stored.get("card", {}))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/panel_config/save",
        vol.Required("entry_id"): str,
        vol.Required("config"): dict,
    }
)
@callback
def ws_panel_save(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Store the card settings of the sidebar panel (admins only)."""
    config = {
        k: v for k, v in msg["config"].items() if k in ("title", "language", "icons")
    }
    hass.data[_DATA].setdefault(msg["entry_id"], {})["card"] = config
    _save(hass)
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is not None and entry.domain == DOMAIN:
        async_update_panel(hass, entry)  # sidebar shows the new name
    connection.send_result(msg["id"], config)
