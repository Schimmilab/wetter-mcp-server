from wetter_mcp import formatting


def test_describe_code_known():
    assert formatting.describe_code(0) == "klar"
    assert formatting.describe_code(61) == "leichter Regen"
    assert formatting.describe_code(95) == "Gewitter"


def test_describe_code_none():
    assert formatting.describe_code(None) == "unbekannt"


def test_describe_code_unknown_number():
    assert formatting.describe_code(4242) == "Wettercode 4242"


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
