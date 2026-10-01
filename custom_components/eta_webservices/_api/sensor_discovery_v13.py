"""API v1.3 specific sensor discovery implementation.

Builds on the v1.2 discovery. On API 1.3 the /user/menu response carries a
permLevel and isWritable per node and a type/defName per fub. This class attaches
that metadata to each endpoint and relaxes the unit-whitelist gate for writability,
so writable endpoints with units outside WRITABLE_SENSOR_UNITS (e.g. "s") are
handled. It changes nothing about #4/#5 behavior it inherits from v1.2.

permLevel gating (USER vs SERVICE) is NOT applied here: discovery tags every
endpoint with its permLevel and the config flow decides visibility/writability
based on the user's service toggles.
"""

import logging

from .sensor_discovery_v12 import SensorDiscoveryV12

_LOGGER = logging.getLogger(__name__)


class SensorDiscoveryV13(SensorDiscoveryV12):
    """ETA API v1.3 specific sensor discovery implementation."""

    def _parse_valid_values(self, unit: str, data: dict, uri: str):
        """Build a writable range even for units outside the whitelist on 1.3.

        v1.2 only builds the min/max range when the unit is in WRITABLE_SENSOR_UNITS.
        On 1.3 the menu tells us what is writable via isWritable, so build the range
        whenever the varinfo exposes a numeric min/max and the node is writable.
        """
        valid_values = super()._parse_valid_values(unit, data, uri)
        if isinstance(valid_values, dict) and "scaled_min_value" in valid_values:
            return valid_values
        raw = data.get("validValues")
        if (
            data.get("@isWritable") == "1"
            and isinstance(raw, dict)
            and isinstance(raw.get("min"), dict)
            and "#text" in raw["min"]
            and isinstance(raw.get("max"), dict)
            and "#text" in raw["max"]
        ):
            return self._createETAValidWritableValues(
                raw_min_value=raw["min"]["#text"],
                raw_max_value=raw["max"]["#text"],
                scale_factor=int(data["@scaleFactor"]),
                dec_places=int(data["@decPlaces"]),
            )
        return valid_values

    def _parse_varinfo(self, data, fub: str, uri: str, var_data_entry):
        """Parse varinfo and attach the API 1.3 menu metadata for this node."""
        endpoint = super()._parse_varinfo(data, fub, uri, var_data_entry)
        meta = self._http.node_meta.get(uri)
        if meta:
            endpoint["perm_level"] = meta.get("perm_level")
            endpoint["fub_type"] = meta.get("fub_type")
            endpoint["fub_def_name"] = meta.get("fub_def_name")
        return endpoint

    def _is_writable(self, endpoint_info) -> bool:
        """Writable on 1.3 = menu isWritable plus a numeric range (no unit whitelist).

        permLevel gating is applied later in the config flow, not here.
        """
        valid_values = endpoint_info["valid_values"]
        return (
            bool(endpoint_info["is_writable"])
            and valid_values is not None
            and "scaled_min_value" in valid_values
        )
