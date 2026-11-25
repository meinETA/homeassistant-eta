"""Tests for the plant topology detection."""

import json
from pathlib import Path
import re

from custom_components.eta_webservices.topology import (
    block_type_for_object,
    build_blocks,
    parse_unique_id,
    unselected_roles,
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


def test_buffer_status_display_address() -> None:
    """Buffer status from 0/0/19403 when the detailed state 0/0/12208 is missing."""
    blocks, _ = build_blocks([_row("/264/10601/0/0/19403", "sensor.pu_state")], STABLE)
    assert blocks[0].roles["status"] == "sensor.pu_state"
    rows = [
        _row("/264/10601/0/0/19403", "sensor.pu_state"),
        _row("/264/10601/0/0/12208", "sensor.pu_detail"),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].roles["status"] == "sensor.pu_detail"


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
            assert re.fullmatch(r"[a-z][a-z0-9_]*", role), role


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


def test_pe_k_boiler_object_is_a_boiler():
    """ETA PE-K reports its boiler under object 10261 (#26)."""
    assert block_type_for_object("10261") == "boiler"


def test_every_buffer_and_node_24_boiler_are_detected():
    """Buffers 2 and 3 use 10252/10253, a boiler can sit on node 24 as 10301 (#37)."""
    assert block_type_for_object("10251") == "buffer"
    assert block_type_for_object("10252") == "buffer"
    assert block_type_for_object("10253") == "buffer"
    assert block_type_for_object("10301") == "boiler"


def test_fwm_flow_rate():
    """The fresh water module shows its secondary flow rate (#38)."""
    rows = [
        (f"eta_{STABLE}_79_10531_0_11148_0", "sensor.fwm_hot_water", None),
        (f"eta_{STABLE}_79_10531_12785_0_0", "sensor.fwm_flow", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].roles["flow"] == "sensor.fwm_flow"


def test_condenser_status_and_return():
    """Condensing heat exchanger 10851 is its own part with status and return (#25)."""
    rows = [
        (f"eta_{STABLE}_120_10851_0_0_19457", "sensor.bw_status", None),
        (f"eta_{STABLE}_120_10851_0_11160_0", "sensor.bw_return", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].type == "condenser"
    assert blocks[0].roles == {
        "status": "sensor.bw_status",
        "return": "sensor.bw_return",
    }


def test_unselected_roles_mark_found_but_not_selected_values():
    """Flow temperature exists on the terminal but is not selected: hint for the card (#25)."""
    rows = [(f"eta_{STABLE}_120_10101_0_0_12090", "sensor.hk_status", None)]
    blocks, _ = build_blocks(rows, STABLE)
    unselected_roles(
        blocks,
        {
            f"eta_{STABLE}_120_10101_0_11060_0",  # flow
            f"eta_{STABLE}_120_10101_0_0_12090",  # already a role
            f"eta_{STABLE}_120_10101_0_11060_2049",  # no role
            f"eta_{STABLE}_120_10102_0_11060_0",  # block without selected values
        },
        STABLE,
    )
    assert blocks[0].unselected == {"flow": "0/11060/0"}
    assert blocks[0].as_dict()["unselected"] == {"flow": "0/11060/0"}


def test_esh_burner_and_switch_valve():
    """Detect eSH 10921, burner 10281 and switch valve 10651 (#40)."""
    rows = [
        (f"eta_{STABLE}_272_10921_0_0_12161", "sensor.esh_temp", None),
        (f"eta_{STABLE}_272_10921_0_0_12000", "sensor.esh_status", None),
        (f"eta_{STABLE}_272_10281_0_0_12006", "sensor.burner_requested", None),
        (f"eta_{STABLE}_272_10281_0_0_12361", "sensor.burner_temp", None),
        (f"eta_{STABLE}_272_10281_0_0_12289", "sensor.burner_status", None),
        (f"eta_{STABLE}_272_10651_0_0_12326", "sensor.uv_hysteresis", None),
        (f"eta_{STABLE}_272_10651_0_0_19447", "sensor.uv_status", None),
        (f"eta_{STABLE}_272_10651_0_0_13458", "sensor.uv_source_1", None),
        (f"eta_{STABLE}_272_10651_0_0_13461", "sensor.uv_source_2", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    by_object = {b.object: b for b in blocks}
    assert by_object["10921"].type == "boiler"
    assert by_object["10921"].roles["temperature"] == "sensor.esh_temp"
    assert by_object["10281"].type == "external_heat"
    assert by_object["10281"].roles["temperature"] == "sensor.burner_temp"
    assert by_object["10281"].roles["status"] == "sensor.burner_status"
    assert by_object["10651"].type == "switch_valve"
    assert by_object["10651"].roles == {
        "status": "sensor.uv_status",
        "source_1": "sensor.uv_source_1",
        "source_2": "sensor.uv_source_2",
    }


def test_buffer_hot_water_zone():
    """Combi tank: hot water temperature of the buffer's hot water zone (#42)."""
    rows = [
        (f"eta_{STABLE}_120_10601_0_11327_0", "sensor.pu_top", None),
        (f"eta_{STABLE}_120_10601_0_0_13434", "sensor.pu_hot_water", None),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    assert blocks[0].roles["hot_water"] == "sensor.pu_hot_water"


def test_flue_gas_return_and_room_roles() -> None:
    """SH20 (#27): flue gas and return at the boiler, room and return at the circuits."""
    rows = [
        _row("/48/10391/0/11109/0", "sensor.kessel"),
        _row("/48/10391/0/0/12162", "sensor.abgas"),
        _row("/48/10391/0/0/12220", "sensor.kessel_rl"),
        _row("/120/10101/0/0/12241", "sensor.hk_vl"),
        _row("/120/10101/0/0/12220", "sensor.hk_rl"),
        _row("/120/10101/0/0/12634", "sensor.hk_raum"),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    roles = {b.type: b.roles for b in blocks}
    assert roles["boiler"]["flue_gas"] == "sensor.abgas"
    assert roles["boiler"]["return"] == "sensor.kessel_rl"
    assert roles["heating_circuit"]["return"] == "sensor.hk_rl"
    assert roles["heating_circuit"]["room"] == "sensor.hk_raum"


def test_sensor_objects_win_over_parameters() -> None:
    """With both present, the sensor object (0/11160/0, 0/11110/0, 0/11237/2293) wins."""
    rows = [
        _row("/48/10391/0/0/12220", "sensor.rl_param"),
        _row("/48/10391/0/11160/0", "sensor.rl_sensor"),
        _row("/48/10391/0/11110/0", "sensor.abgas_sensor"),
        _row("/48/10391/0/0/12162", "sensor.abgas_param"),
        _row("/120/10101/0/0/12634", "sensor.raum_param"),
        _row("/120/10101/0/11237/2293", "sensor.raum_ist"),
    ]
    blocks, _ = build_blocks(rows, STABLE)
    roles = {b.type: b.roles for b in blocks}
    assert roles["boiler"]["return"] == "sensor.rl_sensor"
    assert roles["boiler"]["flue_gas"] == "sensor.abgas_sensor"
    assert roles["heating_circuit"]["room"] == "sensor.raum_ist"
