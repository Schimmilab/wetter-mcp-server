import httpx
import pytest
import respx

from wetter_mcp import weather_client
from wetter_mcp.weather_client import WeatherApiError

TEST_URL = "https://example.test/api"


@respx.mock
async def test_get_returns_json():
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    data = await weather_client._get(TEST_URL, {"a": 1})
    assert data == {"ok": True}


@respx.mock
async def test_get_network_error_raises():
    respx.get(TEST_URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(WeatherApiError, match="nicht erreichbar"):
        await weather_client._get(TEST_URL, {})


@respx.mock
async def test_get_non_200_raises():
    respx.get(TEST_URL).mock(return_value=httpx.Response(503))
    with pytest.raises(WeatherApiError, match="503"):
        await weather_client._get(TEST_URL, {})


@respx.mock
async def test_get_non_json_raises():
    respx.get(TEST_URL).mock(return_value=httpx.Response(200, text="<html>x</html>"))
    with pytest.raises(WeatherApiError, match="JSON"):
        await weather_client._get(TEST_URL, {})


@respx.mock
async def test_geocode_returns_lat_lon_label():
    respx.get(weather_client.GEOCODING_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {
                        "name": "Steinenbronn",
                        "latitude": 48.66667,
                        "longitude": 9.13333,
                        "country": "Deutschland",
                        "admin1": "Baden-Württemberg",
                    }
                ]
            },
        )
    )
    geo = await weather_client.geocode("Steinenbronn")
    assert geo == {
        "lat": 48.66667,
        "lon": 9.13333,
        "label": "Steinenbronn, Baden-Württemberg, Deutschland",
    }


@respx.mock
async def test_geocode_empty_results_raises():
    respx.get(weather_client.GEOCODING_URL).mock(
        return_value=httpx.Response(200, json={"generationtime_ms": 0.1})
    )
    with pytest.raises(WeatherApiError, match="nicht gefunden"):
        await weather_client.geocode("Xyzzyland")
