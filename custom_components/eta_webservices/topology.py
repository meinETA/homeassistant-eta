"""Plant topology for the dashboard card.

Groups the entities of a config entry into function blocks (boiler, buffer,
heating circuit, ...) and assigns well-known roles (boiler temperature, buffer
top sensor, ...) based on the fixed ETA object/parameter addresses in the URI.
Menu names are not used, so detection works independent of language.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import (
    CHOSEN_FLOAT_SENSORS,
    CHOSEN_SWITCHES,
    CHOSEN_TEXT_SENSORS,
    CHOSEN_WRITABLE_SENSORS,
    DOMAIN,
    FLOAT_DICT,
    FORCE_LEGACY_MODE,
    PENDING_DICT,
    STABLE_ID,
    SWITCHES_DICT,
    TEXT_DICT,
    WRITABLE_DICT,
)

# Detection rules: object id -> block type ("1010*" = prefix) and, per block
# type, [address below the object (segments 3..5), role]. Several addresses may
# serve one role; the first one present wins (older firmware exposes some
# values only under a display address). New addresses go into roles.json.
_VERSION: str = json.loads(
    (Path(__file__).parent / "manifest.json").read_text(encoding="utf-8")
)["version"]
_RULES: dict[str, Any] = json.loads(
    (Path(__file__).parent / "roles.json").read_text(encoding="utf-8")
)
_BLOCK_BY_OBJECT: dict[str, str] = {
    obj: block_type for obj, block_type in _RULES["blocks"].items() if "*" not in obj
}
_BLOCK_BY_PREFIX: tuple[tuple[str, str], ...] = tuple(
    (obj.rstrip("*"), block_type)
    for obj, block_type in _RULES["blocks"].items()
    if obj.endswith("*")
)
ROLES: dict[str, list[tuple[str, str]]] = {
    block_type: [(address, role) for address, role in pairs]
    for block_type, pairs in _RULES["roles"].items()
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


def parse_unique_id(
    unique_id: str, stable: str, writable: bool = False
) -> tuple[str, str, str] | None:
    """Split an entity unique_id into (node, object, address) or None.

    "_writable" twins are skipped unless writable is set; then they map to
    the address of the value they write.
    """
    prefix = f"eta_{stable}_"
    if not unique_id.startswith(prefix):
        return None
    if unique_id.endswith("_writable"):
        if not writable:
            return None
        unique_id = unique_id.removesuffix("_writable")
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
    # selecting a value as writable adds a "_writable" twin and disables the
    # plain entity: the twin then provides the role (heating times need it to
    # be editable); with both present, the twin wins for the same address
    entries = sorted(entries, key=lambda row: row[0].endswith("_writable"))
    for unique_id, entity_id, device_name in entries:
        parsed = parse_unique_id(unique_id, stable, writable=True)
        if parsed is None:
            continue
        twin = unique_id.endswith("_writable")
        node, obj, address = parsed
        block_type = block_type_for_object(obj) or "unknown"
        role, prio = _ROLE_INDEX.get(block_type, {}).get(address, (None, 0))
        key = f"{node}/{obj}"
        have = best.get((key, role), prio + 1) if role else 0
        if role and (have < prio or (have == prio and not twin)):
            role = None  # a preferred address already provides this role
        if block_type in _HIDDEN:
            if role and (role not in plant or best.get(("plant", role), 99) > prio):
                plant[role] = entity_id
                best[("plant", role)] = prio
            continue
        block = blocks.setdefault(key, Block(id=key, type=block_type, object=obj))
        if block.name is None and device_name:
            block.name = device_name
        if entity_id not in block.entities:
            block.entities.append(entity_id)
        if role:
            block.roles[role] = entity_id
            best[(key, role)] = prio
        if block_type == "buffer" and (m := _BUFFER_SENSOR_RE.match(address)):
            block.roles[f"sensor_{int(m.group(1)) - 26}"] = entity_id

    def sort_key(block: Block) -> tuple[int, int, str]:
        try:
            pos = BLOCK_ORDER.index(block.type)
        except ValueError:
            pos = len(BLOCK_ORDER)
        # pellet boilers next to the store, so the hoses reach them (SH-TWIN:
        # pellet unit first, then the wood boiler)
        pellets = any(r in block.roles for r in ("hopper", "consumption_total"))
        return pos, 0 if block.type != "boiler" or pellets else 1, block.id

    return sorted(blocks.values(), key=sort_key), plant


def report_text(state: str | None) -> str | None:
    """Return a status text worth reporting, None for numbers and other values.

    Only short texts without digits ("Bereit", "Heizen") are kept: they show
    which address carries a status. Anything with digits (serial numbers,
    times, dates, phone numbers, IP addresses) is left out.
    """
    if not state or state in ("unknown", "unavailable") or len(state) > 40:
        return None
    if any(ch.isdigit() for ch in state):
        return None
    return state


def build_report(entries: list[tuple[Any, ...]], stable: str) -> list[dict[str, Any]]:
    """Build an anonymized plant report.

    entries: (unique_id, entity_id, parameter name, unit[, status text]).
    Contains object ids, parameter addresses, detected roles, units, the ETA
    parameter names and short status texts (see report_text). No entity ids,
    device names or measured values. Used for the "report plant" button.
    """
    blocks, plant = build_blocks([(row[0], row[1], None) for row in entries], stable)
    role_of = {eid: role for block in blocks for role, eid in block.roles.items()}
    role_of.update({eid: role for role, eid in plant.items()})
    objects: dict[str, dict[str, Any]] = {}
    for unique_id, entity_id, name, unit, *rest in entries:
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
            text = report_text(rest[0]) if rest and not unit else None
            item["other"].append(_report_line(address, unit, name, text, entity_id))
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
        # computed values of the integration ("Auswertung" device)
        prefix = f"eta_{stable}_analytics_"
        for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
            if reg_entry.disabled_by is None and reg_entry.unique_id.startswith(prefix):
                plant[reg_entry.unique_id[len(prefix) :]] = reg_entry.entity_id
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
def async_get_report(
    hass: HomeAssistant,
    entry_id: str | None,
    manual: list[list[str]] | None = None,
) -> dict[str, Any]:
    """Return the anonymized report for one config entry (first if None).

    manual: [block type, role, entity id] picked by hand in the card editor;
    reported as addresses only, so missing detection rules become visible.
    """
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
    regs = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    rows = []
    for reg in regs:
        if reg.disabled_by is not None:
            continue
        state = hass.states.get(reg.entity_id)
        rows.append(
            (
                reg.unique_id,
                reg.entity_id,
                _param_name(reg.original_name),
                reg.unit_of_measurement,
                state.state if state else None,
            )
        )
    uid_of = {reg.entity_id: reg.unique_id for reg in regs}
    conf = {**entry.data, **entry.options}
    discovered: dict[str, dict[str, Any]] = {}
    for key in (FLOAT_DICT, SWITCHES_DICT, TEXT_DICT, WRITABLE_DICT):
        discovered.update(conf.get(key) or {})
    chosen: set[str] = set()
    for key in (
        CHOSEN_FLOAT_SENSORS,
        CHOSEN_SWITCHES,
        CHOSEN_TEXT_SENSORS,
        CHOSEN_WRITABLE_SENSORS,
    ):
        chosen.update(conf.get(key) or [])
    return {
        "report": 2,
        "meta": {
            "integration": _VERSION,
            "ha": HA_VERSION,
            "legacy": bool(conf.get(FORCE_LEGACY_MODE)),
            "interval": conf.get("update_interval"),
            "discovered": len(discovered),
            "selected": len(chosen),
            "pending": len(conf.get(PENDING_DICT) or {}),
        },
        "objects": build_report(rows, stable),
        "unselected": unselected_report(discovered, chosen, stable),
        "manual": manual_report(manual or [], uid_of, stable),
    }


def _report_line(
    address: str,
    unit: str | None,
    name: str | None,
    text: str | None = None,
    entity_id: str | None = None,
) -> str:
    """'0/0/19439 | Status = Bereit', '0/0/12080 | Ein/Aus [switch]'."""
    line = f"{address} {unit}" if unit else address
    if name:
        line += f" | {name}"
    if text:
        line += f" = {text}"
    domain = entity_id.split(".", 1)[0] if entity_id else "sensor"
    if domain != "sensor":
        line += f" [{domain}]"
    return line


def unselected_report(
    discovered: dict[str, dict[str, Any]], chosen: set[str], stable: str
) -> dict[str, list[str]]:
    """Addresses found by the discovery but not selected, per node/object."""
    result: dict[str, list[str]] = {}
    for unique_id, info in discovered.items():
        if unique_id in chosen:
            continue
        parsed = parse_unique_id(unique_id, stable)
        if parsed is None:
            continue
        node, obj, address = parsed
        name = _param_name(str(info.get("friendly_name") or "")) if info else None
        result.setdefault(f"{node}/{obj}", []).append(
            _report_line(address, (info or {}).get("unit") or None, name)
        )
    return {key: sorted(set(lines)) for key, lines in sorted(result.items())}


def _param_name(name: str | None) -> str | None:
    """ETA parameter name without the function block ("Kessel > Status" -> "Status").

    The block name can be renamed on the terminal, the parameter name cannot.
    """
    if not name:
        return None
    return name.rsplit(" > ", 1)[-1].strip() or None


def manual_report(
    manual: list[list[str]], uid_of: dict[str, str], stable: str
) -> list[dict[str, str]]:
    """Turn hand-picked [block type, role, entity id] into addresses."""
    result = []
    for item in manual:
        if len(item) != 3:
            continue
        block_type, role, entity_id = item
        parsed = parse_unique_id(uid_of.get(entity_id, ""), stable)
        if parsed is None:
            continue
        _node, obj, address = parsed
        result.append(
            {"type": block_type, "role": role, "object": obj, "address": address}
        )
    return result
