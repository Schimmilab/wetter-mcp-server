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


@respx.mock
async def test_geocode_result_without_coordinates_raises():
    respx.get(weather_client.GEOCODING_URL).mock(
        return_value=httpx.Response(
            200, json={"results": [{"name": "Nirgendwo"}]}
        )
    )
    with pytest.raises(WeatherApiError, match="Koordinaten"):
        await weather_client.geocode("Nirgendwo")


@respx.mock
async def test_geocode_label_skips_missing_parts():
    respx.get(weather_client.GEOCODING_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"name": "Reykjavik", "latitude": 64.15, "longitude": -21.94,
                     "country": "Island"}
                ]
            },
        )
    )
    geo = await weather_client.geocode("Reykjavik")
    assert geo["label"] == "Reykjavik, Island"


@respx.mock
async def test_fetch_forecast_passes_daily_and_forecast_days():
    route = respx.get(weather_client.FORECAST_URL).mock(
        return_value=httpx.Response(200, json={"daily": {}})
    )
    await weather_client.fetch_forecast(
        1.0, 2.0, daily=["temperature_2m_max"], forecast_days=5
    )
    params = route.calls.last.request.url.params
    assert params["daily"] == "temperature_2m_max"
    assert params["forecast_days"] == "5"
    assert "hourly" not in params


@respx.mock
async def test_fetch_forecast_builds_params_and_returns_json():
    route = respx.get(weather_client.FORECAST_URL).mock(
        return_value=httpx.Response(200, json={"current": {"temperature_2m": 12.3}})
    )
    raw = await weather_client.fetch_forecast(
        48.6, 9.1, current=["temperature_2m", "weather_code"]
    )
    assert raw == {"current": {"temperature_2m": 12.3}}
    params = route.calls.last.request.url.params
    assert params["latitude"] == "48.6"
    assert params["longitude"] == "9.1"
    assert params["timezone"] == "auto"
    assert params["wind_speed_unit"] == "kmh"
    assert params["current"] == "temperature_2m,weather_code"


@respx.mock
async def test_fetch_forecast_passes_hourly_and_forecast_hours():
    route = respx.get(weather_client.FORECAST_URL).mock(
        return_value=httpx.Response(200, json={"hourly": {}})
    )
    await weather_client.fetch_forecast(
        1.0, 2.0, hourly=["precipitation"], forecast_hours=12
    )
    params = route.calls.last.request.url.params
    assert params["hourly"] == "precipitation"
    assert params["forecast_hours"] == "12"
    assert "daily" not in params
