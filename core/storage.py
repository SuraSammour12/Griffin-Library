# ============================================================
# Griffin Library - Storage Layer
# ============================================================
# Atomic JSON writes, automatic daily backups (max 7),
# schema migration from legacy versions, and salvage recovery.
# ============================================================

import json
import os
import shutil
import tempfile
import threading
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .schemas import LibraryData

logger = logging.getLogger(__name__)


class Storage:
    MAX_BACKUPS = 7

    def __init__(self, path: Path):
        self.path = Path(path)
        self.backup_dir = self.path.parent / "backups"
        self._lock = threading.RLock()

    # ── Load ──────────────────────────────────────────────────
    def load(self) -> LibraryData:
        with self._lock:
            if not self.path.exists():
                logger.info("No library file found, creating fresh.")
                return LibraryData()

            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to parse library file: %s", e)
                recovered = self._try_recover_from_backup()
                if recovered is not None:
                    return recovered
                return LibraryData()

            raw = self._migrate(raw)

            try:
                return LibraryData.model_validate(raw)
            except Exception as e:
                logger.error("Schema validation failed: %s", e)
                return self._salvage(raw)

    # ── Save ──────────────────────────────────────────────────
    def save(self, data: LibraryData) -> bool:
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                payload = data.model_dump(mode="json")

                fd, tmp_path = tempfile.mkstemp(
                    dir=self.path.parent,
                    prefix=".library_",
                    suffix=".tmp",
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    os.replace(tmp_path, self.path)
                except Exception:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    raise

                self._maybe_backup()
                return True

            except Exception as e:
                logger.exception("Save failed: %s", e)
                return False

    # ── Backup management ────────────────────────────────────
    def _maybe_backup(self):
        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            today_backup = self.backup_dir / f"library_{date.today()}.json"
            if not today_backup.exists() and self.path.exists():
                shutil.copy2(self.path, today_backup)
                self._prune_backups()
        except Exception as e:
            logger.warning("Backup failed (non-fatal): %s", e)

    def _prune_backups(self):
        backups = sorted(
            self.backup_dir.glob("library_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[self.MAX_BACKUPS:]:
            try:
                old.unlink()
            except OSError:
                pass

    def _try_recover_from_backup(self) -> Optional[LibraryData]:
        if not self.backup_dir.exists():
            return None
        backups = sorted(
            self.backup_dir.glob("library_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for backup in backups:
            try:
                raw = json.loads(backup.read_text(encoding="utf-8"))
                raw = self._migrate(raw)
                logger.warning("Recovered from backup: %s", backup.name)
                return LibraryData.model_validate(raw)
            except Exception:
                continue
        return None

    # ── Schema migration ──────────────────────────────────────
    @staticmethod
    def _migrate(raw: dict) -> dict:
        """Bring legacy data forward to current schema (v5)."""
        raw.setdefault("user", {"name": ""})
        raw.setdefault("books", {})
        raw.setdefault("goals", {"yearly_goal": 12, "year": date.today().year})
        raw.setdefault("streak", {"last_date": None, "count": 0})
        raw.setdefault("schema_version", 1)
        raw.setdefault("sessions", [])

        # ── v5: persistent sessions log + reading calendar ────
        raw.setdefault("sessions_log", {})
        raw.setdefault("reading_calendar", {})

        # ─────────────────────────────────────────────────────

        # Refresh year if rolled over
        if raw["goals"].get("year") != date.today().year:
            raw["goals"]["year"] = date.today().year

        # Ensure books have all required fields
        for k, b in raw["books"].items():
            is_custom = b.get("is_custom", False) or str(k).startswith("custom_")
            if is_custom:
                b.setdefault("book_id", k)
            else:
                b.setdefault("book_id", int(k) if str(k).isdigit() else 0)
            b.setdefault("status", "want")
            b.setdefault("my_rating", 0)
            b.setdefault("quotes", [])
            b.setdefault("notes", "")
            b.setdefault("total_pages", int(b.get("num_pages", 0) or 0))
            b.setdefault("current_page", 0)
            b.setdefault("added_date", str(date.today()))
            b.setdefault("is_custom", is_custom)
            b.setdefault("custom_embedding", None)
            for q in b.get("quotes", []):
                q.setdefault("tags", [])

        # Room config
        if "room" not in raw:
            raw["room"] = {}
        room = raw["room"]

        LEGACY_DEFAULTS = {
            "mood":      "warm",
            "lamp_on":   True,
            "language":  "english",
            "onboarded": False,
        }
        for k, v in LEGACY_DEFAULTS.items():
            if k not in room:
                room[k] = v

        VALID_MOODS = ("warm", "bright", "quiet", "soft", "rainy", "night")
        if room.get("mood") not in VALID_MOODS:
            room["mood"] = "warm"

        STALE_VALUES = {
            "sofa_id": {"blush_rose"},
            "lamp_id": {"lamp_1"},
            "shelf_id": set(),
        }
        for field, stale_set in STALE_VALUES.items():
            if room.get(field) in stale_set:
                room[field] = None

        for old_key in ("shelf", "language_code"):
            room.pop(old_key, None)

        raw.setdefault("coach_plan", None)
        raw["schema_version"] = 5
        return raw

    @staticmethod
    def _salvage(raw: dict) -> LibraryData:
        """Best-effort: keep what validates, drop what doesn't."""
        clean = LibraryData()
        try:
            clean.user.name = raw.get("user", {}).get("name", "")
        except Exception:
            pass
        from .schemas import Book
        for k, b in raw.get("books", {}).items():
            try:
                clean.books[str(k)] = Book.model_validate(b)
            except Exception as e:
                logger.warning("Dropping invalid book %s: %s", k, e)
        return clean

    # ── Export / Import ──────────────────────────────────────
    def export_json(self) -> str:
        data = self.load()
        return json.dumps(data.model_dump(mode="json"), ensure_ascii=False, indent=2)

    def list_backups(self) -> list:
        if not self.backup_dir.exists():
            return []
        return sorted(
            [p.name for p in self.backup_dir.glob("library_*.json")],
            reverse=True,
        )