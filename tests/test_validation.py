# ============================================================
# Griffin Library - Query Validation Tests
# ============================================================
# Run: pytest tests/test_validation.py -v

import pytest
from core.validation import is_meaningful_query


# ─────────────────────────────────────────────────────────────
# Valid queries - must all pass
# ─────────────────────────────────────────────────────────────
VALID_QUERIES = [
    "a gripping mystery set in Japan",
    "something heartwarming and cozy",
    "dystopian science fiction",
    "philosophy of mind",
    "war and peace",
    "the great gatsby",
    # Edge cases with valid consonant clusters:
    "a book about strengths and resilience",
    "books on rhythms of nature",
    "psychology",
    "love",
    "epic fantasy with dragons",
    "books that explore grief and healing",
    "classic literature 19th century",
    "1984 by orwell",
    "books like dune",
]


# ─────────────────────────────────────────────────────────────
# Invalid queries - must all fail with the expected reason
# ─────────────────────────────────────────────────────────────
INVALID_QUERIES = [
    ("",            "too_short"),
    ("a",           "too_short"),
    ("ab",          "too_short"),
    ("123",         "numbers_only"),
    ("123 456",     "numbers_only"),
    ("...",         "low_alpha"),       # non-alpha symbols
    ("!!!!",        "low_alpha"),
    ("aaaaaaa",     "repetition"),
    ("hellooooo",   "repetition"),
    ("xkcdfjk",     "keyboard_mash"),
    ("zxcvbn",      "keyboard_mash"),
    ("asdf jkl ghj","keyboard_mash"),
    ("qwrt pdfn",   "keyboard_mash"),
]


@pytest.mark.parametrize("query", VALID_QUERIES)
def test_valid_queries_pass(query):
    valid, reason = is_meaningful_query(query)
    assert valid, f"'{query}' should be valid but got: {reason}"


@pytest.mark.parametrize("query,expected_reason", INVALID_QUERIES)
def test_invalid_queries_fail(query, expected_reason):
    valid, reason = is_meaningful_query(query)
    assert not valid, f"'{query}' should be invalid"
    assert reason == expected_reason, (
        f"'{query}' expected reason '{expected_reason}' but got '{reason}'"
    )


def test_strengths_specifically():
    """Regression test for the regex bug where 'strengths' was rejected."""
    valid, reason = is_meaningful_query("a book about strengths")
    assert valid, f"Got reason: {reason}"


def test_rhythms_specifically():
    """Regression test: words with consonant clusters but valid vowels."""
    valid, _ = is_meaningful_query("books on rhythms")
    assert valid


def test_short_common_words():
    valid, _ = is_meaningful_query("go on a journey")
    assert valid


def test_whitespace_handling():
    valid, _ = is_meaningful_query("   classic literature   ")
    assert valid


def test_unicode_query():
    # Non-Latin scripts should not crash even if heuristics flag them
    result = is_meaningful_query("روايات خيال علمي")
    # Either valid or returns a stable reason - just shouldn't crash
    assert isinstance(result, tuple)
    assert len(result) == 2
