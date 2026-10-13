"""Tests for the API 1.3 permLevel upgrade repair issue."""

from unittest.mock import AsyncMock, MagicMock

import pytest

import custom_components.eta_webservices as eta_init
from custom_components.eta_webservices.const import (
    MAX_PARALLEL_REQUESTS,
    REQUEST_SEMAPHORE,
    SUPPORTS_PERM_LEVEL,
)


def _config(supports=False):
    return {
        SUPPORTS_PERM_LEVEL: supports,
        MAX_PARALLEL_REQUESTS: 5,
        REQUEST_SEMAPHORE: MagicMock(),
        "host": "127.0.0.1",
        "port": 8081,
    }


def _patch(monkeypatch, supports_perm_level_api: bool):
    monkeypatch.setattr(eta_init, "async_get_clientsession", lambda hass: MagicMock())
    fake_api = MagicMock()
    fake_api.supports_perm_level_api = AsyncMock(return_value=supports_perm_level_api)
    monkeypatch.setattr(eta_init, "EtaAPI", lambda *a, **k: fake_api)
    created, deleted = [], []
    monkeypatch.setattr(
        eta_init.ir,
        "async_create_issue",
        lambda hass, domain, issue_id, **kw: created.append(issue_id),
    )
    monkeypatch.setattr(
        eta_init.ir,
        "async_delete_issue",
        lambda hass, domain, issue_id: deleted.append(issue_id),
    )
    return created, deleted


@pytest.mark.asyncio
async def test_upgrade_issue_created_when_boiler_is_v13(monkeypatch):
    """A pre-1.3 entry talking to a 1.3 boiler gets the upgrade issue."""
    created, _ = _patch(monkeypatch, supports_perm_level_api=True)
    entry = MagicMock(entry_id="e1")
    await eta_init._maybe_create_perm_level_upgrade_issue(
        MagicMock(), entry, _config(supports=False)
    )
    assert created == ["perm_level_upgrade_e1"]


@pytest.mark.asyncio
async def test_no_issue_when_boiler_is_not_v13(monkeypatch):
    """No issue when the boiler is still on API < 1.3."""
    created, _ = _patch(monkeypatch, supports_perm_level_api=False)
    entry = MagicMock(entry_id="e1")
    await eta_init._maybe_create_perm_level_upgrade_issue(
        MagicMock(), entry, _config(supports=False)
    )
    assert created == []


@pytest.mark.asyncio
async def test_issue_cleared_when_already_perm_level_aware(monkeypatch):
    """An entry already permLevel-aware clears any stale issue and probes nothing."""
    created, deleted = _patch(monkeypatch, supports_perm_level_api=True)
    entry = MagicMock(entry_id="e1")
    await eta_init._maybe_create_perm_level_upgrade_issue(
        MagicMock(), entry, _config(supports=True)
    )
    assert created == []
    assert deleted == ["perm_level_upgrade_e1"]
