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

Optional über **Umgebungsvariablen** `DEFAULT_LAT`, `DEFAULT_LON`, `DEFAULT_ORT`
— z.B. bei der Registrierung mit `claude mcp add … -e DEFAULT_LAT=…`. Die
`.env`-Datei wird **nicht** automatisch geladen; `.env.example` listet nur die
Variablennamen. Ohne diese Variablen nutzt der Server Steinenbronn (Ortsmitte,
in `server.py` hinterlegt) — der Server läuft also ohne jede Konfiguration.

## Entwicklung

    uv sync
    uv run pytest

## Start

    uv run wetter-mcp
