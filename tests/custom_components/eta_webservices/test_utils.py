"""Unit tests for utility functions."""

# pyright: reportTypedDictNotRequiredAccess=false

from custom_components.eta_webservices.const import DOMAIN
from custom_components.eta_webservices.utils import create_device_info


def test_create_device_info_with_device_name():
    """Device name is prefixed with 'ETA > ' and appended to the identifier."""
    info = create_device_info("192.168.1.10", "8080", "Kessel")
    assert info["name"] == "ETA > Kessel"
    assert (DOMAIN, "eta_192_168_1_10_8080_Kessel") in info["identifiers"]
    assert info["manufacturer"] == "ETA"
    assert info["configuration_url"] == "https://www.meineta.at"


def test_create_device_info_without_device_name():
    """Omitting device_name produces a plain 'ETA' name and shorter identifier."""
    info = create_device_info("192.168.1.10", "8080", None)
    assert info["name"] == "ETA"
    assert (DOMAIN, "eta_192_168_1_10_8080") in info["identifiers"]
    assert info["manufacturer"] == "ETA"
    assert info["configuration_url"] == "https://www.meineta.at"


def test_create_device_info_with_install_name():
    """The install name sits between the prefix and the part."""
    info = create_device_info("192.168.1.10", "8080", "Kessel", "Keller")
    assert info["name"] == "ETA > Keller > Kessel"
    assert (DOMAIN, "eta_192_168_1_10_8080_Kessel") in info["identifiers"]


def test_create_device_info_install_name_eta_is_not_repeated():
    """An install called "ETA" does not give "ETA > ETA > Kessel"; the identifier stays."""
    for name in ("ETA", "eta", " Eta "):
        info = create_device_info("192.168.1.10", "8080", "Kessel", name)
        assert info["name"] == "ETA > Kessel"
        assert (DOMAIN, "eta_192_168_1_10_8080_Kessel") in info["identifiers"]
    assert create_device_info("192.168.1.10", "8080", None, "ETA")["name"] == "ETA"
