"""Type definitions for ETA API."""

from datetime import datetime
from typing import TypedDict

from ..const import (  # noqa: TID252
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
    CUSTOM_UNIT_TIMESLOT,
    CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
    CUSTOM_UNIT_UNITLESS,
)


class ETAValidSwitchValues(TypedDict):
    """Dict providing the raw values for ETA switch sensors."""

    on_value: int
    off_value: int


class ETAValidWritableValues(TypedDict):
    """Dict providing the necessary metadata for ETA writable sensors."""

    scaled_min_value: float
    scaled_max_value: float
    scale_factor: int
    dec_places: int


class ETAEndpoint(TypedDict):
    """Dict providing metadata for a ETA sensor."""

    url: str
    value: float | str
    valid_values: dict | ETAValidSwitchValues | ETAValidWritableValues | None
    friendly_name: str
    unit: str
    endpoint_type: str
    is_writable: bool
    is_invalid: bool


class ETAError(TypedDict):
    """Dict encapsulating all available data of an ETA Error."""

    msg: str
    priority: str
    time: datetime
    text: str
    fub: str
    host: str
    port: int


# Sensor unit constants
FLOAT_SENSOR_UNITS = [
    "%",
    "A",
    "Hz",
    "Ohm",
    "Pa",
    "U/min",
    "V",
    "W",
    "W/m²",
    "bar",
    "kW",
    "kWh",
    "kg",
    "l",
    "l/min",
    "mV",
    "m²",
    "s",
    "°C",
    "%rH",
    "m³",
    "m³/h",
    CUSTOM_UNIT_UNITLESS,
]
# The inclusion of CUSTOM_UNIT_UNITLESS in FLOAT_SENSOR_UNITS will also detect the serial number as a float sensor,
# but there is no way to exclude only this single endpoint without hardcoding it
# If you want to handle it as a string you can add a template helper in HA to convert it to a string

WRITABLE_SENSOR_UNITS = [
    "%",
    "°C",
    "kg",
    "kW",
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
    CUSTOM_UNIT_TIMESLOT,
    CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
    CUSTOM_UNIT_UNITLESS,
]

# valid advTextOffset values to detect an endpoint as a switch
# we have to use a whitelist, and can't just use the number of validValues because some endpoints
# have just two valid values, but aren't switches at all
# for example the endopint `Warmwasserspeicher > Solarladung bis` has the values "Oben (2145)" and "Unten (2146)", but isn't a switch
VALID_SWITCH_OFFSET_VALUES = [
    1800,  # Nein/Ja
    1802,  # Aus/Ein
    1070,  # Nein/Ja, Notbetrieb
    1040,  # Aus/Ein, Diagnose
    950,  # Aus/Ein, Anforderung
]

# valid advTextOffset values to detect an endpoint as a switch, for v11
# (1040 is not always a switch with exactly 2 valid values, so it is excluded here
# because we have no way to determine if it is really a switch on v11)
VALID_SWITCH_OFFSET_VALUES_V11 = [
    1800,  # Nein/Ja
    1802,  # Aus/Ein
    1070,  # Nein/Ja, Notbetrieb
    950,  # Aus/Ein, Anforderung
]

DEFAULT_VALID_WRITABLE_VALUES = {
    "%": ETAValidWritableValues(
        scaled_min_value=-100,
        scaled_max_value=100,
        scale_factor=1,
        dec_places=0,
    ),
    "°C": ETAValidWritableValues(
        scaled_min_value=-100,
        scaled_max_value=200,
        scale_factor=1,
        dec_places=0,
    ),
    "kg": ETAValidWritableValues(
        scaled_min_value=-100000,
        scaled_max_value=100000,
        scale_factor=1,
        dec_places=0,
    ),
    "kW": ETAValidWritableValues(
        scaled_min_value=0,
        scaled_max_value=1000,
        scale_factor=1,
        dec_places=0,
    ),
}
