import pytest

from wetter_mcp import server, weather_client
from wetter_mcp.weather_client import WeatherApiError


async def test_resolve_location_default_no_geocode(monkeypatch):
    async def fail_geocode(name):
        raise AssertionError("geocode darf beim Default nicht aufgerufen werden")

    monkeypatch.setattr(weather_client, "geocode", fail_geocode)
    lat, lon, label = await server.resolve_location(None)
    assert (lat, lon, label) == (server.DEFAULT_LAT, server.DEFAULT_LON, server.DEFAULT_ORT)


async def test_resolve_location_empty_string_is_default(monkeypatch):
    async def fail_geocode(name):
        raise AssertionError("geocode darf bei leerem String nicht aufgerufen werden")

    monkeypatch.setattr(weather_client, "geocode", fail_geocode)
    lat, lon, label = await server.resolve_location("   ")
    assert label == server.DEFAULT_ORT


async def test_resolve_location_explicit_calls_geocode(monkeypatch):
    async def fake_geocode(name):
        assert name == "Bozen"
        return {"lat": 46.5, "lon": 11.35, "label": "Bozen, Südtirol, Italien"}

    monkeypatch.setattr(weather_client, "geocode", fake_geocode)
    lat, lon, label = await server.resolve_location("Bozen")
    assert (lat, lon, label) == (46.5, 11.35, "Bozen, Südtirol, Italien")


async def test_resolve_location_unknown_propagates(monkeypatch):
    async def fake_geocode(name):
        raise WeatherApiError("Ort 'Xyz' nicht gefunden.")

    monkeypatch.setattr(weather_client, "geocode", fake_geocode)
    with pytest.raises(WeatherApiError, match="nicht gefunden"):
        await server.resolve_location("Xyz")


async def test_get_current_weather_uses_current_fields(monkeypatch):
    async def fake_resolve(location):
        return 48.6, 9.1, "Steinenbronn"

    captured = {}

    async def fake_fetch(lat, lon, **kwargs):
        captured.update(kwargs)
        return {
            "current": {
                "time": "2026-07-11T18:00",
                "temperature_2m": 21.4,
                "apparent_temperature": 20.1,
                "relative_humidity_2m": 55,
                "precipitation": 0.0,
                "cloud_cover": 30,
                "wind_speed_10m": 9.2,
                "weather_code": 2,
            }
        }

    monkeypatch.setattr(server, "resolve_location", fake_resolve)
    monkeypatch.setattr(server.weather_client, "fetch_forecast", fake_fetch)
    out = await server.get_current_weather()
    assert captured["current"] == server.CURRENT_FIELDS
    assert out["ort"] == "Steinenbronn"
    assert out["temperatur_c"] == 21.4
    assert out["wetter"] == "teils bewölkt"


async def test_get_hourly_forecast_caps_hours_high(monkeypatch):
    captured = {}

    async def fake_resolve(location):
        return 1.0, 2.0, "X"

    async def fake_fetch(lat, lon, **kwargs):
        captured.update(kwargs)
        return {"hourly": {"time": []}}

    monkeypatch.setattr(server, "resolve_location", fake_resolve)
    monkeypatch.setattr(server.weather_client, "fetch_forecast", fake_fetch)
    await server.get_hourly_forecast(hours=999)
    assert captured["hourly"] == server.HOURLY_FIELDS
    assert captured["forecast_hours"] == 48


async def test_get_hourly_forecast_caps_hours_low(monkeypatch):
    captured = {}

    async def fake_resolve(location):
        return 1.0, 2.0, "X"

    async def fake_fetch(lat, lon, **kwargs):
        captured.update(kwargs)
        return {"hourly": {"time": []}}

    monkeypatch.setattr(server, "resolve_location", fake_resolve)
    monkeypatch.setattr(server.weather_client, "fetch_forecast", fake_fetch)
    await server.get_hourly_forecast(hours=0)
    assert captured["forecast_hours"] == 1


async def test_get_daily_forecast_caps_days(monkeypatch):
    captured = {}

    async def fake_resolve(location):
        return 1.0, 2.0, "X"

    async def fake_fetch(lat, lon, **kwargs):
        captured.update(kwargs)
        return {"daily": {"time": []}}

    monkeypatch.setattr(server, "resolve_location", fake_resolve)
    monkeypatch.setattr(server.weather_client, "fetch_forecast", fake_fetch)
    await server.get_daily_forecast(days=99)
    assert captured["daily"] == server.DAILY_FIELDS
    assert captured["forecast_days"] == 16


def test_main_is_callable():
    assert callable(server.main)
