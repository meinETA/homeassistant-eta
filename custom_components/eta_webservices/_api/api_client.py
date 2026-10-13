"""HTTP client for ETA API communication."""

import asyncio
from datetime import datetime
import logging

from aiohttp import ClientSession
import xmltodict

from .types import FLOAT_SENSOR_UNITS, ETAError

_LOGGER = logging.getLogger(__name__)


class APIClient:
    """Handles low-level HTTP and XML operations for ETA API."""

    def __init__(
        self,
        session: ClientSession,
        host: str,
        port: int,
        max_concurrent_requests: int = 5,
        request_semaphore: asyncio.Semaphore | None = None,
    ) -> None:
        """Initialize HTTP client.

        :param session: aiohttp ClientSession for HTTP requests
        :param host: Hostname or IP address of the ETA device
        :param port: Port number of the ETA API
        """
        self._session = session
        self._host = host
        self._port = int(port)
        self._max_concurrent_requests = max(1, int(max_concurrent_requests))
        self._request_semaphore = request_semaphore or asyncio.Semaphore(
            self._max_concurrent_requests
        )
        self._num_duplicates = 0
        # API 1.3 menu metadata from the last get_sensors_dict() walk, keyed by node
        # uri: {perm_level, is_writable, fub_type, fub_def_name}. Empty/all-None on 1.1/1.2.
        self._node_meta: dict[str, dict] = {}

    def _build_uri(self, suffix: str) -> str:
        """Build full URI from suffix."""
        return f"http://{self._host}:{self._port}{suffix}"

    async def get_request(self, suffix: str):
        """Execute GET request."""
        async with self._request_semaphore:
            return await self._session.get(self._build_uri(suffix))

    async def post_request(self, suffix: str, data: dict):
        """Execute POST request."""
        async with self._request_semaphore:
            return await self._session.post(self._build_uri(suffix), data=data)

    def _record_node_meta(self, node: dict, fub_type, fub_def_name) -> None:
        """Capture API 1.3 menu metadata for a node (values are None on 1.1/1.2)."""
        uri = node.get("@uri")
        if not uri:
            return
        is_writable = node.get("@isWritable")
        self._node_meta[uri] = {
            "perm_level": node.get("@permLevel"),
            "is_writable": (is_writable == "1") if is_writable is not None else None,
            "fub_type": fub_type,
            "fub_def_name": fub_def_name,
        }

    def _evaluate_xml_dict(
        self,
        xml_dict,
        uri_dict: dict,
        prefix: str = "",
        fub_type=None,
        fub_def_name=None,
    ):
        """Recursively evaluate XML dictionary and extract URIs.

        Also captures API 1.3 per-node metadata (permLevel, isWritable) and the
        containing fub's type/defName, inherited downward. All absent on 1.1/1.2.
        """
        if isinstance(xml_dict, list):
            for child in xml_dict:
                self._evaluate_xml_dict(child, uri_dict, prefix, fub_type, fub_def_name)
        elif "object" in xml_dict:
            child = xml_dict["object"]
            new_prefix = f"{prefix}_{xml_dict['@name']}"
            # a fub carries type/defName; inherit it to all descendant objects
            cur_type = xml_dict.get("@type", fub_type)
            cur_def_name = xml_dict.get("@defName", fub_def_name)
            # Store multiple URIs per key
            if new_prefix not in uri_dict:
                uri_dict[new_prefix] = []
            else:
                self._num_duplicates += 1
            # add parent to uri_dict and then evaluate the children
            if (uri := xml_dict["@uri"]) not in uri_dict[new_prefix]:
                uri_dict[new_prefix].append(uri)
            self._record_node_meta(xml_dict, cur_type, cur_def_name)
            self._evaluate_xml_dict(child, uri_dict, new_prefix, cur_type, cur_def_name)
        else:
            key = f"{prefix}_{xml_dict['@name']}"
            if key not in uri_dict:
                uri_dict[key] = []
            else:
                self._num_duplicates += 1
            if (uri := xml_dict["@uri"]) not in uri_dict[key]:
                uri_dict[key].append(uri)
            self._record_node_meta(xml_dict, fub_type, fub_def_name)

    async def get_menu(self):
        """Request the menu from the ETA API."""
        data = await self.get_request("/user/menu")
        text = await data.text()
        return xmltodict.parse(text)

    async def _get_raw_sensor_dict(self):
        """Get raw sensor dictionary from menu."""
        data = await self.get_menu()
        return data["eta"]["menu"]["fub"]

    async def get_sensors_dict(self):
        """Get flattened sensor dictionary with URIs."""
        raw_dict = await self._get_raw_sensor_dict()
        uri_dict = {}
        self._node_meta = {}
        self._evaluate_xml_dict(raw_dict, uri_dict)
        return uri_dict

    def parse_data(
        self,
        data: dict,
        force_number_handling: bool = False,
        force_string_handling: bool = False,
    ) -> tuple[float | str, str]:
        """Parse data from ETA API response.

        :param data: XML data dict
        :param force_number_handling: Force numeric parsing
        :param force_string_handling: Force string parsing
        :param float_sensor_units: List of units that should be parsed as floats
        :return: Tuple of (value, unit)
        """
        _LOGGER.debug("Parsing data %s", data)
        unit = data["@unit"]
        if not force_string_handling and (
            unit in FLOAT_SENSOR_UNITS or force_number_handling
        ):
            scale_factor = int(data["@scaleFactor"])
            # ignore the decPlaces to avoid removing any additional precision the API values may have
            # i.e. the API may send a value of 444 with scaleFactor=10, but set decPlaces=0,
            # which would remove the decimal places and set the value to 44 instead of 44.4
            raw_value = float(data["#text"])
            value = raw_value / scale_factor
        else:
            value = data["@strValue"]
        return value, unit

    async def get_data_plus_raw(self, uri: str) -> tuple[float | str, str, dict]:
        """Get data with raw XML dict.

        :param uri: URI suffix
        :param float_sensor_units: List of units for float parsing
        :return: Tuple of (value, unit, raw_dict)
        """
        data = await self.get_request("/user/var/" + str(uri))
        text = await data.text()
        data = xmltodict.parse(text)["eta"]["value"]
        value, unit = self.parse_data(data)
        return value, unit, data

    async def get_data(
        self, uri, force_number_handling=False, force_string_handling=False
    ) -> tuple[float | str, str]:
        """Request the data from a API URL.

        :param uri: ETA API url suffix, like /120/1/123
        :param force_number_handling: Set to true if the data should be treated as a number even if its unit is not in the list of valid float sensors
        :param force_string_handling: Set to true if the data should be treated as a string regardless of its unit
        :return: Parsed data as a Tuple[Value, Unit]
        :rtype: Tuple[Any,str]
        """
        data = await self.get_request("/user/var/" + str(uri))
        text = await data.text()
        data = xmltodict.parse(text)["eta"]["value"]
        return self.parse_data(
            data,
            force_number_handling=force_number_handling,
            force_string_handling=force_string_handling,
        )

    async def get_all_data(self, sensor_list: dict[str, dict[str, bool]]):
        """Get all data from all endpoints.

        :param sensor_list: Dict[url, Dict[str, bool]] of sensors to query the data for
        :return: List of all data
        :rtype: Dict[str, Any]
        """

        tasks = [
            self.get_data(
                uri,
                force_number_handling=force_handlings.get(
                    "force_number_handling", False
                ),
                force_string_handling=force_handlings.get(
                    "force_string_handling", False
                ),
            )
            for uri, force_handlings in sensor_list.items()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        data_dict: dict[str, float | str] = {}
        for uri, result in zip(sensor_list.keys(), results, strict=False):
            if isinstance(result, BaseException):
                _LOGGER.debug("Failed to get data for %s: %s", uri, str(result))
            else:
                data_dict[uri] = result[0]  # extract value from (value, unit) tuple

        return data_dict

    def parse_errors(self, data) -> list[ETAError]:
        """Parse error data from ETA API.

        :param data: Error data from API
        :param host: Hostname for error dict
        :param port: Port for error dict
        :return: List of ETAError dicts
        """
        errors: list[ETAError] = []
        if isinstance(data, dict):
            data = [data]

        for fub in data:
            fub_name = fub.get("@name", "")
            fub_errors = fub.get("error", [])
            if isinstance(fub_errors, dict):
                fub_errors = [fub_errors]
            errors.extend(
                ETAError(
                    msg=error["@msg"],
                    priority=error["@priority"],
                    time=datetime.strptime(error["@time"], "%Y-%m-%d %H:%M:%S")
                    if error.get("@time", "") != ""
                    else datetime.now(),
                    text=error["#text"],
                    fub=fub_name,
                    host=self._host,
                    port=self._port,
                )
                for error in fub_errors
            )

        return errors

    @property
    def host(self) -> str:
        """Get host."""
        return self._host

    @property
    def node_meta(self) -> dict[str, dict]:
        """API 1.3 menu metadata from the last get_sensors_dict() walk (uri -> dict)."""
        return self._node_meta

    @property
    def num_duplicates(self) -> int:
        """Get number of duplicates found."""
        return self._num_duplicates

    @num_duplicates.setter
    def num_duplicates(self, value: int):
        """Set number of duplicates."""
        self._num_duplicates = value
