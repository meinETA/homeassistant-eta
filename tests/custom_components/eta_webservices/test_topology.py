"""Tests for the plant topology detection."""

import json
from pathlib import Path
import re

from custom_components.eta_webservices.topology import (
    _param_name,
    _report_line,
    block_type_for_object,
    build_blocks,
    build_report,
    manual_report,
    parse_unique_id,
    report_text,
    unselected_report,
)

STABLE = "keller"


def _row(uri: str, entity_id: str, device: str | None = None) -> tuple:
    uid = f"eta_{STABLE}_" + uri.strip("/").replace("/", "_")
    return (uid, entity_id, device)


def test_block_type_for_object() -> None:
    """Object ids map to block types."""
    assert block_type_for_object("10891") == "boiler"
    assert block_type_for_object("10021") == "boiler"
    assert block_type_for_object("10561") == "boiler"
    assert block_type_for_object("10211") == "silo"
    assert block_type_for_object("10311") == "external_demand"
    assert block_type_for_object("10601") == "buffer"
    assert block_type_for_object("10101") == "heating_circuit"
    assert block_type_for_object("10103") == "heating_circuit"
    assert block_type_for_object("10111") == "dhw"
    assert block_type_for_object("10531") == "fwm"
    assert block_type_for_object("99999") is None


def test_parse_unique_id() -> None:
    """Unique ids split into node, object and address."""
    assert parse_unique_id("eta_keller_264_10891_0_11109_0", STABLE) == (
        "264",
        "10891",
        "0/11109/0",
    )
    assert parse_unique_id("eta_keller_264_10891_0_0_12180_writable", STABLE) is None
    assert parse_unique_id("eta_keller_8080_latest_error", STABLE) is None
    assert parse_unique_id("eta_other_264_10891_0_11109_0", STABLE) is None
    # IP-based stable id contains underscores itself
    assert parse_unique_id(
        "eta_172_24_120_210_264_10601_0_11327_0", "172_24_120_210"
    ) == ("264", "10601", "0/11327/0")


def test_build_blocks_roles_and_order() -> None:
    """Blocks get roles, names and card order."""
    rows = [
        _row("/79/10531/0/11148/0", "sensor.fwm_ww", "FWM"),
        _row("/264/10101/0/11060/0", "sensor.hk_vl", "Heizkreis"),
        _row("/264/10601/0/11327/0", "sensor.pu_top", "Puffer"),
        _row("/264/10601/0/0/12528", "sensor.pu_charge", "Puffer"),
        _row("/264/10891/0/11109/0", "sensor.k_temp", "Kessel"),
        _row("/264/10891/0/0/12000", "sensor.k_status", "Kessel"),
        _row("/264/10891/0/0/99999", "sensor.k_other", "Kessel"),
        _row("/264/10201/0/0/12015", "sensor.silo", "Silo"),
        _row("/264/10241/0/11127/0", "sensor.outside", "Sys"),
        _row("/264/10911/0/0/6670", "sensor.diag", "Diagnose"),
        _row("/264/12345/0/0/1", "sensor.mystery", "X"),
    ]
    blocks, plant = build_blocks(rows, STABLE)
    assert [b.type for b in blocks] == [
        "silo",
        "boiler",
        "buffer",
        "heating_circuit",
        "fwm",
        "unknown",
    ]
    boiler = blocks[1]
    assert boiler.name == "Kessel"
    assert boiler.roles == {"temperature": "sensor.k_temp", "status": "sensor.k_status"}
    assert "sensor.k_other" in boiler.entities
    assert blocks[2].roles == {
        "top": "sensor.pu_top",
        "sensor_1": "sensor.pu_top",
        "charge": "sensor.pu_charge",
    }
    assert plant == {"outside": "sensor.outside"}


def test_multiple_heating_circuits_are_separate_blocks() -> None:
    """Each heating circuit is its own block."""
    rows = [
        _row("/264/10102/0/11060/0", "sensor.hk2"),
        _row("/264/10101/0/11060/0", "sensor.hk1"),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert [b.id for b in blocks] == ["264/10101", "264/10102"]


def test_preferred_address_wins_regardless_of_order() -> None:
    """The sensor address beats the display address for the same role."""
    rows = [
        _row("/264/10891/0/0/12161", "sensor.display"),
        _row("/264/10891/0/11109/0", "sensor.sensor"),
        _row("/40/10021/0/0/12161", "sensor.only_display"),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    by_id = {b.id: b for b in blocks}
    assert by_id["264/10891"].roles["temperature"] == "sensor.sensor"
    assert by_id["40/10021"].roles["temperature"] == "sensor.only_display"


def test_build_report_is_anonymous():
    """The report keeps addresses/roles/units only, no entity ids or names."""
    rows = [
        (f"eta_{STABLE}_40_10021_0_11109_0", "sensor.haus_mueller_kessel", None, "°C"),
        (f"eta_{STABLE}_40_10021_0_0_99999", "sensor.haus_mueller_x", None, "%"),
        (f"eta_{STABLE}_40_19999_0_0_1", "sensor.haus_mueller_y", None, None),
    ]
    report = build_report(rows, STABLE)
    assert report == [
        {
            "node": "40",
            "object": "10021",
            "type": "boiler",
            "roles": {"temperature": "0/11109/0"},
            "other": ["0/0/99999 %"],
        },
        {
            "node": "40",
            "object": "19999",
            "type": "unknown",
            "roles": {},
            "other": ["0/0/1"],
        },
    ]
    assert "mueller" not in str(report)


def test_heating_circuit_control_roles():
    """Control keys and heating time slots are detected on heating circuits."""
    rows = [
        (f"eta_{STABLE}_264_10101_0_0_12080", "switch.hk_on_off", None),
        (f"eta_{STABLE}_264_10101_0_0_12218", "switch.hk_come", None),
        (f"eta_{STABLE}_264_10101_0_0_12231", "switch.hk_go", None),
        (f"eta_{STABLE}_264_10101_12113_0_1082", "sensor.hk_mon_1", None),
        (f"eta_{STABLE}_264_10101_12113_0_1108", "sensor.hk_sun_3", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].roles == {
        "switch": "switch.hk_on_off",
        "come": "switch.hk_come",
        "go": "switch.hk_go",
        "slot_0_0": "sensor.hk_mon_1",
        "slot_6_2": "sensor.hk_sun_3",
    }


def test_buffer_with_four_sensors():
    """All numbered buffer sensors get a sensor_<n> role in top-down order."""
    rows = [
        (f"eta_{STABLE}_264_10601_0_{11327 + n}_0", f"sensor.f{n + 1}", None)
        for n in range(4)
    ]
    blocks, _ = build_blocks(rows, STABLE)
    roles = blocks[0].roles
    assert [roles[f"sensor_{n}"] for n in range(1, 5)] == [
        "sensor.f1",
        "sensor.f2",
        "sensor.f3",
        "sensor.f4",
    ]
    assert roles["top"] == "sensor.f1"
    assert roles["bottom"] == "sensor.f3"


def test_status_display_addresses() -> None:
    """Newer firmware exposes status texts only under 0/0/194xx."""
    rows = [
        _row("/40/10021/0/0/19402", "sensor.boiler_status"),
        _row("/120/10101/0/0/19404", "sensor.hc_status"),
        _row("/120/10111/0/0/19406", "sensor.dhw_status"),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    roles = {b.id: b.roles.get("status") for b in blocks}
    assert roles == {
        "40/10021": "sensor.boiler_status",
        "120/10101": "sensor.hc_status",
        "120/10111": "sensor.dhw_status",
    }


def test_roles_json_is_consistent() -> None:
    """roles.json: valid object ids and addresses, no duplicates, known types."""
    path = Path(__file__).parents[3] / "custom_components/eta_webservices/roles.json"
    rules = json.loads(path.read_text(encoding="utf-8"))
    types = set(rules["blocks"].values())
    for obj in rules["blocks"]:
        assert re.fullmatch(r"\d+\*?", obj), obj
    for block_type, pairs in rules["roles"].items():
        assert block_type in types, block_type
        addresses = [address for address, _ in pairs]
        assert len(addresses) == len(set(addresses)), block_type
        for address, role in pairs:
            assert re.fullmatch(r"\d+/\d+/\d+", address), address
            assert re.fullmatch(r"[a-z_]+", role), role


def test_manual_report_has_addresses_only() -> None:
    """Hand-picked values are reported as object and address, no entity ids."""
    uid = _row("/40/10021/0/0/19999", "sensor.x")[0]
    result = manual_report(
        [["boiler", "pressure", "sensor.x"], ["boiler", "status", "sensor.gone"]],
        {"sensor.x": uid},
        STABLE,
    )
    assert result == [
        {
            "type": "boiler",
            "role": "pressure",
            "object": "10021",
            "address": "0/0/19999",
        }
    ]


def test_writable_twin_provides_role() -> None:
    """A "_writable" twin (plain entity disabled) still fills the slot role."""
    uri = "/264/10101/12113/0/1082"
    uid = _row(uri, "x")[0]
    rows = [(f"{uid}_writable", "sensor.slot_w", None)]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].roles["slot_0_0"] == "sensor.slot_w"
    # both enabled: the twin wins regardless of order
    for order in (
        [(uid, "sensor.slot", None), *rows],
        [*rows, (uid, "sensor.slot", None)],
    ):
        blocks, _ = build_blocks(order, STABLE)
        assert blocks[0].roles["slot_0_0"] == "sensor.slot_w"


def test_report_v2_names_and_status_texts():
    """Parameter names and short status texts are reported, numbers are not."""
    rows = [
        (f"eta_{STABLE}_264_10571_0_0_19439", "sensor.a", "Status", None, "Bereit"),
        (
            f"eta_{STABLE}_264_10571_0_0_12733",
            "sensor.b",
            "Seriennummer",
            None,
            "12345678",
        ),
        (f"eta_{STABLE}_264_10571_0_11318_2328", "sensor.c", "Leistung", "W", "12.0"),
        (f"eta_{STABLE}_264_10571_0_0_14439", "sensor.d", None, None, "unknown"),
    ]
    report = build_report(rows, STABLE)
    assert report[0]["type"] == "particle_separator"
    assert report[0]["other"] == [
        "0/0/12733 | Seriennummer",
        "0/0/14439",
        "0/0/19439 | Status = Bereit",
        "0/11318/2328 W | Leistung",
    ]
    assert "12345678" not in str(report)
    assert "12.0" not in str(report)


def test_report_text_filter():
    """Only short texts without digits are kept."""
    assert report_text("Bereit") == "Bereit"
    assert report_text("Ein [Heizen]") == "Ein [Heizen]"
    for value in (
        None,
        "",
        "unknown",
        "unavailable",
        "21:00",
        "192.168.1.5",
        "+43 7672",
        "x" * 41,
    ):
        assert report_text(value) is None


def test_param_name_drops_block_name():
    """Renamable block names are cut off, the ETA parameter name stays."""
    assert _param_name("HK Oma > Status") == "Status"
    assert _param_name("Status") == "Status"
    assert _param_name(None) is None


def test_unselected_report_lists_found_but_not_selected():
    """Discovered endpoints that were not selected are reported per object."""
    discovered = {
        f"eta_{STABLE}_264_10891_0_11109_0": {
            "friendly_name": "Kessel > Kessel",
            "unit": "°C",
        },
        f"eta_{STABLE}_264_10891_0_0_12080": {
            "friendly_name": "Kessel > Ein/Aus",
            "unit": "",
        },
    }
    chosen = {f"eta_{STABLE}_264_10891_0_11109_0"}
    assert unselected_report(discovered, chosen, STABLE) == {
        "264/10891": ["0/0/12080 | Ein/Aus"]
    }


def test_report_line_marks_non_sensor_domains():
    """Switches and other non-sensor entities carry their domain."""
    assert _report_line("0/0/12080", None, "Ein/Aus", None, "switch.x") == (
        "0/0/12080 | Ein/Aus [switch]"
    )
    assert _report_line("0/11109/0", "°C", "Kessel", None, "sensor.x") == (
        "0/11109/0 °C | Kessel"
    )


def test_pc_boiler_object_is_a_boiler():
    """ETA PC reports its boiler under object 10511 (#21)."""
    assert block_type_for_object("10511") == "boiler"


def test_sh_twin_boilers_are_detected():
    """SH-TWIN: log wood boiler 10391 and pellet unit 10401 are boilers (#22, #23)."""
    rows = [
        (f"eta_{STABLE}_40_10401_0_0_12013", "sensor.ash", None),
        (f"eta_{STABLE}_40_10401_0_0_12414", "sensor.twin_pump", None),
        (f"eta_{STABLE}_48_10391_0_0_12161", "sensor.sh_temp", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    by_id = {b.id: b for b in blocks}
    assert by_id["40/10401"].type == "boiler"
    assert by_id["40/10401"].roles["ash_used"] == "sensor.ash"
    assert by_id["40/10401"].roles["pump"] == "sensor.twin_pump"
    assert by_id["48/10391"].type == "boiler"
    assert by_id["48/10391"].roles["temperature"] == "sensor.sh_temp"


def test_pellet_boiler_comes_before_wood_boiler():
    """The boiler with pellets stands next to the store, whatever its node."""
    rows = [
        (f"eta_{STABLE}_10_10391_0_0_12161", "sensor.sh_temp", None),
        (f"eta_{STABLE}_40_10401_0_0_12011", "sensor.twin_hopper", None),
        (f"eta_{STABLE}_40_10201_0_0_12015", "sensor.stock", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert [b.id for b in blocks] == ["40/10201", "40/10401", "10/10391"]


def test_boiler_residual_oxygen_role():
    """Residual oxygen is shown as fourth boiler value."""
    rows = [(f"eta_{STABLE}_48_10391_0_0_12164", "sensor.o2", None)]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].roles["oxygen"] == "sensor.o2"
