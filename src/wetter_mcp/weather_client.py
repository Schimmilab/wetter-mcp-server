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


async def geocode(name: str) -> dict:
    """Ortsname → {'lat','lon','label'}. Label = 'Ort, Region, Land'.

    Nimmt den ersten Treffer. Wirft WeatherApiError, wenn kein Ort gefunden wird.
    """
    data = await _get(
        GEOCODING_URL,
        {"name": name, "count": 1, "language": "de", "format": "json"},
    )
    results = data.get("results") or []
    if not results:
        raise WeatherApiError(f"Ort '{name}' nicht gefunden.")
    top = results[0]
    parts = [top.get("name"), top.get("admin1"), top.get("country")]
    label = ", ".join(p for p in parts if p)
    return {"lat": top["latitude"], "lon": top["longitude"], "label": label}
