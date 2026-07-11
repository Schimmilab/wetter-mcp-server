"""Wetter-MCP-Server — Tool-Schicht. Orchestrierung + Formatierung, keine HTTP-Logik."""
import os

from fastmcp import FastMCP

from wetter_mcp import formatting, weather_client

# Default-Ort: Steinenbronn (Ortsmitte — öffentlich, nicht die Straßenadresse).
# Per Umgebungsvariablen überschreibbar (siehe .env.example).
DEFAULT_LAT = float(os.environ.get("DEFAULT_LAT") or "48.6667")
DEFAULT_LON = float(os.environ.get("DEFAULT_LON") or "9.1333")
DEFAULT_ORT = os.environ.get("DEFAULT_ORT") or "Steinenbronn"

CURRENT_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "cloud_cover",
    "wind_speed_10m",
]
HOURLY_FIELDS = [
    "temperature_2m",
    "precipitation",
    "precipitation_probability",
    "weather_code",
    "wind_speed_10m",
]
DAILY_FIELDS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "sunshine_duration",
    "weather_code",
]

mcp = FastMCP(
    "wetter",
    instructions=(
        "Wetterprognose über Open-Meteo (kein API-Key). Ohne Ortsangabe gilt "
        "Zuhause (Steinenbronn). location kann ein beliebiger Ort sein "
        "(z.B. 'Bozen', 'Stockholm', 'Südtirol') — er wird per Geocoding "
        "aufgelöst; die Antwort nennt den aufgelösten Ort. "
        "Temperaturen in °C, Niederschlag in mm, Wind in km/h, Zeiten in Ortszeit."
    ),
)


async def resolve_location(location: str | None) -> tuple[float, float, str]:
    """location leer/None → Default (Zuhause). Sonst per Geocoding auflösen."""
    if location is None or not location.strip():
        return DEFAULT_LAT, DEFAULT_LON, DEFAULT_ORT
    geo = await weather_client.geocode(location.strip())
    return geo["lat"], geo["lon"], geo["label"]


async def get_current_weather(location: str | None = None) -> dict:
    """Aktuelles Wetter: Temperatur, gefühlte Temperatur, Luftfeuchte, Wind,
    Bewölkung, aktueller Niederschlag. Ohne location = Zuhause (Steinenbronn)."""
    lat, lon, label = await resolve_location(location)
    raw = await weather_client.fetch_forecast(lat, lon, current=CURRENT_FIELDS)
    return formatting.format_current(raw, label)


async def get_hourly_forecast(location: str | None = None, hours: int = 24) -> dict:
    """Stündliche Vorhersage: Temperatur, Regen (mm + Wahrscheinlichkeit), Wind,
    Wetterlage. hours 1–48 (Standard 24). Ohne location = Zuhause.

    Für 'kann ich die Fenster nachts offen lassen?' die Nachtstunden auf
    Niederschlag und Minimaltemperatur prüfen."""
    hours = max(1, min(hours, 48))
    lat, lon, label = await resolve_location(location)
    raw = await weather_client.fetch_forecast(
        lat, lon, hourly=HOURLY_FIELDS, forecast_hours=hours
    )
    return formatting.format_hourly(raw, label, hours)


async def get_daily_forecast(location: str | None = None, days: int = 7) -> dict:
    """Tagesvorhersage: Min/Max-Temperatur, Regensumme + Wahrscheinlichkeit,
    Sonnenstunden, Wetterlage. days 1–16 (Standard 7). Ohne location = Zuhause.

    Für Reisewetter je Roadtrip-Station die location auf den jeweiligen Ort setzen."""
    days = max(1, min(days, 16))
    lat, lon, label = await resolve_location(location)
    raw = await weather_client.fetch_forecast(
        lat, lon, daily=DAILY_FIELDS, forecast_days=days
    )
    return formatting.format_daily(raw, label, days)


mcp.tool(get_current_weather)
mcp.tool(get_hourly_forecast)
mcp.tool(get_daily_forecast)


def main() -> None:
    mcp.run()
