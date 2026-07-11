from wetter_mcp import formatting


def test_describe_code_known():
    assert formatting.describe_code(0) == "klar"
    assert formatting.describe_code(61) == "leichter Regen"
    assert formatting.describe_code(95) == "Gewitter"


def test_describe_code_none():
    assert formatting.describe_code(None) == "unbekannt"


def test_describe_code_unknown_number():
    assert formatting.describe_code(4242) == "Wettercode 4242"
