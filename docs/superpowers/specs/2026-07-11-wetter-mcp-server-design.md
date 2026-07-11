# Wetter-MCP-Server — Design

> Datum: 2026-07-11
> Status: Design (freigegeben) — bereit für Implementierungsplan
> Kontext: Teil von Schimmis MCP-Server-Flotte (~/workspace/*-mcp-server)

## Zweck

Ein lokaler MCP-Server, der Claude im KI-OS eine Wetterprognose liefert — für zwei
Kern-Anwendungsfälle:

1. **Allgemeine Prognose** — „wie wird das Wetter heute/diese Woche".
2. **Konkrete Alltagsfrage** — „kann ich die Fenster nachts offen lassen?"
   (regnet es, wie kalt wird es in den Nachtstunden).

Zusätzlich soll **beliebiger Ort** abfragbar sein (Reisewetter je Roadtrip-Station,
„wie ist das Wetter in Schweden / Südtirol"), nicht nur Zuhause.

**Bewusst NICHT in V1** (YAGNI):
- Keine amtlichen Wetterwarnungen (explizit verworfen).
- Keine Tibber-Kopplung / Strompreis-Tendenz aus PV/Wind — spätere Ausbaustufe,
  eigener Server-Consumer, nicht Teil dieses Servers.
- Kein eigenes „Fenster offen?"-Werkzeug (siehe Entscheidung unten, Variante A).

## Datenquelle: Open-Meteo

Gewählt gegen DWD (nur DE, kein Geocoding, sperriges GRIB) und OpenWeatherMap
(API-Key + Free-Tier-Limits).

**Warum Open-Meteo:**
- **Kein API-Key**, für nicht-kommerzielle Nutzung frei → Server bleibt minimal
  (kein Secret-Handling, kein Rate-Limit-Code).
- **Weltweite Abdeckung** — erfüllt die Reisewetter-Anforderung (Schweden, Südtirol).
- **Geocoding-API inklusive** (`geocoding-api.open-meteo.com`) — Ortsname → Koordinaten.
- Aggregiert je Region das beste Modell (für DE automatisch DWD-ICON).
- Endpoints: `api.open-meteo.com/v1/forecast` (current/hourly/daily),
  `geocoding-api.open-meteo.com/v1/search` (Ortsauflösung).

## Öffentliches Interface — 3 Werkzeuge

Alle mit optionalem `location`-Parameter. Leer = Zuhause (Steinenbronn, Default aus `.env`).

| Tool | Parameter | Liefert |
|---|---|---|
| `get_current_weather` | `location?` | Jetzt-Zustand: Temp, gefühlte Temp, Wind, Bewölkung, aktueller Niederschlag |
| `get_hourly_forecast` | `location?`, `hours=24` | Stündlich: Temp, Regen-mm, Regen-Wahrscheinlichkeit, Wind |
| `get_daily_forecast` | `location?`, `days=7` | Täglich: Min/Max-Temp, Regensumme, Regen-Wahrscheinlichkeit, Sonnenstunden |

**Geocoding intern:** `location` als String („Südtirol", „Marienplatz 1, München")
wird serverintern zu Koordinaten aufgelöst. Die Antwort nennt im Kopf den
**aufgelösten Ort + Land**, damit bei mehrdeutigen Namen sichtbar ist, welcher Ort
getroffen wurde. Kein separates Geocoding-Tool nach außen (YAGNI).

### Entscheidung: „Fenster nachts offen?" → Variante A (schlank)

Kein eigenes Werkzeug. Claude ruft `get_hourly_forecast` und liest Regen +
Min-Temp für die Nachtstunden selbst aus. Begründung: die Rohdaten sind ohnehin da,
Claude beantwortet die Frage daraus zuverlässig, und es spart eine Komponente mit
hartkodierter Nacht-Definition. Ein dediziertes `get_overnight_window` bleibt eine
mögliche spätere Ergänzung, falls die Abfrage im Alltag zu umständlich wird.

## Architektur

Folgt dem bestehenden MCP-Muster der Flotte (tibber/oura), damit
`setup-mcp-servers.sh` und CI ohne Sonderfall greifen.

```
~/workspace/wetter-mcp-server/
  server.py            # MCP-Entry, die 3 Tool-Definitionen
  weather_client.py    # Open-Meteo-Aufrufe (httpx async) + Geocoding
  formatting.py        # Rohdaten (JSON) → knappe, lesbare Textausgabe
  tests/               # pytest, Open-Meteo-Antworten gemockt
  .env                 # DEFAULT_LAT / DEFAULT_LON / DEFAULT_ORT — nicht ins Git
  .env.example         # dieselben Keys ohne Werte
  .github/workflows/   # CI (pytest)
  README.md
  .claude/
```

**Default-Ort (`.env`):** Koordinaten von Steinenbronn (~48.67 N, 9.14 E — beim
Bau einmalig per Geocoding verifizieren, nicht raten). `DEFAULT_ORT` als Klartext
für die Antwort-Kopfzeile. Die Adresse selbst bleibt aus dem öffentlichen Repo
(steht in `.env`, nicht `.env.example`).

## Datenfluss (ein Tool-Call)

1. `location` leer? → Default-Koordinaten aus `.env`.
   Sonst → Geocoding-Endpoint → erster Treffer → lat/lon + aufgelöster Name/Land.
2. Forecast-Endpoint mit den zum Tool passenden `current`/`hourly`/`daily`-Feldern,
   `timezone=auto` (liefert Ortszeit — wichtig fürs Reisewetter), Einheiten metrisch
   (°C, mm, km/h).
3. `formatting.py` macht aus dem JSON eine **kompakte Textantwort** — nur die
   relevanten, benannten Werte mit Ort im Kopf. Kein Roh-JSON an Claude zurück.

## Fehlerbehandlung

Die drei realen Fälle, jeweils saubere Meldung statt Crash/Stacktrace:

- **Ort nicht gefunden** (Geocoding leer) → „Ort ‚xy' nicht gefunden".
- **Open-Meteo nicht erreichbar / Timeout** → kurze Fehlermeldung.
- **Ungültige Parameter** (z.B. `days=99`) → auf erlaubtes Maximum kappen statt Fehler.

Kein API-Key → kein Auth-Fehlerpfad, kein Rate-Limit-Handling nötig.

## Tests

Open-Meteo-Antworten als Fixtures gemockt (keine echten Netz-Calls in CI):

- Je Tool ein Happy-Path.
- Die drei Fehlerfälle (Ort nicht gefunden, Endpoint-Timeout, Parameter-Kappung).
- Geocoding: Default (leerer `location`) vs. expliziter Ort — inkl. Prüfung, dass
  der aufgelöste Ortsname in der Antwort steht.

## Spätere Ausbaustufen (nicht V1, nur Notiz)

- Tibber-Kopplung: aus Wetter (PV-Ertrag Sonne, Wind) eine Strompreis-Tendenz fürs
  E-Auto-Laden ableiten — als separater Consumer beider MCPs, nicht in diesem Server.
- Optional `get_overnight_window` falls Variante A im Alltag zu umständlich wird.
