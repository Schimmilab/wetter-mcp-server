"""HTTP-Client für Open-Meteo: Geocoding (Ortsname → Koordinaten) + Forecast.

Kein API-Key nötig. Alle Fehler werden als WeatherApiError mit deutscher,
LLM-tauglicher Meldung geworfen.
"""
import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


class WeatherApiError(Exception):
    """Fehler mit LLM-tauglicher, deutscher Meldung."""


async def _get(url: str, params: dict) -> dict:
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise WeatherApiError(f"Wetterdienst nicht erreichbar: {exc}") from exc
    if response.status_code != 200:
        raise WeatherApiError(f"Wetterdienst-Fehler: HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError as exc:
        raise WeatherApiError(
            f"Wetterdienst lieferte keine gültige JSON-Antwort "
            f"(HTTP {response.status_code})."
        ) from exc
