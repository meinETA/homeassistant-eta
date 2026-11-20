"""Tests for the computed values (ash box, pellet consumption, forecasts)."""

from datetime import date, timedelta

from custom_components.eta_webservices.analytics import (
    compute,
    daily_consumption,
    find_sources,
    forecast_days,
    terminal_language,
)

STABLE = "keller"


def _uid(uri: str) -> str:
    return f"eta_{STABLE}_" + uri.strip("/").replace("/", "_")


def test_find_sources_by_address() -> None:
    """Inputs are found via the fixed addresses, writable twins included."""
    ids = [
        _uid("/264/10891/0/0/12013"),
        _uid("/264/10891/0/0/12120") + "_writable",
        _uid("/264/10891/0/0/12016"),
        _uid("/264/10201/0/0/12015"),
        _uid("/264/10891/0/0/12000"),
    ]
    found = find_sources(ids, STABLE)
    assert found == {
        "ash_used": ids[0],
        "ash_limit": ids[1],
        "consumption_total": ids[2],
        "stock": ids[3],
    }


def test_compute_fill_consumption_and_forecast() -> None:
    """Fill level, daily consumption and the days until full / empty."""
    values = {
        "ash_used": 150.0,
        "ash_limit": 1500.0,
        "consumption_total": 7770.0,
        "stock": 600.0,
    }
    out = compute(values, 7762.0, 7740.0, 20.0, date(2026, 11, 19))
    assert out["ash_fill"] == 10.0
    assert out["pellets_today"] == 8.0
    assert out["pellets_yesterday"] == 22.0
    assert out["pellets_avg"] == 20.0
    assert out["ash_days"] == 68  # 1350 kg left / 20 kg per day
    assert out["ash_date"] == date(2027, 1, 26)
    assert out["silo_days"] == 30
    assert out["silo_date"] == date(2026, 12, 19)


def test_compute_without_history() -> None:
    """No statistics yet: only the fill level, no forecast."""
    out = compute(
        {"ash_used": 100.0, "ash_limit": 1500.0}, None, None, None, date(2026, 11, 19)
    )
    assert out == {"ash_fill": 6.7}


def test_daily_consumption_skips_resets() -> None:
    """Per-day consumption from end-of-day counter values; resets are skipped."""
    d = date(2026, 1, 1)
    rows = [(d, 100.0), (d + timedelta(days=1), 120.0), (d + timedelta(days=2), 5.0)]
    assert daily_consumption(rows) == {d + timedelta(days=1): 20.0}


def _year(today: date, value, winter: float = 10.0) -> dict:
    """Daily values for the last 381 days; `value(k)` for days after last year's today."""
    base = today - timedelta(days=365)
    out = {}
    for k in range(-16, 365):
        out[base + timedelta(days=k)] = value(k) if k >= 0 else winter
    return out


def test_forecast_uses_last_year_curve() -> None:
    """Coming days use last year's consumption of the same days."""
    today = date(2026, 11, 19)
    daily = _year(today, lambda k: 50.0 if k < 30 else 10.0)
    for k in range(1, 15):  # last 14 days like last year: factor 1
        daily[today - timedelta(days=k)] = 10.0
    days, method = forecast_days(600.0, 10.0, daily, today)
    assert (days, method) == (12, "seasonal")  # 50 kg per day, not 60 days at 10


def test_forecast_scales_with_recent_consumption() -> None:
    """A colder start than last year shortens the forecast."""
    today = date(2026, 11, 19)
    daily = _year(today, lambda k: 10.0)
    for k in range(1, 15):
        daily[today - timedelta(days=k)] = 20.0  # twice last year's consumption
    days, _ = forecast_days(400.0, 20.0, daily, today)
    assert days == 20


def test_forecast_falls_back_to_average() -> None:
    """Less than a year of statistics: the 14-day average."""
    days, method = forecast_days(300.0, 15.0, {}, date(2026, 11, 19))
    assert (days, method) == (20.0, "average")


def test_terminal_language_from_menu_names() -> None:
    """Device name follows the language of the ETA menu names."""
    de = ["Kessel > Zählerstände > Gesamtverbrauch", "Puffer > Eingänge > Fühler 1"]
    en = ["Boiler > Counters > Total consumption", "Buffer > Inputs > Sensor 1"]
    assert terminal_language(de) == "de"
    assert terminal_language(en) == "en"
    assert terminal_language(["Caldaia > Contatori"]) == "en"
