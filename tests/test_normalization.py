from app.services.normalization import normalize_for_comparison


def test_normalize_removes_accents_and_special_chars():
    assert normalize_for_comparison("être") == "etre"
    assert normalize_for_comparison("niño") == "nino"
    assert normalize_for_comparison("façade") == "facade"
    assert normalize_for_comparison("œuvre") == "oeuvre"
