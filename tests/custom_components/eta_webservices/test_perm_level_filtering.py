"""Tests for API 1.3 permission-level filtering in the config flow."""

from custom_components.eta_webservices._api.types import ETAEndpoint
from custom_components.eta_webservices.config_flow import (
    _auto_selected_keys,
    _compute_supports_perm_level,
    _visible_keys,
)
from custom_components.eta_webservices.const import (
    ALLOW_SERVICE_WRITE,
    FLOAT_DICT,
    PENDING_DICT,
    SHOW_SERVICE_SENSORS,
    SUPPORTS_PERM_LEVEL,
    SWITCHES_DICT,
    TEXT_DICT,
    WRITABLE_DICT,
)


def _ep(perm=None, is_writable=None):
    return ETAEndpoint(
        url="/u",
        value=0,
        valid_values=None,
        friendly_name="x",
        unit="°C",
        endpoint_type="DEFAULT",
        perm_level=perm,
        is_writable=is_writable,
    )


def test_supports_perm_level_detection():
    """Permission-level support is detected from endpoint metadata."""
    assert _compute_supports_perm_level({"a": _ep("USER")}) is True
    assert _compute_supports_perm_level({"a": _ep(None)}) is False
    assert _compute_supports_perm_level({}) is False


def test_visible_keys_no_support_no_filtering():
    """On API 1.1/1.2 (no support) no filtering is applied."""
    d = {"u": _ep(None), "s": _ep(None)}
    # supports=False -> everything visible (API 1.1/1.2 behavior)
    assert set(_visible_keys(d, False, False)) == {"u", "s"}


def test_visible_keys_user_default_hides_service():
    """USER endpoints show by default; SERVICE/unknown only when enabled."""
    d = {"u": _ep("USER"), "s": _ep("SERVICE"), "x": _ep("ServiceKD")}
    # show_service off -> only USER
    assert _visible_keys(d, True, show_service=False) == ["u"]
    # show_service on -> all
    assert set(_visible_keys(d, True, show_service=True)) == {"u", "s", "x"}


def test_visible_keys_writable_requires_write_permission():
    """Service writables need the service-write toggle."""
    d = {"u": _ep("USER", True), "s": _ep("SERVICE", True)}
    # service visible but writing not allowed -> service writable excluded
    assert _visible_keys(
        d, True, show_service=True, allow_service_write=False, writable=True
    ) == ["u"]
    # writing allowed -> both
    assert set(
        _visible_keys(
            d, True, show_service=True, allow_service_write=True, writable=True
        )
    ) == {"u", "s"}


def test_auto_selected_keys_respects_toggles():
    """Select-all honors the permission-level toggles."""
    data = {
        SUPPORTS_PERM_LEVEL: True,
        SHOW_SERVICE_SENSORS: False,
        ALLOW_SERVICE_WRITE: False,
        FLOAT_DICT: {"u": _ep("USER"), "s": _ep("SERVICE")},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {"uw": _ep("USER", True), "sw": _ep("SERVICE", True)},
        PENDING_DICT: {},
    }
    floats, _switches, _texts, writables, _pending = _auto_selected_keys(data)
    assert floats == ["u"]
    assert writables == ["uw"]

    data[SHOW_SERVICE_SENSORS] = True
    data[ALLOW_SERVICE_WRITE] = True
    floats, _switches, _texts, writables, _pending = _auto_selected_keys(data)
    assert set(floats) == {"u", "s"}
    assert set(writables) == {"uw", "sw"}


def _option_values(schema: dict, field: str) -> list[str]:
    """Extract the option values of a SelectSelector field from a schema dict."""
    for marker, selector_obj in schema.items():
        if getattr(marker, "schema", None) == field:
            cfg = selector_obj.config
            opts = cfg["options"] if isinstance(cfg, dict) else cfg.options
            return [o["value"] for o in opts]
    return []


def test_already_selected_service_key_stays_a_valid_option():
    """A pre-selected SERVICE key remains an option even with show_service off.

    Prevents the voluptuous "value must be one of" error and raw-id rendering, and
    keeps enabling permLevel non-destructive for existing selections.
    """
    from custom_components.eta_webservices.config_flow import (
        _build_endpoint_selection_schema,
    )
    from custom_components.eta_webservices.const import CHOSEN_FLOAT_SENSORS

    data = {
        SUPPORTS_PERM_LEVEL: True,
        SHOW_SERVICE_SENSORS: False,
        ALLOW_SERVICE_WRITE: False,
        FLOAT_DICT: {"user_k": _ep("USER"), "svc_k": _ep("SERVICE")},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        PENDING_DICT: {},
    }
    # svc_k is already selected -> must appear as an option even though it is SERVICE
    schema = _build_endpoint_selection_schema(
        data, defaults={CHOSEN_FLOAT_SENSORS: ["svc_k"]}
    )
    values = _option_values(schema, CHOSEN_FLOAT_SENSORS)
    assert "user_k" in values
    assert "svc_k" in values, "already-selected SERVICE key was dropped from options"

    # Not selected -> SERVICE stays hidden by default
    schema2 = _build_endpoint_selection_schema(data)
    values2 = _option_values(schema2, CHOSEN_FLOAT_SENSORS)
    assert values2 == ["user_k"]


def test_disabling_show_service_keeps_already_selected_service():
    """Turning show_service off must not drop an already-selected service key."""
    data = {
        SUPPORTS_PERM_LEVEL: True,
        SHOW_SERVICE_SENSORS: False,
        ALLOW_SERVICE_WRITE: False,
        FLOAT_DICT: {"u": _ep("USER"), "s": _ep("SERVICE")},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        PENDING_DICT: {},
        "chosen_float_sensors": ["s"],  # service sensor selected earlier
    }
    floats, _sw, _t, _w, _p = _auto_selected_keys(data)
    # non-destructive: USER visible + the already-selected SERVICE key kept
    assert set(floats) == {"u", "s"}


def test_discovered_counts_ignore_hidden_service_sensors():
    """Shown counts reflect the selection: hidden service sensors are not counted."""
    from custom_components.eta_webservices.config_flow import (
        _build_discovered_entity_placeholders,
    )

    data = {
        SUPPORTS_PERM_LEVEL: True,
        SHOW_SERVICE_SENSORS: False,
        ALLOW_SERVICE_WRITE: False,
        FLOAT_DICT: {"u": _ep("USER"), "s": _ep("SERVICE")},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {"uw": _ep("USER", True), "sw": _ep("SERVICE", True)},
        PENDING_DICT: {},
    }

    # show_service off: only USER-level is offered, so service is not counted,
    # and the service line reads "disabled" (not "0") in both languages.
    ph = _build_discovered_entity_placeholders(data, "en")
    assert ph["float_count"] == "1"
    assert ph["writable_count"] == "1"
    assert ph["total_count"] == "2"
    assert ph["service_count"] == "0"
    assert ph["service_line"] == "\nService-level sensors: disabled"
    ph_de = _build_discovered_entity_placeholders(data, "de")
    assert ph_de["service_line"] == "\nService-Sensoren: deaktiviert"

    # show_service on (read-only service shown) but writing not allowed:
    # service float counts; service writable stays excluded from the writable list.
    data[SHOW_SERVICE_SENSORS] = True
    ph = _build_discovered_entity_placeholders(data, "en")
    assert ph["float_count"] == "2"
    assert ph["writable_count"] == "1"
    assert ph["total_count"] == "3"
    assert ph["service_count"] == "1"
    assert ph["service_line"] == "\nService-level sensors: 1"

    # both toggles on: service writable is offered too.
    data[ALLOW_SERVICE_WRITE] = True
    ph = _build_discovered_entity_placeholders(data, "en")
    assert ph["writable_count"] == "2"
    assert ph["total_count"] == "4"
    assert ph["service_count"] == "2"
    assert ph["service_line"] == "\nService-level sensors: 2"


def test_service_line_omitted_without_perm_level_support():
    """On API 1.1/1.2 there is no service concept, so no service line is shown."""
    from custom_components.eta_webservices.config_flow import (
        _build_discovered_entity_placeholders,
    )

    data = {
        SUPPORTS_PERM_LEVEL: False,
        FLOAT_DICT: {"a": _ep(None), "b": _ep(None)},
        SWITCHES_DICT: {},
        TEXT_DICT: {},
        WRITABLE_DICT: {},
        PENDING_DICT: {},
    }
    ph = _build_discovered_entity_placeholders(data, "de")
    assert ph["total_count"] == "2"
    assert ph["service_line"] == ""
