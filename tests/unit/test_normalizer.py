from __future__ import annotations

from app.matching.normalizer import normalize_title


def test_normalizes_case_and_punctuation() -> None:
    assert normalize_title("Apple AirPods Pro (2nd Generation)") == normalize_title(
        "apple airpods pro 2nd generation"
    )


def test_generation_synonym_applied() -> None:
    result = normalize_title("AirPods Pro (2nd Generation)")
    assert "gen" in result
    assert "generation" not in result


def test_collapses_whitespace() -> None:
    assert normalize_title("Sony   WH-1000XM5") == normalize_title("Sony WH-1000XM5")


def test_does_not_remove_model_numbers() -> None:
    result = normalize_title("Sony WH-1000XM5 Headphones")
    assert "1000xm5" in result
