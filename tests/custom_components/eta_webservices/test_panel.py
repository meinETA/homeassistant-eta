"""Tests for the sidebar panel."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.eta_webservices import panel
from custom_components.eta_webservices.const import DOMAIN, SIDEBAR_PANEL, STABLE_ID


def _entry(**data):
    return MockConfigEntry(domain=DOMAIN, title="Keller", data=data)


def test_panel_url_uses_stable_id():
    """Sidebar url follows the frozen stable id."""
    assert panel.panel_url(_entry(**{STABLE_ID: "keller_haus"})) == "eta-keller-haus"
    assert panel.panel_url(_entry(host="192.168.0.5")) == "eta-192-168-0-5"


def test_sidebar_default_and_override(hass):
    """Off for existing installs, on for new ones, stored choice wins."""
    hass.data[panel._DATA] = {}
    old = _entry(**{STABLE_ID: "a"})
    new = _entry(**{STABLE_ID: "b", SIDEBAR_PANEL: True})
    assert not panel.sidebar_enabled(hass, old)  # existing installs: off
    assert panel.sidebar_enabled(hass, new)  # new installs: on
    hass.data[panel._DATA][new.entry_id] = {"sidebar": False}
    assert not panel.sidebar_enabled(hass, new)
