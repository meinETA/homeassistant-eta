"""Values reported as `xxx` with a valid raw state are not offline nodes."""

from custom_components.eta_webservices._api.sensor_discovery_v12 import (
    SensorDiscoveryV12,
)

SWITCH = {"Aus": 1802, "Ein": 1803}


def test_xxx_with_valid_switch_state_is_kept() -> None:
    """FWM "Ein/Aus Taste": text `xxx`, raw 1803 (Ein)."""
    raw = {"@strValue": "xxx", "#text": "1803"}
    assert SensorDiscoveryV12._raw_in_valid_values(raw, SWITCH)


def test_xxx_without_valid_state_stays_invalid() -> None:
    """Offline node: raw value outside the valid values, or no discrete values."""
    assert not SensorDiscoveryV12._raw_in_valid_values(
        {"@strValue": "xxx", "#text": "0"}, SWITCH
    )
    assert not SensorDiscoveryV12._raw_in_valid_values(
        {"@strValue": "xxx", "#text": "1803"}, None
    )
    assert not SensorDiscoveryV12._raw_in_valid_values(
        {"@strValue": "xxx", "#text": "5"}, {"scaled_min_value": 0}
    )
