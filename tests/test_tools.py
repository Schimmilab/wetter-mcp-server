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
