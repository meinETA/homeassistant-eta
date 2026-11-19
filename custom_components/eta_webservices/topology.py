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

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    label_registry as lr,
)

from .const import (
    DOMAIN,
    FAST_UPDATE_LABEL_ID,
    FAST_UPDATE_LABEL_NAME,
    PANEL_DATA,
    STABLE_ID,
)

# Detection rules: object id -> block type ("1010*" = prefix) and, per block
# type, [address below the object (segments 3..5), role]. Several addresses may
# serve one role; the first one present wins (older firmware exposes some
# values only under a display address). New addresses go into roles.json.
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


def _stable(entry: ConfigEntry) -> str:
    return entry.data.get(STABLE_ID) or str(entry.data.get("host", "")).replace(
        ".", "_"
    )


# roles the card uses for calculations only, they change rarely or never;
# heating time slots ("slot_*") are refreshed right after a write anyway
SLOW_ROLES = frozenset({"ash_limit", "stock_max", "stock_warn", "consumption_total"})
_BUFFER_POSITIONS = ("top", "middle", "bottom")


def card_entities(
    blocks: list[Block], plant: dict[str, str], card: dict[str, Any]
) -> set[str]:
    """Return the entities the plant card shows, with its stored settings.

    Mirrors applyConfig() of the card: roles assigned by hand replace the
    detected ones, "-" hides a role, hidden blocks are left out, and a buffer
    with a hand-picked top/middle/bottom sensor drops its numbered sensors.
    """
    overrides = card.get("roles") or {}
    hidden = set(card.get("hidden") or [])
    result: set[str] = set()

    def apply(roles: dict[str, str], own: Any) -> dict[str, str]:
        roles = dict(roles)
        for role, entity_id in (own if isinstance(own, dict) else {}).items():
            if entity_id == "-":
                roles.pop(role, None)
            elif isinstance(entity_id, str) and entity_id:
                roles[role] = entity_id
        return roles

    block_ids = [block.id for block in blocks]
    block_ids += [
        x["id"] for x in card.get("extra") or [] if isinstance(x, dict) and "id" in x
    ]
    detected = {block.id: block for block in blocks}
    for block_id in block_ids:
        if block_id in hidden:
            continue
        block = detected.get(block_id)
        own = overrides.get(block_id)
        roles = apply(block.roles if block else {}, own)
        if (
            block is not None
            and block.type == "buffer"
            and isinstance(own, dict)
            and any(pos in own for pos in _BUFFER_POSITIONS)
        ):
            roles = {r: e for r, e in roles.items() if not r.startswith("sensor_")}
        result.update(
            entity_id
            for role, entity_id in roles.items()
            if role not in SLOW_ROLES and not role.startswith("slot_")
        )
    result.update(apply(plant, overrides.get("plant")).values())
    return result


def entity_uris(entity_ids: set[str], uid_of: dict[str, str], stable: str) -> set[str]:
    """Return the ETA uris of entities of this entry (others are skipped)."""
    uris = set()
    for entity_id in entity_ids:
        parsed = parse_unique_id(uid_of.get(entity_id, ""), stable, writable=True)
        if parsed is not None:
            node, obj, address = parsed
            uris.add(f"/{node}/{obj}/{address}")
    return uris


@callback
def async_fast_uris(hass: HomeAssistant, entry: ConfigEntry) -> set[str]:
    """Return the uris to poll fast: plant card values and labelled entities."""
    ent_reg = er.async_get(hass)
    stable = _stable(entry)
    regs = [
        reg
        for reg in er.async_entries_for_config_entry(ent_reg, entry.entry_id)
        if reg.disabled_by is None
    ]
    blocks, plant = build_blocks(
        [(reg.unique_id, reg.entity_id, None) for reg in regs], stable
    )
    stored = hass.data.get(PANEL_DATA, {}).get(entry.entry_id, {})
    entity_ids = card_entities(blocks, plant, stored.get("card") or {})
    # entities the user marked with the "ETA Fast Update" label
    entity_ids.update(
        reg.entity_id for reg in regs if FAST_UPDATE_LABEL_ID in reg.labels
    )
    uid_of = {reg.entity_id: reg.unique_id for reg in regs}
    return entity_uris(entity_ids, uid_of, stable)


@callback
def async_ensure_fast_label(hass: HomeAssistant) -> None:
    """Create the "ETA Fast Update" label once, so users only pick it.

    Found by id: a renamed label keeps working, a deleted one comes back.
    """
    label_reg = lr.async_get(hass)
    if label_reg.async_get_label(FAST_UPDATE_LABEL_ID) is not None:
        return
    if label_reg.async_get_label_by_name(FAST_UPDATE_LABEL_NAME) is not None:
        return  # same name, other id: leave the user's label alone
    label_reg.async_create(
        FAST_UPDATE_LABEL_NAME,
        icon="mdi:speedometer",
        description="Home Assistant reads entities of the ETA integration with this label more often.",
    )


def _entry_rows(
    hass: HomeAssistant, entry: ConfigEntry
) -> list[tuple[str, str, str | None]]:
    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)
    rows = []
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.disabled_by is not None:
            continue
        device = dev_reg.async_get(reg_entry.device_id) if reg_entry.device_id else None
        device_name = (device.name_by_user or device.name) if device else None
        rows.append((reg_entry.unique_id, reg_entry.entity_id, device_name))
    return rows


@callback
def async_get_topology(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Return the topology of every loaded ETA config entry."""
    ent_reg = er.async_get(hass)
    result = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        stable = _stable(entry)
        blocks, plant = build_blocks(_entry_rows(hass, entry), stable)
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
    stable = _stable(entry)
    regs = er.async_entries_for_config_entry(ent_reg, entry.entry_id)
    rows = [
        (reg.unique_id, reg.entity_id, None, reg.unit_of_measurement)
        for reg in regs
        if reg.disabled_by is None
    ]
    uid_of = {reg.entity_id: reg.unique_id for reg in regs}
    return {
        "objects": build_report(rows, stable),
        "manual": manual_report(manual or [], uid_of, stable),
    }


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
