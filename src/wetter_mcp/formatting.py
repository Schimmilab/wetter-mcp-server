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
    """WMO-Wettercode → deutsche Beschreibung; None/unbekannt sauber abgefangen."""
    if code is None:
        return "unbekannt"
    return WEATHER_CODES.get(code, f"Wettercode {code}")


def _at(block: dict, key: str, i: int):
    """Wert an Index i aus einem Open-Meteo-Array-Block, None wenn nicht vorhanden."""
    arr = block.get(key)
    if not arr or i >= len(arr):
        return None
    return arr[i]


def format_current(raw: dict, label: str) -> dict:
    """Aktueller-Wetter-Block → kompaktes Dict mit benannten Feldern + Ort."""
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


def format_hourly(raw: dict, label: str, hours: int) -> dict:
    """Stündlicher Block → bis zu `hours` Stunden-Dicts + Ort."""
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


def format_daily(raw: dict, label: str, days: int) -> dict:
    """Täglicher Block → bis zu `days` Tages-Dicts + Ort (Sonne in Stunden)."""
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
