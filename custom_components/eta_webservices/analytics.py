"""Computed values of the plant ("ETA Auswertung").

Ash box fill level, pellet consumption per day and forecasts for ash box and
pellet store. The inputs are ETA values the user selected (found via the fixed
addresses in roles.json); the history comes from Home Assistant's long-term
statistics of the total consumption counter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STABLE_ID
from .topology import build_blocks
from .utils import create_device_info

_LOGGER = logging.getLogger(__name__)

ANALYTICS = "analytics"
DEVICE_NAME = "Auswertung"
AVG_DAYS = 14
# seasonal forecast: needs most of the last year as daily consumption
SEASON_MIN_DAYS = 300
HORIZON_DAYS = 3 * 365

# block type -> roles read from the plant
_SOURCES = {
    "boiler": ("ash_used", "ash_limit", "consumption_total"),
    "silo": ("stock", "stock_warn"),
}


def find_sources(unique_ids: list[str], stable: str) -> dict[str, str]:
    """Return role -> unique_id of the inputs among the selected values."""
    blocks, _ = build_blocks([(uid, uid, None) for uid in unique_ids], stable)
    found: dict[str, str] = {}
    for block in blocks:
        for role in _SOURCES.get(block.type, ()):
            if role in block.roles and role not in found:
                found[role] = block.roles[role]
    return found


@dataclass(frozen=True)
class Spec:
    """One computed value."""

    key: str
    needs: tuple[str, ...]
    unit: str | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    precision: int | None = None
    options: tuple[str, ...] | None = None


SPECS = (
    Spec("ash_fill", ("ash_used", "ash_limit"), PERCENTAGE, None, SensorStateClass.MEASUREMENT, 0),
    Spec("ash_days", ("ash_used", "ash_limit", "consumption_total"), "d", SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT, 0),
    Spec("ash_date", ("ash_used", "ash_limit", "consumption_total"), None, SensorDeviceClass.DATE),
    Spec("pellets_today", ("consumption_total",), "kg", SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL_INCREASING, 1),
    Spec("pellets_yesterday", ("consumption_total",), "kg", SensorDeviceClass.WEIGHT, SensorStateClass.MEASUREMENT, 1),
    Spec("pellets_avg", ("consumption_total",), "kg/d", None, SensorStateClass.MEASUREMENT, 1),
    Spec("silo_days", ("stock", "consumption_total"), "d", SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT, 0),
    Spec("silo_date", ("stock", "consumption_total"), None, SensorDeviceClass.DATE),
    Spec("method", ("consumption_total",), None, SensorDeviceClass.ENUM, options=("seasonal", "average")),
)  # fmt: skip


def daily_consumption(rows: list[tuple[date, float]]) -> dict[date, float]:
    """Consumption per day from the counter value at the end of each day."""
    by_day = dict(rows)
    out: dict[date, float] = {}
    for day, value in by_day.items():
        prev = by_day.get(day - timedelta(days=1))
        if prev is not None and value >= prev:  # skip counter resets
            out[day] = value - prev
    return out


def forecast_days(
    remaining: float,
    avg: float | None,
    daily: dict[date, float] | None,
    today: date,
) -> tuple[float | None, str | None]:
    """Days until `remaining` kg are used up, and the method used.

    With most of a year recorded, every coming day uses the consumption of the
    same day last year, scaled by how the last 14 days compare to the same 14
    days last year (mild or cold winter); the scaling fades out after about a
    month. Otherwise the 14-day average.
    """
    if remaining <= 0:
        return 0, "average" if not daily else "seasonal"
    if daily:
        base = today - timedelta(days=365)
        year = [daily.get(base + timedelta(days=k)) for k in range(365)]
        known = [v for v in year if v is not None]
        if len(known) >= SEASON_MIN_DAYS:
            fill = sum(known) / len(known)
            curve = [fill if v is None else v for v in year]
            recent = [daily.get(today - timedelta(days=k)) for k in range(1, 15)]
            before = [daily.get(base - timedelta(days=k)) for k in range(1, 15)]
            factor = 1.0
            if None not in recent and None not in before and sum(before) >= 5:
                factor = min(max(sum(recent) / sum(before), 0.3), 3.0)
            left = remaining
            for k in range(HORIZON_DAYS):
                # the recent trend holds for about a month, then fades to last year
                weight = min(max((90 - k) / 60, 0.0), 1.0)
                left -= curve[k % 365] * (1 + (factor - 1) * weight)
                if left <= 0:
                    return k + 1, "seasonal"
    if avg and avg > 0:
        return remaining / avg, "average"
    return None, None


def compute(
    values: dict[str, float],
    at_midnight: float | None,
    at_prev_midnight: float | None,
    avg: float | None,
    today: date,
    daily: dict[date, float] | None = None,
) -> dict[str, Any]:
    """Derive all values from the current inputs and the counter history."""
    out: dict[str, Any] = {}
    used, limit = values.get("ash_used"), values.get("ash_limit")
    total, stock = values.get("consumption_total"), values.get("stock")
    if used is not None and limit:
        out["ash_fill"] = round(used / limit * 100, 1)
    if total is not None and at_midnight is not None:
        out["pellets_today"] = round(max(total - at_midnight, 0.0), 1)
    if at_midnight is not None and at_prev_midnight is not None:
        out["pellets_yesterday"] = round(max(at_midnight - at_prev_midnight, 0.0), 1)
    if avg is not None:
        out["pellets_avg"] = round(avg, 1)
    for key, remaining in (
        ("ash", limit - used if used is not None and limit else None),
        ("silo", stock),
    ):
        if remaining is None:
            continue
        days, method = forecast_days(max(remaining, 0.0), avg, daily, today)
        if days is not None:
            out[f"{key}_days"] = round(days)
            out[f"{key}_date"] = today + timedelta(days=round(days))
            out["method"] = method
    return out


class EtaAnalyticsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Recomputes the values every few minutes from states and statistics."""

    def __init__(
        self, hass: HomeAssistant, config: dict, sources: dict[str, str]
    ) -> None:
        """Set up for one plant; sources maps role -> unique_id."""
        super().__init__(
            hass,
            _LOGGER,
            name="ETA analytics",
            update_interval=timedelta(minutes=5),
        )
        self.sources = sources
        self.config = config
        self._history: tuple[datetime, float | None, float | None, float | None]
        self._history = (datetime.min.replace(tzinfo=dt_util.UTC), None, None, None)
        self._daily: tuple[date | None, dict[date, float]] = (None, {})

    def _entity_id(self, unique_id: str) -> str | None:
        reg = er.async_get(self.hass)
        domains = (
            ("number", "sensor") if unique_id.endswith("_writable") else ("sensor",)
        )
        for domain in domains:
            if entity_id := reg.async_get_entity_id(domain, DOMAIN, unique_id):
                return entity_id
        return None

    def _value(self, role: str) -> float | None:
        unique_id = self.sources.get(role)
        entity_id = unique_id and self._entity_id(unique_id)
        state = entity_id and self.hass.states.get(entity_id)
        try:
            return float(state.state) if state else None
        except ValueError:
            return None

    async def _counter_at(self, statistic_id: str, when: datetime) -> float | None:
        """Counter value at a point in time from the hourly statistics."""
        rows = await self._stats(statistic_id, when - timedelta(hours=1), when)
        return rows[-1]["max"] if rows else None

    async def _stats(
        self, statistic_id: str, start: datetime, end: datetime, period: str = "hour"
    ) -> list[dict[str, Any]]:
        try:
            from homeassistant.components.recorder import get_instance  # noqa: PLC0415
            from homeassistant.components.recorder.statistics import (  # noqa: PLC0415
                statistics_during_period,
            )

            result = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                start,
                end,
                {statistic_id},
                period,
                None,
                {"max", "min"},
            )
        except Exception:  # noqa: BLE001 - recorder missing or not ready
            return []
        return [r for r in result.get(statistic_id, []) if r.get("max") is not None]

    async def _history_values(self) -> tuple[float | None, float | None, float | None]:
        """Counter at midnight, at the previous midnight and the average per day."""
        midnight = dt_util.start_of_local_day()
        cached_at, at_mid, at_prev, avg = self._history
        # at most hourly, and fresh after midnight (new day)
        fresh = max(dt_util.utcnow() - timedelta(hours=1), midnight)
        if cached_at > fresh and at_mid is not None:
            return at_mid, at_prev, avg
        unique_id = self.sources.get("consumption_total")
        entity_id = unique_id and self._entity_id(unique_id)
        if not entity_id:
            return None, None, None
        at_mid = await self._counter_at(entity_id, midnight)
        if at_mid is None:
            # recorded only since today: count from the first value of the day
            today = await self._stats(entity_id, midnight, dt_util.utcnow())
            if today and today[0].get("min") is not None:
                at_mid = today[0]["min"]
        at_prev = await self._counter_at(entity_id, midnight - timedelta(days=1))
        # average over the last AVG_DAYS full days, or as many as recorded
        rows = await self._stats(
            entity_id, midnight - timedelta(days=AVG_DAYS), midnight
        )
        avg = None
        if rows and at_mid is not None:
            first = rows[0]
            start = first["start"]
            start = (
                dt_util.utc_from_timestamp(start)
                if isinstance(start, (int, float))
                else start
            )
            days = (midnight - start).total_seconds() / 86400
            if days >= 1:
                avg = max(at_mid - first["max"], 0.0) / days
        self._history = (dt_util.utcnow(), at_mid, at_prev, avg)
        return at_mid, at_prev, avg

    async def _async_update_data(self) -> dict[str, Any]:
        values = {
            role: value
            for role in self.sources
            if (value := self._value(role)) is not None
        }
        at_mid, at_prev, avg = await self._history_values()
        today = dt_util.now().date()
        return compute(
            values, at_mid, at_prev, avg, today, await self._daily_values(today)
        )

    async def _daily_values(self, today: date) -> dict[date, float]:
        """Consumption per day of the last year (+14 days), refreshed daily."""
        if self._daily[0] == today:
            return self._daily[1]
        unique_id = self.sources.get("consumption_total")
        entity_id = unique_id and self._entity_id(unique_id)
        if not entity_id:
            return {}
        midnight = dt_util.start_of_local_day()
        rows = await self._stats(
            entity_id, midnight - timedelta(days=365 + 16), midnight, "day"
        )
        points = []
        for row in rows:
            start = row["start"]
            if isinstance(start, (int, float)):
                start = dt_util.utc_from_timestamp(start)
            points.append((dt_util.as_local(start).date(), row["max"]))
        self._daily = (today, daily_consumption(points))
        return self._daily[1]


class EtaAnalyticsSensor(CoordinatorEntity[EtaAnalyticsCoordinator], SensorEntity):
    """One computed value on the "Auswertung" device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EtaAnalyticsCoordinator, spec: Spec) -> None:
        """Create the sensor for one spec."""
        super().__init__(coordinator)
        config = coordinator.config
        host = config.get(CONF_HOST, "")
        stable = config.get(STABLE_ID) or host.replace(".", "_")
        self._key = spec.key
        self._attr_unique_id = f"eta_{stable}_{ANALYTICS}_{spec.key}"
        self._attr_translation_key = f"analytics_{spec.key}"
        self._attr_native_unit_of_measurement = spec.unit
        self._attr_device_class = spec.device_class
        self._attr_state_class = spec.state_class
        self._attr_suggested_display_precision = spec.precision
        if spec.options:
            self._attr_options = list(spec.options)
        self._attr_device_info = create_device_info(
            host, config.get(CONF_PORT, ""), DEVICE_NAME, config.get(CONF_NAME)
        )

    async def async_added_to_hass(self) -> None:
        """Recompute once the source values are loaded after startup."""
        await super().async_added_to_hass()

        async def _later(_now: datetime) -> None:
            await self.coordinator.async_request_refresh()

        self.async_on_remove(async_call_later(self.hass, 60, _later))

    @property
    def native_value(self) -> Any:
        """Return the computed value, None while unknown."""
        return (self.coordinator.data or {}).get(self._key)


async def async_create_analytics(
    hass: HomeAssistant, config: dict, unique_ids: list[str]
) -> list[SensorEntity]:
    """Create the computed sensors whose inputs are selected."""
    stable = config.get(STABLE_ID) or str(config.get(CONF_HOST, "")).replace(".", "_")
    sources = find_sources(unique_ids, stable)
    specs = [s for s in SPECS if all(role in sources for role in s.needs)]
    if not specs:
        return []
    coordinator = EtaAnalyticsCoordinator(hass, config, sources)
    await coordinator.async_refresh()
    return [EtaAnalyticsSensor(coordinator, spec) for spec in specs]
