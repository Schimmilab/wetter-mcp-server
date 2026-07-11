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


def test_format_hourly_field_array_shorter_than_time():
    raw = {
        "hourly": {
            "time": ["2026-07-11T18:00", "2026-07-11T19:00"],
            "temperature_2m": [21.0],  # kürzer als time
            "precipitation": [0.0, 0.5],
            "precipitation_probability": [10, 40],
            "wind_speed_10m": [9.0, 8.0],
            "weather_code": [2, 61],
        }
    }
    out = formatting.format_hourly(raw, "X", hours=2)
    assert len(out["stunden"]) == 2
    assert out["stunden"][1]["temperatur_c"] is None
    assert out["stunden"][1]["niederschlag_mm"] == 0.5


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
