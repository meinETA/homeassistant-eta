"""Tests for API v1.3 permLevel-aware discovery (SensorDiscoveryV13)."""

from unittest.mock import AsyncMock

from aiohttp import ClientSession
from packaging import version
import pytest

from custom_components.eta_webservices.api import EtaAPI

API_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<eta version="1.0" xmlns="http://www.eta.co.at/rest/v1">'
    '<api version="1.3" uri="/user/api"/></eta>'
)

# 1.3 menu: fub carries type/defName, objects carry permLevel + isWritable.
MENU_XML = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<eta version="1.0" xmlns="http://www.eta.co.at/rest/v1"><menu uri="/user/menu">'
    '<fub uri="/264/10891" type="60" defName="ePE / Pelletsbrenner" name="Kessel">'
    '<object uri="/264/10891/0/0/12006" permLevel="USER" isWritable="0" name="Angeforderte Temperatur"/>'
    '<object uri="/264/10891/0/0/12111" permLevel="USER" isWritable="1" name="Zirkulation Laufzeit"/>'
    '<object uri="/264/10891/0/0/13001" permLevel="SERVICE" isWritable="0" name="Service Temperatur"/>'
    '<object uri="/264/10891/0/0/12080" permLevel="USER" isWritable="1" name="Ein/Aus Taste"/>'
    "</fub></menu></eta>"
)


def _varinfo(uri, name, unit, typ="DEFAULT", extra="", is_writable="0", offset="0"):
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<eta version="1.0" xmlns="http://www.eta.co.at/rest/v1">'
        f'<varInfo uri="/user/varinfo/{uri}">'
        f'<variable fullName="Kessel > {name}" scaleFactor="10" uri="{uri}" '
        f'name="{name}" decPlaces="0" advTextOffset="{offset}" unit="{unit}" '
        f'isWritable="{is_writable}">'
        f"<type>{typ}</type>{extra}</variable></varInfo></eta>"
    )


def _var(uri, unit, value="100", str_value="10,0"):
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<eta version="1.0" xmlns="http://www.eta.co.at/rest/v1">'
        f'<value scaleFactor="10" uri="/user/var/{uri}" decPlaces="0" '
        f'strValue="{str_value}" advTextOffset="0" unit="{unit}">{value}</value></eta>'
    )


MIN_MAX = (
    "<validValues>"
    "<min><value>0</value><strValue>0</strValue><advTextOffset>0</advTextOffset>"
    "<unit>s</unit><scaleFactor>10</scaleFactor><decPlaces>0</decPlaces>"
    "<text>0</text><min>0</min><max>6000</max><begin/><end/></min>"
    "<max><value>6000</value><strValue>600</strValue><advTextOffset>0</advTextOffset>"
    "<unit>s</unit><scaleFactor>10</scaleFactor><decPlaces>0</decPlaces>"
    "<text>6000</text><min>0</min><max>6000</max><begin/><end/></max>"
    "</validValues>"
)
# xmltodict expects #text nodes; build a simpler valid min/max the parser reads.
MIN_MAX = (
    "<validValues>"
    '<min unit="s" scaleFactor="10" decPlaces="0">0</min>'
    '<max unit="s" scaleFactor="10" decPlaces="0">6000</max>'
    "</validValues>"
)

SWITCH_VV = (
    "<validValues>"
    '<value strValue="Aus">1802</value>'
    '<value strValue="Ein">1803</value>'
    "</validValues>"
)

DATA = {
    "/user/api": API_XML,
    "/user/menu": MENU_XML,
    "/264/10891/0/0/12006": (
        _varinfo("264/10891/0/0/12006", "Angeforderte Temperatur", "°C"),
        _var("264/10891/0/0/12006", "°C", "445", "44,5"),
    ),
    "/264/10891/0/0/12111": (
        _varinfo(
            "264/10891/0/0/12111",
            "Zirkulation Laufzeit",
            "s",
            extra=MIN_MAX,
            is_writable="1",
        ),
        _var("264/10891/0/0/12111", "s", "100", "10,0"),
    ),
    "/264/10891/0/0/13001": (
        _varinfo("264/10891/0/0/13001", "Service Temperatur", "°C"),
        _var("264/10891/0/0/13001", "°C", "700", "70,0"),
    ),
    "/264/10891/0/0/12080": (
        _varinfo(
            "264/10891/0/0/12080",
            "Ein/Aus Taste",
            "",
            typ="TEXT",
            extra=SWITCH_VV,
            is_writable="1",
            offset="1802",
        ),
        _var("264/10891/0/0/12080", "", "1802", "Aus"),
    ),
}


def _lookup(suffix: str):
    if suffix in ("/user/api", "/user/menu"):
        return DATA[suffix]
    if suffix.startswith("/user/varinfo"):
        uri = "/" + suffix.split("/user/varinfo", 1)[1].lstrip("/")
        entry = DATA.get(uri)
        return entry[0] if entry else "<eta><error>x</error></eta>"
    if suffix.startswith("/user/var"):
        uri = "/" + suffix.split("/user/var", 1)[1].lstrip("/")
        entry = DATA.get(uri)
        return entry[1] if entry else "<eta><error>x</error></eta>"
    return "<eta><error>x</error></eta>"


@pytest.mark.asyncio
async def test_v13_discovery_permlevel_and_writable_without_unit_whitelist():
    """V13 tags permLevel/fub metadata and makes non-whitelist units writable."""
    api = EtaAPI(AsyncMock(spec=ClientSession), "192.168.0.25", 8080)
    # Force the v1.3 route via the real version methods.
    api.get_api_version = AsyncMock(return_value=version.parse("1.3"))

    async def mock_get_request(suffix):
        resp = AsyncMock()
        resp.text = AsyncMock(return_value=_lookup(suffix))
        return resp

    api._http.get_request = mock_get_request

    float_dict, switches_dict, text_dict, writable_dict, pending_dict = (
        {},
        {},
        {},
        {},
        {},
    )
    result = await api.get_all_sensors(
        False, float_dict, switches_dict, text_dict, writable_dict, pending_dict
    )
    assert result is True  # >= v1.2 route used

    # USER float temperature is discovered and tagged USER, with fub type/defName.
    user_temp = next(
        v for v in float_dict.values() if v["url"] == "/264/10891/0/0/12006"
    )
    assert user_temp["perm_level"] == "USER"
    assert user_temp["fub_type"] == "60"
    assert user_temp["fub_def_name"] == "ePE / Pelletsbrenner"

    # SERVICE read-only float is discovered and tagged SERVICE (flow filters it later).
    svc_temp = next(
        v for v in float_dict.values() if v["url"] == "/264/10891/0/0/13001"
    )
    assert svc_temp["perm_level"] == "SERVICE"

    # Key case: unit "s" is NOT in WRITABLE_SENSOR_UNITS, but isWritable=1 + a numeric
    # range makes it writable on 1.3 (whitelist bypassed).
    s_writable = [
        v for v in writable_dict.values() if v["url"] == "/264/10891/0/0/12111"
    ]
    assert len(s_writable) == 1
    assert s_writable[0]["unit"] == "s"
    assert s_writable[0]["perm_level"] == "USER"
    assert s_writable[0]["is_writable"] is True

    # The USER switch endpoint is discovered and tagged USER (category-agnostic:
    # a writable switch may land in switches and/or writable).
    all_eps = [
        v
        for d in (float_dict, switches_dict, text_dict, writable_dict)
        for v in d.values()
    ]
    switch_eps = [v for v in all_eps if v["url"] == "/264/10891/0/0/12080"]
    assert switch_eps, "switch endpoint 12080 not discovered"
    assert all(v["perm_level"] == "USER" for v in switch_eps)
