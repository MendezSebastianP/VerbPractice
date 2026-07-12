from app.services.conjugation_engine import accepted_conjugation_forms, conjugation_answer_is_correct


def test_russian_gender_alternatives_are_accepted_individually():
    expected = "знал (знала, знало)"

    assert accepted_conjugation_forms(expected, "RU") == {
        expected,
        "знал",
        "знала",
        "знало",
    }
    assert conjugation_answer_is_correct("знала", expected, "RU") is True


def test_french_optional_agreement_suffixes_expand_to_real_forms():
    expected = "êtes descendu(e)(s)"

    assert {"êtes descendu", "êtes descendue", "êtes descendus", "êtes descendues"}.issubset(
        accepted_conjugation_forms(expected, "FR")
    )
    assert conjugation_answer_is_correct("êtes descendues", expected, "FR") is True


def test_usage_annotations_are_not_required_in_an_answer():
    assert conjugation_answer_is_correct("lanzo", "lanzo (coloquial)", "ES") is True
    assert conjugation_answer_is_correct("coloquial", "lanzo (coloquial)", "ES") is False
