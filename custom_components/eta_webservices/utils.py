"""Various utility functions."""

from homeassistant.helpers.device_registry import DeviceInfo

from .const import CUSTOM_UNIT_UNITLESS, DOMAIN


def create_device_info(
    host: str, port: str, fub_name: str | None, install_name: str | None = None
) -> DeviceInfo:
    """Build the DeviceInfo shared by all entities of an install.

    Identifier is host/port/FUB only, so it stays stable when the install name
    changes (else a rename orphans the old devices). The "ETA > " prefix stops
    the frontend stripping the device name from entity names.
    """
    identifier = f"eta_{host.replace('.', '_')}_{port}" + (
        f"_{fub_name}" if fub_name else ""
    )
    parts = " · ".join(p for p in (install_name, fub_name) if p)
    eta_device_name = f"ETA > {parts}" if parts else "ETA"

    return DeviceInfo(
        identifiers={(DOMAIN, identifier)},
        name=eta_device_name,
        manufacturer="ETA",
        configuration_url="https://www.meineta.at",
    )


def get_native_unit(unit):
    """Convert ETA API units to Home Assistant native units."""
    if unit == "%rH":
        return "%"
    if unit == "":
        return None
    if unit == CUSTOM_UNIT_UNITLESS:
        return None
    return unit
