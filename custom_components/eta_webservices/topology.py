"""Plant topology for the dashboard card.

Groups the entities of a config entry into function blocks (boiler, buffer,
heating circuit, ...) and assigns well-known roles (boiler temperature, buffer
top sensor, ...) based on the fixed ETA object/parameter addresses in the URI.
Menu names are not used, so detection works independent of language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN, STABLE_ID

# Object id (second URI segment) -> block type.
_BLOCK_BY_OBJECT: dict[str, str] = {
    "10021": "boiler",
    "10891": "boiler",
    "10561": "boiler",
    "10201": "silo",
    "10211": "silo",  # pellet store with suction switching unit
    "10221": "solar",
    "10241": "system",
    "10251": "buffer",
    "10601": "buffer",
    "10291": "external_heat",
    "10311": "external_demand",
    "10531": "fwm",
    "10911": "diagnostics",
    "10961": "pv",
}
_BLOCK_BY_PREFIX: tuple[tuple[str, str], ...] = (
    ("1010", "heating_circuit"),
    ("1011", "dhw"),
)

# Block type -> [(address below the object (segments 3..5), role)].
# Several addresses may serve one role; the first one present wins (older
# firmware exposes some values only under a display address).
ROLES: dict[str, list[tuple[str, str]]] = {
    "boiler": [
        ("0/11109/0", "temperature"),
        ("0/0/12161", "temperature"),
        ("0/0/12180", "pressure"),
        ("0/0/12011", "hopper"),
        ("0/0/12000", "status"),
        ("0/11123/0", "pump"),
        ("0/11195/0", "pump"),
        ("0/11160/0", "return"),
        # chip/pellet discharge handled by the boiler itself (no own store FUB)
        ("0/2203/0", "auger"),
        ("0/0/12058", "discharge"),
        ("0/0/12080", "switch"),
    ],
    "silo": [
        ("0/0/12015", "stock"),
        ("0/0/12423", "status"),
        ("0/11029/0", "auger"),
    ],
    "buffer": [
        ("0/11327/0", "top"),
        ("0/0/12242", "top"),
        ("0/11328/0", "middle"),
        ("0/11329/0", "bottom"),
        ("0/0/12244", "bottom"),
        ("0/0/12528", "charge"),
        ("0/0/12208", "status"),
    ],
    "heating_circuit": [
        ("0/11060/0", "flow"),
        ("0/0/12241", "flow"),
        ("0/0/12090", "status"),
        ("0/11124/0", "pump"),
        ("0/0/12092", "mode"),
        ("0/0/12080", "switch"),
        ("0/0/12125", "heat"),
        ("0/0/12126", "auto"),
        ("0/0/12230", "lower"),
        ("0/0/12218", "come"),
        ("0/0/12231", "go"),
    ],
    "dhw": [
        ("0/11129/0", "temperature"),
        ("0/0/12271", "temperature"),
        ("0/0/12129", "temperature"),
        ("0/0/12274", "pump"),
    ],
    "solar": [
        ("0/11139/0", "collector"),
        ("0/0/12275", "collector"),
        ("0/0/12784", "storage_top"),
        ("0/0/12781", "storage_bottom"),
        ("0/0/12278", "pump"),
        ("0/0/12183", "status"),
    ],
    "external_heat": [
        ("0/0/12161", "temperature"),
        ("0/0/12491", "storage"),
        ("0/11088/0", "pump"),
    ],
    "fwm": [
        ("0/11148/0", "hot_water"),
        ("0/11243/0", "primary_flow"),
        ("0/11186/0", "primary_return"),
        ("0/0/12195", "status"),
        ("0/11280/0", "pump"),
        ("0/0/12080", "switch"),
    ],
    "external_demand": [
        ("0/0/19416", "status"),
    ],
    "system": [
        ("0/11127/0", "outside"),
        ("0/0/12197", "outside"),
    ],
}
# Heating times: weekday d (0 = Monday) has three time slots at 1082 + 4 * d + n.
ROLES["heating_circuit"] += [
    (f"12113/0/{1082 + 4 * day + slot}", f"slot_{day}_{slot}")
    for day in range(7)
    for slot in range(3)
]
_ROLE_INDEX: dict[str, dict[str, tuple[str, int]]] = {
    block_type: {address: (role, prio) for prio, (address, role) in enumerate(pairs)}
    for block_type, pairs in ROLES.items()
}

# Left-to-right order on the card; unknown types go last.
BLOCK_ORDER = (
    "silo",
    "boiler",
    "solar",
    "external_heat",
    "buffer",
    "heating_circuit",
    "external_demand",
    "dhw",
    "fwm",
    "pv",
)
_HIDDEN = {"diagnostics", "system"}

# Buffer sensors "Fühler 1 (oben)", "Fühler 2", ... numbered top to bottom; they
# get an extra role sensor_<n> besides top/middle/bottom.
_BUFFER_SENSOR_RE = re.compile(r"^0/113(2[7-9]|3[0-5])/0$")

_URI_RE = re.compile(r"^(\d+)_(\d+)_(\d+)_(\d+)_(\d+)$")


def block_type_for_object(obj: str) -> str | None:
    """Return the block type for an ETA object id, None if unknown."""
    if obj in _BLOCK_BY_OBJECT:
        return _BLOCK_BY_OBJECT[obj]
    for prefix, block_type in _BLOCK_BY_PREFIX:
        if obj.startswith(prefix):
            return block_type
    return None


def parse_unique_id(unique_id: str, stable: str) -> tuple[str, str, str] | None:
    """Split an entity unique_id into (node, object, address) or None."""
    prefix = f"eta_{stable}_"
    if not unique_id.startswith(prefix) or unique_id.endswith("_writable"):
        return None
    match = _URI_RE.match(unique_id[len(prefix) :])
    if not match:
        return None
    node, obj, a, b, c = match.groups()
    return node, obj, f"{a}/{b}/{c}"


@dataclass
class Block:
    """One function block of the plant."""

    id: str
    type: str
    object: str = ""
    name: str | None = None
    roles: dict[str, str] = field(default_factory=dict)
    entities: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:  # noqa: D102
        return {
            "id": self.id,
            "type": self.type,
            "object": self.object,
            "name": self.name,
            "roles": self.roles,
            "entities": self.entities,
        }


def build_blocks(
    entries: list[tuple[str, str, str | None]], stable: str
) -> tuple[list[Block], dict[str, str]]:
    """Build blocks from (unique_id, entity_id, device_name) tuples.

    Returns the visible blocks in card order and plant-wide roles (e.g. the
    outside temperature from the system block).
    """
    blocks: dict[str, Block] = {}
    plant: dict[str, str] = {}
    best: dict[tuple[str, str], int] = {}
    for unique_id, entity_id, device_name in entries:
        parsed = parse_unique_id(unique_id, stable)
        if parsed is None:
            continue
        node, obj, address = parsed
        block_type = block_type_for_object(obj) or "unknown"
        role, prio = _ROLE_INDEX.get(block_type, {}).get(address, (None, 0))
        key = f"{node}/{obj}"
        if role and best.get((key, role), prio + 1) <= prio:
            role = None  # a preferred address already provides this role
        if block_type in _HIDDEN:
            if role and (role not in plant or best.get(("plant", role), 99) > prio):
                plant[role] = entity_id
                best[("plant", role)] = prio
            continue
        block = blocks.setdefault(key, Block(id=key, type=block_type, object=obj))
        if block.name is None and device_name:
            block.name = device_name
        block.entities.append(entity_id)
        if role:
            block.roles[role] = entity_id
            best[(key, role)] = prio
        if block_type == "buffer" and (m := _BUFFER_SENSOR_RE.match(address)):
            block.roles[f"sensor_{int(m.group(1)) - 26}"] = entity_id

    def sort_key(block: Block) -> tuple[int, str]:
        try:
            pos = BLOCK_ORDER.index(block.type)
        except ValueError:
            pos = len(BLOCK_ORDER)
        return pos, block.id

    return sorted(blocks.values(), key=sort_key), plant


def build_report(
    entries: list[tuple[str, str, str | None, str | None]], stable: str
) -> list[dict[str, Any]]:
    """Build an anonymized plant report from (unique_id, entity_id, name, unit).

    Contains only object ids, parameter addresses, detected roles and units:
    no names, entity ids or values. Used for the "report plant" button.
    """
    blocks, plant = build_blocks([(u, e, None) for u, e, _, _ in entries], stable)
    role_of = {eid: role for block in blocks for role, eid in block.roles.items()}
    role_of.update({eid: role for role, eid in plant.items()})
    objects: dict[str, dict[str, Any]] = {}
    for unique_id, entity_id, _name, unit in entries:
        parsed = parse_unique_id(unique_id, stable)
        if parsed is None:
            continue
        node, obj, address = parsed
        item = objects.setdefault(
            f"{node}/{obj}",
            {
                "node": node,
                "object": obj,
                "type": block_type_for_object(obj) or "unknown",
                "roles": {},
                "other": [],
            },
        )
        if entity_id in role_of:
            item["roles"][role_of[entity_id]] = address
        else:
            item["other"].append(f"{address} {unit}" if unit else address)
    for item in objects.values():
        item["other"].sort()
    return [objects[key] for key in sorted(objects)]


@callback
def async_get_topology(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Return the topology of every loaded ETA config entry."""
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    result = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        stable = entry.data.get(STABLE_ID) or str(entry.data.get("host", "")).replace(
            ".", "_"
        )
        rows = []
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if reg_entry.disabled_by is not None:
                continue
            device = (
                dev_reg.async_get(reg_entry.device_id) if reg_entry.device_id else None
            )
            device_name = (device.name_by_user or device.name) if device else None
            rows.append((reg_entry.unique_id, reg_entry.entity_id, device_name))
        blocks, plant = build_blocks(rows, stable)
        result.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "plant": plant,
                "blocks": [block.as_dict() for block in blocks],
            }
        )
    return result


@callback
def async_get_report(hass: HomeAssistant, entry_id: str | None) -> dict[str, Any]:
    """Return the anonymized report for one config entry (first if None)."""
    ent_reg = er.async_get(hass)
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = next((e for e in entries if e.entry_id == entry_id), None) or (
        entries[0] if entries else None
    )
    if entry is None:
        return {"objects": []}
    stable = entry.data.get(STABLE_ID) or str(entry.data.get("host", "")).replace(
        ".", "_"
    )
    rows = [
        (reg.unique_id, reg.entity_id, None, reg.unit_of_measurement)
        for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        if reg.disabled_by is None
    ]
    return {"objects": build_report(rows, stable)}
