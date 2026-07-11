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
