"""Tests for the plant topology detection."""

from custom_components.eta_webservices.topology import (
    block_type_for_object,
    build_blocks,
    build_report,
    parse_unique_id,
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
