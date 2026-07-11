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
