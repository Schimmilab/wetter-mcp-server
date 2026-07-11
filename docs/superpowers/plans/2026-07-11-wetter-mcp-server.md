# Wetter-MCP-Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ein lokaler MCP-Server, der Claude Wetterprognosen (aktuell / stündlich / täglich) über Open-Meteo liefert — für Zuhause (Steinenbronn, Default) und beliebige Orte weltweit (Reisewetter).

**Architecture:** FastMCP-Server nach dem Muster von `tibber-mcp-server`. Drei Schichten: `weather_client.py` (httpx-Aufrufe an Open-Meteo: Geocoding + Forecast, alle Fehler als `WeatherApiError`), `formatting.py` (reine Funktionen: Roh-JSON → kompakte deutsche Ausgabe), `server.py` (Tool-Schicht: Ortsauflösung, Orchestrierung, Registrierung). Kein API-Key, kein State, kein Cache.

**Tech Stack:** Python ≥3.11, `fastmcp>=3`, `httpx>=0.27`, `pytest` + `pytest-asyncio` (`asyncio_mode=auto`) + `respx` (httpx-Mocking), uv/hatchling, GitHub-Actions-CI.

---

## Dateistruktur

Neu anzulegen (Repo existiert bereits mit `.git` + `.gitignore` + `docs/`):

```
~/workspace/wetter-mcp-server/
  pyproject.toml              # Projekt, Deps, Script-Entry, pytest-Config
  LICENSE                     # MIT (von tibber kopiert)
  README.md                   # Kurzdoku
  .env.example                # DEFAULT_LAT / DEFAULT_LON / DEFAULT_ORT (leer)
  .github/workflows/ci.yml    # uv sync + uv run pytest
  src/wetter_mcp/
    __init__.py               # leer
    weather_client.py         # httpx: _get(), geocode(), fetch_forecast(); WeatherApiError
    formatting.py             # WEATHER_CODES, describe_code(), format_current/hourly/daily()
    server.py                 # FastMCP, resolve_location(), 3 Tools, main()
  tests/
    __init__.py               # leer
    test_weather_client.py    # respx: _get/geocode/fetch_forecast inkl. Fehlerpfade
    test_formatting.py        # reine Funktionen auf Beispiel-Payloads
    test_tools.py             # Tool-Ebene: Default-Ort, expliziter Ort, Parameter-Kappung
```

**Verantwortlichkeiten (klare Grenzen):**
- `weather_client.py` kennt nur HTTP + Open-Meteo-Endpoints. Weiß nichts von MCP.
- `formatting.py` ist rein (Dict rein → Dict raus), kein I/O, kein Netz. Vollständig ohne Mocks testbar.
- `server.py` verdrahtet beide + macht die Ortsauflösung. Enthält keine HTTP-Logik.

---

### Task 1: Projekt-Gerüst

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `.env.example`
- Create: `.github/workflows/ci.yml`
- Create: `src/wetter_mcp/__init__.py` (leer)
- Create: `tests/__init__.py` (leer)
- Modify: `.gitignore` (erweitern)
- Test: `tests/test_smoke.py`

- [ ] **Step 1: `pyproject.toml` schreiben**

```toml
[project]
name = "wetter-mcp-server"
version = "0.1.0"
description = "MCP-Server für Wetterprognosen über Open-Meteo (kein API-Key)"
license = { text = "MIT" }
authors = [{ name = "Jürgen Schilling" }]
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=3",
    "httpx>=0.27",
]

[project.urls]
Repository = "https://github.com/Schimmilab/wetter-mcp-server"

[project.scripts]
wetter-mcp = "wetter_mcp.server:main"

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "respx>=0.21",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/wetter_mcp"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
```

- [ ] **Step 2: Restliche Gerüst-Dateien anlegen**

`LICENSE` (MIT von tibber übernehmen, gleicher Autor):
```bash
cp ~/workspace/tibber-mcp-server/LICENSE ~/workspace/wetter-mcp-server/LICENSE
```

`.env.example`:
```
# Standard-Ort für Wetterabfragen ohne location-Angabe.
# Leer lassen = Server nutzt Steinenbronn (Ortsmitte, in server.py hinterlegt).
DEFAULT_LAT=
DEFAULT_LON=
DEFAULT_ORT=
```

`.github/workflows/ci.yml`:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.12"
      - run: uv sync
      - run: uv run pytest
```

`src/wetter_mcp/__init__.py` und `tests/__init__.py`: leere Dateien anlegen.

`.gitignore` auf diesen Inhalt erweitern (ersetzen):
```
.idea/
__pycache__/
.venv/
*.egg-info/
*.pyc
.pytest_cache/
.ruff_cache/
.env
*.iml
```

- [ ] **Step 3: Smoke-Test schreiben (failing)**

`tests/test_smoke.py`:
```python
def test_package_importierbar():
    import wetter_mcp

    assert wetter_mcp is not None
```

- [ ] **Step 4: Deps installieren + Test laufen lassen**

Run: `cd ~/workspace/wetter-mcp-server && uv sync && uv run pytest tests/test_smoke.py -v`
Expected: PASS (1 passed). `uv sync` legt `.venv` + `uv.lock` an.

- [ ] **Step 5: Commit**

```bash
cd ~/workspace/wetter-mcp-server
git add -A
git commit -m "chore: Projekt-Gerüst (pyproject, CI, Paket-Skelett)"
```

---

### Task 2: HTTP-Kern `_get()` im weather_client

**Files:**
- Create: `src/wetter_mcp/weather_client.py`
- Test: `tests/test_weather_client.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_weather_client.py`:
```python
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
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `cd ~/workspace/wetter-mcp-server && uv run pytest tests/test_weather_client.py -v`
Expected: FAIL (ModuleNotFoundError: `wetter_mcp.weather_client` bzw. `_get` nicht definiert).

- [ ] **Step 3: `weather_client.py` mit `_get()` implementieren**

`src/wetter_mcp/weather_client.py`:
```python
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
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `cd ~/workspace/wetter-mcp-server && uv run pytest tests/test_weather_client.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/weather_client.py tests/test_weather_client.py
git commit -m "feat: HTTP-Kern _get() mit Fehlerbehandlung"
```

---

### Task 3: `geocode()` — Ortsname → Koordinaten

**Files:**
- Modify: `src/wetter_mcp/weather_client.py`
- Test: `tests/test_weather_client.py`

- [ ] **Step 1: Failing tests anhängen**

An `tests/test_weather_client.py` anhängen:
```python
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
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_weather_client.py -k geocode -v`
Expected: FAIL (`geocode` nicht definiert).

- [ ] **Step 3: `geocode()` implementieren**

An `src/wetter_mcp/weather_client.py` anhängen:
```python
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
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_weather_client.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/weather_client.py tests/test_weather_client.py
git commit -m "feat: geocode() — Ortsname zu Koordinaten"
```

---

### Task 4: `fetch_forecast()` — Forecast-Abruf mit korrekten Parametern

**Files:**
- Modify: `src/wetter_mcp/weather_client.py`
- Test: `tests/test_weather_client.py`

- [ ] **Step 1: Failing tests anhängen**

An `tests/test_weather_client.py` anhängen:
```python
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
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_weather_client.py -k fetch_forecast -v`
Expected: FAIL (`fetch_forecast` nicht definiert).

- [ ] **Step 3: `fetch_forecast()` implementieren**

An `src/wetter_mcp/weather_client.py` anhängen:
```python
async def fetch_forecast(
    lat: float,
    lon: float,
    *,
    current: list[str] | None = None,
    hourly: list[str] | None = None,
    daily: list[str] | None = None,
    forecast_hours: int | None = None,
    forecast_days: int | None = None,
) -> dict:
    """Roh-JSON vom Open-Meteo-Forecast-Endpoint für die gegebenen Felder.

    timezone=auto liefert Ortszeit (wichtig fürs Reisewetter). Wind in km/h.
    """
    params: dict = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        "wind_speed_unit": "kmh",
    }
    if current:
        params["current"] = ",".join(current)
    if hourly:
        params["hourly"] = ",".join(hourly)
    if daily:
        params["daily"] = ",".join(daily)
    if forecast_hours is not None:
        params["forecast_hours"] = forecast_hours
    if forecast_days is not None:
        params["forecast_days"] = forecast_days
    return await _get(FORECAST_URL, params)
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_weather_client.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/weather_client.py tests/test_weather_client.py
git commit -m "feat: fetch_forecast() — Open-Meteo-Forecast-Abruf"
```

---

### Task 5: `formatting.py` — Wettercodes + `describe_code()`

**Files:**
- Create: `src/wetter_mcp/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Failing test schreiben**

`tests/test_formatting.py`:
```python
from wetter_mcp import formatting


def test_describe_code_known():
    assert formatting.describe_code(0) == "klar"
    assert formatting.describe_code(61) == "leichter Regen"
    assert formatting.describe_code(95) == "Gewitter"


def test_describe_code_none():
    assert formatting.describe_code(None) == "unbekannt"


def test_describe_code_unknown_number():
    assert formatting.describe_code(4242) == "Wettercode 4242"
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: FAIL (`wetter_mcp.formatting` nicht vorhanden).

- [ ] **Step 3: `formatting.py` mit Codes + Helfer anlegen**

`src/wetter_mcp/formatting.py`:
```python
"""Roh-JSON von Open-Meteo → kompakte, benannte Ausgabe für das LLM.

Reine Funktionen ohne I/O. WMO-Wettercodes → deutsche Klartext-Beschreibung.
"""

WEATHER_CODES: dict[int, str] = {
    0: "klar",
    1: "überwiegend klar",
    2: "teils bewölkt",
    3: "bedeckt",
    45: "Nebel",
    48: "gefrierender Nebel",
    51: "leichter Nieselregen",
    53: "Nieselregen",
    55: "starker Nieselregen",
    56: "leichter gefrierender Nieselregen",
    57: "gefrierender Nieselregen",
    61: "leichter Regen",
    63: "Regen",
    65: "starker Regen",
    66: "leichter gefrierender Regen",
    67: "gefrierender Regen",
    71: "leichter Schneefall",
    73: "Schneefall",
    75: "starker Schneefall",
    77: "Schneegriesel",
    80: "leichte Regenschauer",
    81: "Regenschauer",
    82: "heftige Regenschauer",
    85: "leichte Schneeschauer",
    86: "starke Schneeschauer",
    95: "Gewitter",
    96: "Gewitter mit leichtem Hagel",
    99: "Gewitter mit Hagel",
}


def describe_code(code: int | None) -> str:
    if code is None:
        return "unbekannt"
    return WEATHER_CODES.get(code, f"Wettercode {code}")


def _at(block: dict, key: str, i: int):
    """Wert an Index i aus einem Open-Meteo-Array-Block, None wenn nicht vorhanden."""
    arr = block.get(key)
    if not arr or i >= len(arr):
        return None
    return arr[i]
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: Wettercode-Mapping + describe_code()"
```

---

### Task 6: `format_current()`

**Files:**
- Modify: `src/wetter_mcp/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Failing test anhängen**

An `tests/test_formatting.py` anhängen:
```python
def test_format_current():
    raw = {
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
    out = formatting.format_current(raw, "Steinenbronn")
    assert out == {
        "ort": "Steinenbronn",
        "zeit": "2026-07-11T18:00",
        "temperatur_c": 21.4,
        "gefuehlt_c": 20.1,
        "luftfeuchte_pct": 55,
        "niederschlag_mm": 0.0,
        "bewoelkung_pct": 30,
        "wind_kmh": 9.2,
        "wetter": "teils bewölkt",
    }
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_formatting.py -k format_current -v`
Expected: FAIL (`format_current` nicht definiert).

- [ ] **Step 3: `format_current()` implementieren**

An `src/wetter_mcp/formatting.py` anhängen:
```python
def format_current(raw: dict, label: str) -> dict:
    cur = raw.get("current") or {}
    return {
        "ort": label,
        "zeit": cur.get("time"),
        "temperatur_c": cur.get("temperature_2m"),
        "gefuehlt_c": cur.get("apparent_temperature"),
        "luftfeuchte_pct": cur.get("relative_humidity_2m"),
        "niederschlag_mm": cur.get("precipitation"),
        "bewoelkung_pct": cur.get("cloud_cover"),
        "wind_kmh": cur.get("wind_speed_10m"),
        "wetter": describe_code(cur.get("weather_code")),
    }
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: format_current()"
```

---

### Task 7: `format_hourly()`

**Files:**
- Modify: `src/wetter_mcp/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Failing test anhängen**

An `tests/test_formatting.py` anhängen:
```python
def test_format_hourly_limits_to_hours():
    raw = {
        "hourly": {
            "time": ["2026-07-11T18:00", "2026-07-11T19:00", "2026-07-11T20:00"],
            "temperature_2m": [21.0, 20.0, 19.0],
            "precipitation": [0.0, 0.5, 1.2],
            "precipitation_probability": [10, 40, 80],
            "wind_speed_10m": [9.0, 8.0, 7.0],
            "weather_code": [2, 61, 63],
        }
    }
    out = formatting.format_hourly(raw, "Steinenbronn", hours=2)
    assert out["ort"] == "Steinenbronn"
    assert len(out["stunden"]) == 2
    assert out["stunden"][0] == {
        "zeit": "2026-07-11T18:00",
        "temperatur_c": 21.0,
        "niederschlag_mm": 0.0,
        "niederschlag_prob_pct": 10,
        "wind_kmh": 9.0,
        "wetter": "teils bewölkt",
    }
    assert out["stunden"][1]["wetter"] == "leichter Regen"


def test_format_hourly_hours_exceeds_data():
    raw = {
        "hourly": {
            "time": ["2026-07-11T18:00"],
            "temperature_2m": [21.0],
            "precipitation": [0.0],
            "precipitation_probability": [10],
            "wind_speed_10m": [9.0],
            "weather_code": [2],
        }
    }
    out = formatting.format_hourly(raw, "X", hours=24)
    assert len(out["stunden"]) == 1
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_formatting.py -k format_hourly -v`
Expected: FAIL (`format_hourly` nicht definiert).

- [ ] **Step 3: `format_hourly()` implementieren**

An `src/wetter_mcp/formatting.py` anhängen:
```python
def format_hourly(raw: dict, label: str, hours: int) -> dict:
    h = raw.get("hourly") or {}
    times = h.get("time") or []
    stunden = []
    for i in range(min(hours, len(times))):
        stunden.append(
            {
                "zeit": times[i],
                "temperatur_c": _at(h, "temperature_2m", i),
                "niederschlag_mm": _at(h, "precipitation", i),
                "niederschlag_prob_pct": _at(h, "precipitation_probability", i),
                "wind_kmh": _at(h, "wind_speed_10m", i),
                "wetter": describe_code(_at(h, "weather_code", i)),
            }
        )
    return {"ort": label, "stunden": stunden}
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: format_hourly()"
```

---

### Task 8: `format_daily()`

**Files:**
- Modify: `src/wetter_mcp/formatting.py`
- Test: `tests/test_formatting.py`

- [ ] **Step 1: Failing test anhängen**

An `tests/test_formatting.py` anhängen (Sonnenstunden: Sekunden → Stunden):
```python
def test_format_daily():
    raw = {
        "daily": {
            "time": ["2026-07-11", "2026-07-12"],
            "temperature_2m_max": [24.0, 22.0],
            "temperature_2m_min": [13.0, 12.0],
            "precipitation_sum": [0.0, 3.4],
            "precipitation_probability_max": [5, 60],
            "sunshine_duration": [36000, 18000],
            "weather_code": [1, 63],
        }
    }
    out = formatting.format_daily(raw, "Steinenbronn", days=7)
    assert out["ort"] == "Steinenbronn"
    assert len(out["tage"]) == 2
    assert out["tage"][0] == {
        "datum": "2026-07-11",
        "min_c": 13.0,
        "max_c": 24.0,
        "niederschlag_mm": 0.0,
        "niederschlag_prob_pct": 5,
        "sonnenstunden": 10.0,
        "wetter": "überwiegend klar",
    }
    assert out["tage"][1]["sonnenstunden"] == 5.0


def test_format_daily_missing_sunshine():
    raw = {
        "daily": {
            "time": ["2026-07-11"],
            "temperature_2m_max": [24.0],
            "temperature_2m_min": [13.0],
            "precipitation_sum": [0.0],
            "precipitation_probability_max": [5],
            "weather_code": [1],
        }
    }
    out = formatting.format_daily(raw, "X", days=7)
    assert out["tage"][0]["sonnenstunden"] is None
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_formatting.py -k format_daily -v`
Expected: FAIL (`format_daily` nicht definiert).

- [ ] **Step 3: `format_daily()` implementieren**

An `src/wetter_mcp/formatting.py` anhängen:
```python
def format_daily(raw: dict, label: str, days: int) -> dict:
    d = raw.get("daily") or {}
    times = d.get("time") or []
    tage = []
    for i in range(min(days, len(times))):
        sun = _at(d, "sunshine_duration", i)
        tage.append(
            {
                "datum": times[i],
                "min_c": _at(d, "temperature_2m_min", i),
                "max_c": _at(d, "temperature_2m_max", i),
                "niederschlag_mm": _at(d, "precipitation_sum", i),
                "niederschlag_prob_pct": _at(d, "precipitation_probability_max", i),
                "sonnenstunden": round(sun / 3600, 1) if sun is not None else None,
                "wetter": describe_code(_at(d, "weather_code", i)),
            }
        )
    return {"ort": label, "tage": tage}
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_formatting.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/formatting.py tests/test_formatting.py
git commit -m "feat: format_daily()"
```

---

### Task 9: `server.py` — Ortsauflösung + Default-Ort

**Files:**
- Create: `src/wetter_mcp/server.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Failing tests schreiben**

`tests/test_tools.py`:
```python
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
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_tools.py -v`
Expected: FAIL (`wetter_mcp.server` bzw. `resolve_location` nicht vorhanden).

- [ ] **Step 3: `server.py` mit FastMCP-Instanz + `resolve_location()` anlegen**

`src/wetter_mcp/server.py`:
```python
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
```

- [ ] **Step 4: Test ausführen (grün)**

Run: `uv run pytest tests/test_tools.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/server.py tests/test_tools.py
git commit -m "feat: server.py — Ortsauflösung + Default-Ort Steinenbronn"
```

---

### Task 10: Die 3 Tools + Registrierung + `main()`

**Files:**
- Modify: `src/wetter_mcp/server.py`
- Test: `tests/test_tools.py`

- [ ] **Step 1: Failing tests anhängen**

An `tests/test_tools.py` anhängen. Die Tools werden über gemockte `resolve_location` + `fetch_forecast` getestet — geprüft werden Feldauswahl, Parameter-Kappung und dass die Formatierung greift:
```python
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
```

- [ ] **Step 2: Test ausführen (fehlschlägt)**

Run: `uv run pytest tests/test_tools.py -v`
Expected: FAIL (`get_current_weather` etc. nicht definiert).

- [ ] **Step 3: Tools, Registrierung und `main()` implementieren**

An `src/wetter_mcp/server.py` anhängen:
```python
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
```

- [ ] **Step 4: Test ausführen (grün) + volle Suite**

Run: `uv run pytest -v`
Expected: PASS (alle Tests grün: smoke 1 + weather_client 8 + formatting 8 + tools 9 = 26).

- [ ] **Step 5: Commit**

```bash
git add src/wetter_mcp/server.py tests/test_tools.py
git commit -m "feat: 3 Wetter-Tools + Registrierung + main()"
```

---

### Task 11: README + Live-Rauchtest + Inbetriebnahme

**Files:**
- Create: `README.md`
- Registrierung im Claude-MCP (User-Scope)
- Vault-Doku (im ki-os-Repo, separat committen)

- [ ] **Step 1: `README.md` schreiben**

`README.md`:
```markdown
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
```

- [ ] **Step 2: Live-Rauchtest gegen echtes Open-Meteo**

Kein Mock — prüft, dass die echten Endpoints + Feldnamen stimmen:
```bash
cd ~/workspace/wetter-mcp-server
uv run python -c "
import asyncio
from wetter_mcp import server
print(asyncio.run(server.get_current_weather()))
print(asyncio.run(server.get_hourly_forecast(hours=3)))
print(asyncio.run(server.get_daily_forecast(location='Bozen', days=2)))
"
```
Expected: drei Dicts mit plausiblen Werten; `get_current_weather` zeigt `ort: Steinenbronn`, der Bozen-Aufruf zeigt ein aufgelöstes Label (`Bozen, …, Italien`). Falls ein Feld `None` ist, das Feld gegen die Open-Meteo-Doku prüfen (Feldname evtl. abweichend).

- [ ] **Step 3: Commit README**

```bash
git add README.md
git commit -m "docs: README"
```

- [ ] **Step 4: Im Claude-MCP registrieren (User-Scope)**

Bestehende Registrierung als Vorlage ansehen:
```bash
claude mcp list
```
Dann analog registrieren (stdio, User-Scope):
```bash
claude mcp add wetter -s user -- uv run --directory /Users/jurgenschilling/workspace/wetter-mcp-server wetter-mcp
```
Verifizieren: `claude mcp list` zeigt `wetter`. In einer neuen Session prüfen, dass die drei Tools erscheinen und `get_current_weather` ein Ergebnis liefert.

- [ ] **Step 5: GitHub-Repo + Vault-Doku (im ki-os-Repo)**

- Repo auf GitHub anlegen und pushen: `gh repo create Schimmilab/wetter-mcp-server --public --source=. --push` (HTTPS + gh CLI).
- Projektnotiz im Vault anlegen: `~/ki-os/04-projects/mcp-server/wetter-mcp-server.md` (analog zu `telegram-mcp-server.md`) — Zweck, Tools, Default-Ort, Verweis aufs Repo + auf `docs/superpowers/specs/2026-07-11-wetter-mcp-server-design.md`. Mit `[dateiname](dateiname.md)`-Links.
- Eintrag in `~/ki-os/08-resources/mcp-usage-log.md` (ein Eintrag für den neuen MCP).
- In `~/ki-os/08-resources/scripts/automation/setup-mcp-servers.sh` `wetter` als bekannten Server ergänzen (Klonen + `uv sync` + User-Scope-Registrierung), damit die Einrichtung auf einem neuen Rechner reproduzierbar ist.
- ki-os-Änderungen committen (eigener Commit im ki-os-Repo).

---

## Self-Review

**Spec-Abdeckung** (gegen `docs/superpowers/specs/2026-07-11-wetter-mcp-server-design.md`):
- Open-Meteo, kein Key → Task 2–4 (kein Auth-Pfad). ✓
- 3 Tools `get_current_weather` / `get_hourly_forecast` / `get_daily_forecast` mit optionalem `location` → Task 10. ✓
- Internes Geocoding, Antwort nennt aufgelösten Ort/Land → Task 3 (`label`), sichtbar in jeder Ausgabe (`ort`). ✓
- Default-Ort Steinenbronn, Adresse nicht im Repo → Task 9 (Ortsmitte als Code-Konstante, Straßenadresse taucht nirgends auf; Env-Override optional). ✓
- Variante A (kein `overnight_window`) → Hinweis im Docstring von `get_hourly_forecast`, kein Extra-Tool. ✓
- `timezone=auto` (Ortszeit fürs Reisewetter) → Task 4. ✓
- Fehlerbehandlung: Ort nicht gefunden (Task 3), Netz/Timeout + non-200 (Task 2), Parameter-Kappung (Task 10). ✓
- Tests: Happy-Path je Tool, drei Fehlerfälle, Geocoding Default vs. explizit → Tasks 2/3/9/10. ✓
- Struktur nach tibber-Muster (fastmcp, src-Layout, respx, uv, CI) → Task 1. ✓
- Tibber-Kopplung / `overnight_window` bewusst NICHT gebaut (spätere Stufe). ✓

**Platzhalter-Scan:** keine TBD/TODO; jeder Code-Step enthält vollständigen Code; jeder Run-Step nennt Befehl + erwartetes Ergebnis. ✓

**Typ-Konsistenz:** `geocode()` liefert `{lat,lon,label}` (Task 3) → `resolve_location()` liest genau diese Keys (Task 9). `fetch_forecast(lat, lon, *, current/hourly/daily/forecast_hours/forecast_days)` (Task 4) → von den Tools mit exakt diesen Kwargs aufgerufen (Task 10). `format_current/hourly/daily(raw, label[, n])` (Tasks 6–8) → Tool-Rückgaben nutzen dieselben Signaturen (Task 10). Konstanten `CURRENT_FIELDS/HOURLY_FIELDS/DAILY_FIELDS` in Task 9 definiert, in Task 10 verwendet. ✓
```
