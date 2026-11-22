"""Terminal part of the plant file: menu, API version and what the discovery left out.

The plant file (card "Download plant file", diagnostics) contains every endpoint
the discovery found. For improving the discovery itself this adds, read live
from the terminal when the file is created:

- the API version,
- the whole menu (every node, also folders and endpoints the discovery skipped),
- the variable info of skipped endpoints (unit, type, scale, text offset, valid
  values) so it is visible why they were skipped.

Function block names (renamable on the terminal) and free texts are left out.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import xmltodict

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

_LOGGER = logging.getLogger(__name__)

# keep the button responsive on slow terminals
SKIPPED_MAX = 150
TIMEOUT = 60
# variable attributes that explain how the discovery treats an endpoint
_VAR_KEYS = ("unit", "decPlaces", "scaleFactor", "advTextOffset", "isWritable")


def flatten_menu(menu: dict[str, Any]) -> list[dict[str, Any]]:
    """Every menu node as {uri, path, leaf}; path below the function block."""
    rows: list[dict[str, Any]] = []

    def walk(node: Any, path: list[str]) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item, path)
            return
        if not isinstance(node, dict):
            return
        children = node.get("object")
        name = str(node.get("@name") or "")
        uri = str(node.get("@uri") or "").strip("/")
        here = [*path, name] if path is not None else []
        if uri:
            rows.append(
                {"uri": uri, "path": " > ".join(here) or None, "leaf": not children}
            )
        if children:
            walk(children, here)

    fubs = (((menu or {}).get("eta") or {}).get("menu") or {}).get("fub") or []
    for fub in fubs if isinstance(fubs, list) else [fubs]:
        uri = str(fub.get("@uri") or "").strip("/")
        if uri:
            rows.append({"uri": uri, "path": None, "leaf": False, "fub": True})
        walk(fub.get("object"), [])  # block name left out
    return rows


def var_details(xml: str) -> dict[str, Any]:
    """Attributes, type and valid values of a varinfo answer (no free texts)."""
    data = xmltodict.parse(xml)
    var = (((data.get("eta") or {}).get("varInfo") or {}).get("variable")) or {}
    out: dict[str, Any] = {k: var.get(f"@{k}") for k in _VAR_KEYS if f"@{k}" in var}
    if "type" in var:
        out["type"] = var["type"]
    valid = var.get("validValues")
    if isinstance(valid, dict):
        keep: dict[str, Any] = {}
        for key in ("min", "max", "def"):
            if isinstance(valid.get(key), dict):
                keep[key] = valid[key].get("#text")
        values = valid.get("value")
        if values:
            values = values if isinstance(values, list) else [values]
            keep["values"] = {
                v.get("@strValue"): v.get("#text")
                for v in values
                if isinstance(v, dict)
            }
        out["valid"] = keep
    return out


async def async_terminal_info(
    hass: HomeAssistant, entry_id: str, found: set[str]
) -> dict[str, Any]:
    """API version, menu and details of skipped endpoints; errors are reported."""
    config = (hass.data.get(DOMAIN) or {}).get(entry_id) or {}
    if not config.get(CONF_HOST):
        return {"error": "integration not loaded"}
    api = EtaAPI(
        async_get_clientsession(hass),
        config[CONF_HOST],
        config.get(CONF_PORT),
        max_concurrent_requests=config.get(
            MAX_PARALLEL_REQUESTS, DEFAULT_MAX_PARALLEL_REQUESTS
        ),
        request_semaphore=config.get(REQUEST_SEMAPHORE),
    )
    info: dict[str, Any] = {}
    try:
        info["api_version"] = str(
            await asyncio.wait_for(api.get_api_version(), TIMEOUT)
        )
        menu = flatten_menu(await asyncio.wait_for(api.get_menu(), TIMEOUT))
    except Exception as err:  # noqa: BLE001 - report it, the file stays useful
        info["error"] = f"{type(err).__name__}: {err}"
        return info
    info["menu"] = menu
    skipped = [r["uri"] for r in menu if r["leaf"] and r["uri"] not in found]
    info["skipped_count"] = len(skipped)

    async def details(uri: str) -> tuple[str, Any]:
        try:
            response = await api._http.get_request(f"/user/varinfo/{uri}")  # noqa: SLF001
            return uri, var_details(await response.text())
        except Exception as err:  # noqa: BLE001
            return uri, {"error": type(err).__name__}

    # slow terminals: keep what arrived within the time limit
    tasks = [asyncio.ensure_future(details(u)) for u in skipped[:SKIPPED_MAX]]
    done, pending = (
        await asyncio.wait(tasks, timeout=TIMEOUT) if tasks else (set(), set())
    )
    for task in pending:
        task.cancel()
    info["skipped"] = dict(sorted(t.result() for t in done))
    if pending:
        info["skipped_timeout"] = len(pending)
    return info
