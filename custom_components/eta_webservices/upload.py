"""Send the stored raw plant data to the meinETA backend (button "Upload plant data").

The data is sealed (encrypted for the maintainers, see seal.py) before it leaves
Home Assistant; only a SHA-256 of the plaintext travels next to it, so the
server can skip a file it already has. A small proof of work (ALTCHA) protects
the server against floods.

Every config entry gets a random upload token on its first upload. The server
binds it to the instance UUID, so nobody else can overwrite the plant data of
this instance; the same token is the deletion code the user enters on
https://delete.meineta.net. It is kept in its own store, not in the config
entry (changing the entry would reload the integration) and never in the
diagnostics.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import re
import secrets
from typing import Any

from aiohttp import ClientError, ClientTimeout

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import translation
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.loader import async_get_integration
from homeassistant.util import dt as dt_util

from .const import DOMAIN, INSTANCE_UUID
from .seal import seal

UPLOAD_URL = "https://upload.meineta.net"
DELETE_URL = "https://delete.meineta.net"
STORAGE_VERSION = 1
TIMEOUT = ClientTimeout(total=120)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
# hass.data key of the running uploads, by config entry id
_RUNNING_KEY = f"{DOMAIN}_uploads_running"

_LOGGER = logging.getLogger(__name__)


def _store(hass: HomeAssistant, entry_id: str) -> Store[dict[str, Any]]:
    return Store(hass, STORAGE_VERSION, f"{DOMAIN}.upload_{entry_id}")


async def async_get_upload_info(hass: HomeAssistant, entry_id: str) -> dict[str, Any]:
    """Token (= deletion code) and the last upload of an entry; empty before the first upload."""
    return await _store(hass, entry_id).async_load() or {}


async def async_remove_upload_info(hass: HomeAssistant, entry_id: str) -> None:
    """Forget the upload token of a deleted entry."""
    await _store(hass, entry_id).async_remove()


def _solve(challenge: dict[str, Any]) -> str:
    """ALTCHA: find the number with sha256(salt + number) == challenge (runs in the executor)."""
    salt, target = str(challenge["salt"]), str(challenge["challenge"])
    for number in range(int(challenge["maxnumber"]) + 1):
        if hashlib.sha256(f"{salt}{number}".encode()).hexdigest() == target:
            payload = {
                "algorithm": challenge["algorithm"],
                "challenge": target,
                "number": number,
                "salt": salt,
                "signature": challenge["signature"],
            }
            return base64.b64encode(json.dumps(payload).encode()).decode()
    raise HomeAssistantError(translation_domain=DOMAIN, translation_key="upload_failed")


def _error(key: str, **placeholders: str) -> HomeAssistantError:
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders or None,
    )


async def async_upload_plant_file(
    hass: HomeAssistant, entry: ConfigEntry, data: dict[str, Any]
) -> dict[str, Any]:
    """Seal and send the raw plant data of an entry.

    :param data: the stored raw data ({"version", "instance_uuid", "collected_at", "responses"})
    :return: {"upload_id", "status" ("stored" or "unchanged"), "deletion_code"}
    :raises HomeAssistantError: no UUID, already running, or the server refused it
    """
    instance_uuid = str(data.get(INSTANCE_UUID) or "").lower()
    if not _UUID_RE.match(instance_uuid):
        raise _error("upload_no_uuid")

    running: set[str] = hass.data.setdefault(_RUNNING_KEY, set())
    if entry.entry_id in running:
        raise _error("upload_running")
    running.add(entry.entry_id)
    try:
        return await _async_upload(hass, entry, data, instance_uuid)
    finally:
        running.discard(entry.entry_id)


async def _async_upload(
    hass: HomeAssistant, entry: ConfigEntry, data: dict[str, Any], instance_uuid: str
) -> dict[str, Any]:
    store = _store(hass, entry.entry_id)
    info = await store.async_load() or {}
    if not info.get("token"):
        info["token"] = secrets.token_urlsafe(32)
        await store.async_save(info)

    plain = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
    sealed = await hass.async_add_executor_job(seal, plain)
    integration = await async_get_integration(hass, DOMAIN)
    session = async_get_clientsession(hass)

    try:
        async with session.get(f"{UPLOAD_URL}/challenge", timeout=TIMEOUT) as resp:
            if resp.status == 429:
                raise _error("upload_rate_limited")
            resp.raise_for_status()
            challenge = await resp.json()
        altcha = await hass.async_add_executor_job(_solve, challenge)
        body = {
            "instance_uuid": instance_uuid,
            "upload_token": info["token"],
            "sha256": hashlib.sha256(plain).hexdigest(),
            "sealed": sealed,
            "integration_version": str(integration.version or ""),
            "ha_version": HA_VERSION,
            "altcha": altcha,
        }
        async with session.post(
            f"{UPLOAD_URL}/upload", json=body, timeout=TIMEOUT
        ) as resp:
            answer = await resp.json(content_type=None)
            status = resp.status
    except HomeAssistantError:
        raise
    except (ClientError, TimeoutError, asyncio.TimeoutError, ValueError) as err:
        _LOGGER.warning("Plant data upload failed: %s", err)
        raise _error("upload_failed") from err

    if status == 403 and "token" in str(answer.get("error", "")):
        raise _error("upload_token_mismatch")
    if status == 429:
        raise _error("upload_rate_limited")
    if status not in (200, 201) or not answer.get("upload_id"):
        _LOGGER.warning("Plant data upload refused (%s): %s", status, answer)
        raise _error("upload_failed")

    info.update(
        last_upload_id=answer["upload_id"],
        last_upload_at=dt_util.utcnow().isoformat(timespec="seconds"),
    )
    await store.async_save(info)
    _LOGGER.info(
        "Plant data uploaded: %s (%s)", answer["upload_id"], answer.get("status")
    )
    return {
        "upload_id": answer["upload_id"],
        "status": answer.get("status", "stored"),
        "deletion_code": info["token"],
    }


_FALLBACK_TEXTS = {
    "upload_done_title": "ETA: plant data uploaded",
    "upload_done": (
        "Thank you! The plant data of {name} was sent (upload {upload_id}). "
        "It helps us to support more ETA systems.\n\n"
        "Should you ever want it deleted: Settings > Devices & services > "
        "ETA Heating > Configure > Plant data upload."
    ),
}


def upload_notification_id(entry_id: str) -> str:
    """Id of the notification shown after an upload."""
    return f"{DOMAIN}_upload_{entry_id}"


async def async_notify_uploaded(
    hass: HomeAssistant, entry: ConfigEntry, instance_uuid: str, result: dict[str, Any]
) -> None:
    """Tell the user that the upload worked, with the deletion code."""
    texts = await translation.async_get_translations(
        hass, hass.config.language, "exceptions", {DOMAIN}
    )
    values = {
        "name": entry.title,
        "upload_id": result["upload_id"],
    }

    def text(key: str) -> str:
        template = texts.get(
            f"component.{DOMAIN}.exceptions.{key}.message", _FALLBACK_TEXTS[key]
        )
        try:
            return template.format(**values)
        except (KeyError, IndexError, ValueError):
            return _FALLBACK_TEXTS[key].format(**values)

    persistent_notification.async_create(
        hass,
        text("upload_done"),
        title=text("upload_done_title"),
        notification_id=upload_notification_id(entry.entry_id),
    )
