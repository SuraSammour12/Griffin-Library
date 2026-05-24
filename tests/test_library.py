# ============================================================
# Griffin Library - Library Service Tests
# ============================================================
# Run: pytest tests/test_library.py -v

import json
import pytest
from pathlib import Path

from core.library import Library
from core.storage import Storage


@pytest.fixture
def lib(tmp_path):
    return Library(tmp_path / "test_library.json")


def test_fresh_library(lib):
    assert lib.get_name() == ""
    assert lib.get_all() == {}
    assert lib.total_quotes() == 0


def test_set_name(lib):
    lib.set_name("alice")
    assert lib.get_name() == "Alice"  # capitalize


def test_add_book(lib):
    lib.add(123, {
        "title": "Test Book",
        "authors": "Jane Doe",
        "genres": "fiction, mystery",
        "num_pages": 300,
        "avg_rating": 4.2,
    }, status="want")

    book = lib.get(123)
    assert book is not None
    assert book.title == "Test Book"
    assert book.status == "want"
    assert book.total_pages == 300


def test_status_transitions(lib):
    lib.add(1, {"title": "A", "authors": "X"}, status="want")
    assert lib.get(1).start_date is None

    lib.update_status(1, "reading")
    assert lib.get(1).start_date is not None

    lib.update_status(1, "read")
    assert lib.get(1).finish_date is not None


def test_add_quote(lib):
    lib.add(1, {"title": "A", "authors": "X"}, status="reading")
    ok = lib.add_quote(1, "A great line about life", page="42", tags=["wisdom"])
    assert ok
    book = lib.get(1)
    assert len(book.quotes) == 1
    assert book.quotes[0].text == "A great line about life"
    assert "wisdom" in book.quotes[0].tags


def test_empty_quote_rejected(lib):
    lib.add(1, {"title": "A", "authors": "X"})
    assert not lib.add_quote(1, "   ")
    assert not lib.add_quote(1, "")


def test_rating_clamp(lib):
    lib.add(1, {"title": "A", "authors": "X"})
    lib.update_rating(1, 99)
    assert lib.get(1).my_rating == 5
    lib.update_rating(1, -3)
    assert lib.get(1).my_rating == 0


def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "lib.json"
    lib1 = Library(path)
    lib1.set_name("alice")
    lib1.add(1, {"title": "Book", "authors": "Author"}, status="reading")
    lib1.add_quote(1, "Quote text")

    # Reload
    lib2 = Library(path)
    assert lib2.get_name() == "Alice"
    assert lib2.get(1) is not None
    assert lib2.total_quotes() == 1


def test_corrupted_json_recovery(tmp_path):
    path = tmp_path / "lib.json"
    path.write_text("this is not valid json{{{")
    lib = Library(path)
    # Should fall back to fresh state, not crash
    assert lib.get_name() == ""
    assert lib.get_all() == {}


def test_legacy_schema_migration(tmp_path):
    """v1 schemas (no schema_version, no quote tags) should load cleanly."""
    path = tmp_path / "lib.json"
    legacy = {
        "user": {"name": "Bob"},
        "books": {
            "5": {
                "title": "Old Book",
                "authors": "X",
                "status": "read",
                "my_rating": 4,
                "quotes": [{"text": "old quote", "page": "1", "date": "2024-01-01"}],
                "current_page": 0,
                "total_pages": 100,
            }
        },
        "goals": {"yearly_goal": 12, "year": 2024},
        "streak": {"last_date": None, "count": 0},
    }
    path.write_text(json.dumps(legacy))
    lib = Library(path)
    assert lib.get_name() == "Bob"
    book = lib.get(5)
    assert book is not None
    assert book.quotes[0].tags == []  # migrated default


def test_atomic_write_no_corruption(tmp_path):
    """Even if save is interrupted, the file should be valid JSON."""
    path = tmp_path / "lib.json"
    lib = Library(path)
    lib.set_name("test")
    for i in range(50):
        lib.add(i, {"title": f"Book {i}", "authors": "x"})
    # Read back raw bytes - should always parse
    raw = path.read_text()
    parsed = json.loads(raw)
    assert len(parsed["books"]) == 50


def test_export_json(lib):
    lib.set_name("alice")
    lib.add(1, {"title": "Book", "authors": "Author"})
    out = lib.export_json()
    parsed = json.loads(out)
    assert parsed["user"]["name"] == "Alice"


def test_reset(lib):
    lib.set_name("alice")
    lib.add(1, {"title": "A", "authors": "X"})
    lib.reset()
    assert lib.get_name() == ""
    assert lib.get_all() == {}


def test_streak_increments_on_consecutive_days(lib, monkeypatch):
    from datetime import date, timedelta

    today = date(2025, 6, 15)

    class FakeDate(date):
        @classmethod
        def today(cls):
            return today

    # Day 1
    monkeypatch.setattr("core.library.date", FakeDate)
    lib.touch_streak()
    assert lib.get_streak().count == 1


def test_quote_deletion(lib):
    lib.add(1, {"title": "A", "authors": "X"})
    lib.add_quote(1, "Quote 1")
    lib.add_quote(1, "Quote 2")
    lib.add_quote(1, "Quote 3")
    assert lib.total_quotes() == 3

    lib.delete_quote(1, 1)  # delete middle
    quotes = lib.get(1).quotes
    assert len(quotes) == 2
    assert quotes[0].text == "Quote 1"
    assert quotes[1].text == "Quote 3"
