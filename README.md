# wetter-mcp-server

MCP-Server für Wetterprognosen über [Open-Meteo](https://open-meteo.com) — kein API-Key nötig.

## Tools

- `get_current_weather(location?)` — aktuelles Wetter
- `get_hourly_forecast(location?, hours=24)` — stündlich (1–48 h)
- `get_daily_forecast(location?, days=7)` — täglich (1–16 Tage)

Ohne `location` gilt der Standard-Ort (Steinenbronn). `location` kann ein
beliebiger Ortsname sein (z.B. `"Bozen"`, `"Stockholm"`) und wird per Geocoding
aufgelöst. Temperaturen in °C, Niederschlag in mm, Wind in km/h, Zeiten in Ortszeit.

## Standard-Ort ändern

Optional über Umgebungsvariablen (siehe `.env.example`): `DEFAULT_LAT`,
`DEFAULT_LON`, `DEFAULT_ORT`. Ohne diese nutzt der Server Steinenbronn.

## Entwicklung

    uv sync
    uv run pytest

## Start

    uv run wetter-mcp
