"""Tests for the plant data upload."""

import base64
from contextlib import asynccontextmanager, contextmanager
import hashlib
import json
import re
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from custom_components.eta_webservices import upload
from custom_components.eta_webservices.const import INSTANCE_UUID
from homeassistant.exceptions import HomeAssistantError

UUID = "0b6f3c1e-6c55-4f4e-9a52-6d1f0d7a7e10"
DATA = {
    "version": 1,
    INSTANCE_UUID: UUID,
    "collected_at": "2026-11-24T10:00:00+00:00",
    "responses": {"/user/menu": "<menu/>"},
}


def _challenge(number: int = 7, maxnumber: int = 50) -> dict:
    salt = "abc?expires=9999999999"
    return {
        "algorithm": "SHA-256",
        "challenge": hashlib.sha256(f"{salt}{number}".encode()).hexdigest(),
        "maxnumber": maxnumber,
        "salt": salt,
        "signature": "sig",
    }


class _Response:
    def __init__(self, status: int, body: dict) -> None:
        self.status = status
        self._body = body

    async def json(self, content_type=None):
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise upload.ClientError(f"status {self.status}")


class _Session:
    """aiohttp session double: GET /challenge, POST /upload."""

    def __init__(self, status: int, body: dict) -> None:
        self.answer = _Response(status, body)
        self.posted: dict | None = None

    @asynccontextmanager
    async def get(self, url, timeout=None):
        assert url.endswith("/challenge")
        yield _Response(200, _challenge())

    @asynccontextmanager
    async def post(self, url, json=None, timeout=None):
        assert url.endswith("/upload")
        self.posted = json
        yield self.answer


def _hass():
    hass = MagicMock()
    hass.data = {}
    hass.async_add_executor_job = AsyncMock(side_effect=lambda func, *args: func(*args))
    return hass


def _entry():
    entry = Mock()
    entry.entry_id = "entry1"
    entry.title = "ETA Boiler"
    return entry


def _store(data=None):
    store = Mock()
    store.async_load = AsyncMock(return_value=data)
    store.async_save = AsyncMock()
    return store


@contextmanager
def _patched(session, store):
    integration = Mock()
    integration.version = "2.2.0"
    with (
        patch.object(upload, "_store", return_value=store),
        patch.object(upload, "async_get_clientsession", return_value=session),
        patch.object(
            upload, "async_get_integration", AsyncMock(return_value=integration)
        ),
    ):
        yield


def test_solve_finds_the_number():
    """The proof of work payload carries the number that hashes to the challenge."""
    payload = json.loads(
        base64.b64decode(upload._solve(_challenge(number=42, maxnumber=100)))
    )
    assert payload["number"] == 42
    assert payload["signature"] == "sig"


async def test_upload_creates_token_and_sends_sealed_data():
    """First upload: a token is created and stored, the data leaves sealed with its hash."""
    session = _Session(201, {"status": "stored", "upload_id": "U-0123456789ab"})
    store = _store(None)
    with _patched(session, store):
        result = await upload.async_upload_plant_file(_hass(), _entry(), DATA)

    body = session.posted
    token = body["upload_token"]
    assert len(token) >= 32
    assert result == {"upload_id": "U-0123456789ab", "status": "stored"}
    assert body["instance_uuid"] == UUID
    assert body["integration_version"] == "2.2.0"
    assert base64.b64decode(body["sealed"])[:4] == b"ETA1"
    assert b"<menu/>" not in base64.b64decode(body["sealed"])
    saved = store.async_save.await_args.args[0]
    assert saved["token"] == token
    assert saved["last_upload_id"] == "U-0123456789ab"
    assert re.fullmatch(r"[23456789A-HJKMNP-Z]{6}", saved["code"])
    assert token not in json.dumps(result)


async def test_deletion_code_travels_sealed():
    """The short deletion code is inside the sealed data, the hash covers it."""
    session = _Session(201, {"status": "stored", "upload_id": "U-0123456789ab"})
    sealed_plain: list[bytes] = []

    def fake_seal(plain: bytes) -> str:
        sealed_plain.append(plain)
        return base64.b64encode(b"ETA1" + b"x" * 64).decode()

    with (
        _patched(session, _store({"token": "t" * 43, "code": "K7MQ2X"})),
        patch.object(upload, "seal", fake_seal),
    ):
        await upload.async_upload_plant_file(_hass(), _entry(), DATA)

    plain = sealed_plain[0]
    assert json.loads(plain) == {**DATA, "deletion_code": "K7MQ2X"}
    assert session.posted["sha256"] == hashlib.sha256(plain).hexdigest()
    assert "K7MQ2X" not in json.dumps(session.posted)


async def test_deletion_code_is_created_once():
    """The code exists before the first upload and stays the same."""
    store = _store(None)
    with patch.object(upload, "_store", return_value=store):
        info = await upload.async_get_upload_info(_hass(), "entry1")
    code = info["code"]
    assert re.fullmatch(r"[23456789A-HJKMNP-Z]{6}", code)
    store.async_save.assert_awaited_once()

    store = _store({"code": code})
    with patch.object(upload, "_store", return_value=store):
        info = await upload.async_get_upload_info(_hass(), "entry1")
    assert info["code"] == code
    store.async_save.assert_not_awaited()


async def test_upload_reuses_stored_token():
    """Later uploads send the token of the first one."""
    session = _Session(200, {"status": "unchanged", "upload_id": "U-0123456789ab"})
    with _patched(session, _store({"token": "t" * 43})):
        result = await upload.async_upload_plant_file(_hass(), _entry(), DATA)

    assert session.posted["upload_token"] == "t" * 43
    assert result["status"] == "unchanged"


@pytest.mark.parametrize(
    ("status", "body", "key"),
    [
        pytest.param(
            403,
            {"error": "upload token does not match this instance"},
            "upload_token_mismatch",
            id="token",
        ),
        pytest.param(
            429, {"error": "too many requests"}, "upload_rate_limited", id="rate"
        ),
        pytest.param(
            400,
            {"error": "not a sealed plant file (ETA1)"},
            "upload_failed",
            id="refused",
        ),
    ],
)
async def test_upload_errors(status, body, key):
    """Refusals of the server reach the user as translated errors."""
    with (
        _patched(_Session(status, body), _store({"token": "t" * 43})),
        pytest.raises(HomeAssistantError) as err,
    ):
        await upload.async_upload_plant_file(_hass(), _entry(), DATA)
    assert err.value.translation_key == key


async def test_upload_needs_uuid():
    """Without an instance UUID nothing is sent."""
    session = _Session(201, {"upload_id": "U-0123456789ab"})
    with _patched(session, _store(None)), pytest.raises(HomeAssistantError) as err:
        await upload.async_upload_plant_file(
            _hass(), _entry(), {**DATA, INSTANCE_UUID: ""}
        )
    assert err.value.translation_key == "upload_no_uuid"
    assert session.posted is None


async def test_upload_runs_once_per_entry():
    """A second press while an upload runs is refused."""
    hass = _hass()
    hass.data[upload._RUNNING_KEY] = {"entry1"}
    with (
        _patched(_Session(201, {}), _store(None)),
        pytest.raises(HomeAssistantError) as err,
    ):
        await upload.async_upload_plant_file(hass, _entry(), DATA)
    assert err.value.translation_key == "upload_running"


async def test_running_flag_is_cleared_after_failure():
    """A failed upload does not block the next press."""
    hass = _hass()
    with (
        _patched(_Session(400, {"error": "x"}), _store({"token": "t" * 43})),
        pytest.raises(HomeAssistantError),
    ):
        await upload.async_upload_plant_file(hass, _entry(), DATA)
    assert hass.data[upload._RUNNING_KEY] == set()


async def test_upload_entry_needs_collected_data():
    """Before the raw data is collected, the button says "not ready"."""
    entry = _entry()
    with (
        patch.object(upload, "async_get_raw_data", AsyncMock(return_value=None)),
        pytest.raises(HomeAssistantError) as err,
    ):
        await upload.async_upload_entry(_hass(), entry)
    assert err.value.translation_key == "upload_not_ready"


async def test_upload_entry_uploads_and_notifies():
    """With data, the entry is uploaded and the user is told."""
    entry = _entry()
    notify = AsyncMock()
    with (
        patch.object(upload, "async_get_raw_data", AsyncMock(return_value=DATA)),
        patch.object(
            upload,
            "async_upload_plant_file",
            AsyncMock(return_value={"upload_id": "U-1", "status": "stored"}),
        ),
        patch.object(upload, "async_notify_uploaded", notify),
    ):
        result = await upload.async_upload_entry(_hass(), entry)
    assert result == {"upload_id": "U-1", "status": "stored"}
    notify.assert_awaited_once()
    assert notify.await_args.args[2] == UUID
