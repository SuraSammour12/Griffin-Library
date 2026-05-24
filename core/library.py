# ============================================================
# Griffin Library - Library Service
# ============================================================
# Core data layer: CRUD for books, quotes, sessions, goals,
# streak, calendar, room config, and coach plan.
# ============================================================
import logging, uuid as _uuid_mod
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

from .schemas import LibraryData, Book, Quote, Goals, Streak, User, RoomConfig, ReadingSession
from .storage import Storage

logger = logging.getLogger(__name__)


class Library:
    def __init__(self, data_path: Path, tz: str = "UTC"):
        self.storage = Storage(data_path)
        self._data: LibraryData = self.storage.load()
        try:    self.tz = ZoneInfo(tz)
        except: self.tz = ZoneInfo("UTC")

    def _commit(self):   return self.storage.save(self._data)
    def _today(self) -> date:       return datetime.now(self.tz).date()
    def _now(self)  -> datetime:    return datetime.now(self.tz)

    # ── User ─────────────────────────────────────────────────
    def get_name(self) -> str: return self._data.user.name
    def set_name(self, name: str):
        self._data.user.name = name.strip().capitalize()
        self._commit()

    # ── Books CRUD ───────────────────────────────────────────
    def add(self, book_id, book_data: dict, status: str = "want"):
        today = str(self._today()); key = str(book_id)
        if key not in self._data.books:
            catalog_pages = int(book_data.get("num_pages", 0) or 0)
            try:    bid_int = int(book_id)
            except: bid_int = 0
            book = Book(
                book_id=bid_int, title=str(book_data.get("title","")),
                authors=str(book_data.get("authors","")), genres=str(book_data.get("genres","")),
                description=str(book_data.get("description","")),
                avg_rating=float(book_data.get("avg_rating",0) or 0),
                num_ratings=int(book_data.get("num_ratings",0) or 0),
                num_pages=catalog_pages, url=str(book_data.get("url","")),
                status=status, total_pages=catalog_pages,
                start_date=today if status=="reading" else None,
                finish_date=today if status=="read" else None,
                added_date=today, is_custom=bool(book_data.get("is_custom",False)),
                custom_embedding=book_data.get("_embedding"),
            )
            self._data.books[key] = book
        else:
            b = self._data.books[key]; b.status = status
            if status=="reading" and not b.start_date:  b.start_date  = today
            if status=="read"    and not b.finish_date: b.finish_date = today
        self._commit()

    def get(self, book_id) -> Optional[Book]: return self._data.books.get(str(book_id))
    def get_all(self) -> Dict[str, Book]:     return self._data.books
    def get_by_status(self, status: str) -> List[Book]:
        return [b for b in self._data.books.values() if b.status == status]

    def update_status(self, book_id, status: str):
        key = str(book_id)
        if key not in self._data.books: return
        today = str(self._today()); b = self._data.books[key]; b.status = status
        if status=="reading" and not b.start_date:  b.start_date  = today
        if status=="read"    and not b.finish_date: b.finish_date = today
        self._commit()

    def update_rating(self, book_id, rating: int):
        key = str(book_id)
        if key in self._data.books:
            self._data.books[key].my_rating = max(0, min(5, int(rating))); self._commit()

    def update_pages(self, book_id, total: int, current: int):
        key = str(book_id)
        if key in self._data.books:
            self._data.books[key].total_pages  = max(0, int(total))
            self._data.books[key].current_page = max(0, int(current))
            self._commit(); self.touch_streak()

    def update_notes(self, book_id, notes: str):
        key = str(book_id)
        if key in self._data.books:
            self._data.books[key].notes = notes; self._commit()

    def add_quote(self, book_id, text: str, page: str="", tags: Optional[List[str]]=None) -> bool:
        key = str(book_id)
        if key not in self._data.books or not text.strip(): return False
        q = Quote(text=text.strip(), page=page.strip(), date=str(self._today()), tags=tags or [])
        self._data.books[key].quotes.append(q); self._commit(); self.touch_streak(); return True

    def delete_quote(self, book_id, index: int):
        key = str(book_id)
        if key in self._data.books:
            qs = self._data.books[key].quotes
            if 0 <= index < len(qs): qs.pop(index); self._commit()

    def update_quote_tags(self, book_id, index: int, tags: List[str]):
        key = str(book_id)
        if key in self._data.books:
            qs = self._data.books[key].quotes
            if 0 <= index < len(qs):
                qs[index].tags = [t.strip() for t in tags if t.strip()]; self._commit()

    def delete(self, book_id):
        key = str(book_id)
        if key in self._data.books: del self._data.books[key]; self._commit()

    # ── Goals / Streak ───────────────────────────────────────
    def get_goals(self) -> Goals: return self._data.goals
    def set_goal(self, goal: int):
        self._data.goals = Goals(yearly_goal=int(goal), year=self._today().year); self._commit()

    def get_streak(self) -> Streak: return self._data.streak
    def touch_streak(self):
        today_s = str(self._today()); s = self._data.streak
        if s.last_date == today_s: return
        yesterday = str(self._today() - timedelta(days=1))
        s.count = (s.count + 1) if s.last_date == yesterday else 1
        s.last_date = today_s; self._commit()

    # Sessions log structure per day:
    # {
    #   "2026-05-21": {
    #     "total_min": 45, "total_pages": 20, "count": 2,
    #     "entries": [
    #       {"id","time","duration_min","type","book_id","book_title",
    #        "pages_read","start_page","end_page","note"}
    #     ]
    #   }
    # }
    # Legacy entries {duration_min,pages_read,count} are migrated automatically.

    def _migrate_log_entry(self, entry: dict) -> dict:
        """Migrate a legacy session entry to the current structure."""
        if "entries" in entry: return entry
        old_id = str(_uuid_mod.uuid4())[:8]
        return {
            "total_min":   entry.get("duration_min", 0),
            "total_pages": entry.get("pages_read",   0),
            "count":       entry.get("count",        1),
            "entries": [{
                "id":           old_id,
                "time":         "00:00",
                "duration_min": entry.get("duration_min", 0),
                "type":         "free",
                "book_id":      "",
                "book_title":   "",
                "pages_read":   entry.get("pages_read", 0),
                "start_page":   0,
                "end_page":     0,
                "note":         "",
            }],
        }

    def get_sessions_log(self) -> Dict[str, Any]:
        """Return the full sessions log, migrating any legacy entries."""
        raw = self._data.sessions_log or {}
        migrated = {}
        changed  = False
        for k, v in raw.items():
            m = self._migrate_log_entry(v)
            migrated[k] = m
            if m is not v: changed = True
        if changed:
            self._data.sessions_log = migrated
            self._commit()
        return migrated

    def update_sessions_log(self, date_str: str, duration_min: int,
                             pages_read: int = 0,
                             session_type: str = "free",
                             book_id: str = "",
                             book_title: str = "",
                             start_page: int = 0,
                             end_page: int = 0,
                             time_str: str = "") -> str:
        """Add a new session entry for the given day. Returns session_id."""
        if not self._data.sessions_log:
            self._data.sessions_log = {}

        raw = self._data.sessions_log.get(date_str, {})
        day = self._migrate_log_entry(raw) if raw else {
            "total_min": 0, "total_pages": 0, "count": 0, "entries": []
        }

        sid = str(_uuid_mod.uuid4())[:8]
        entry = {
            "id":           sid,
            "time":         time_str or self._now().strftime("%H:%M"),
            "duration_min": max(1, int(duration_min)),
            "type":         session_type,  # "free" | "book"
            "book_id":      str(book_id),
            "book_title":   str(book_title),
            "pages_read":   max(0, int(pages_read)),
            "start_page":   max(0, int(start_page)),
            "end_page":     max(0, int(end_page)),
            "note":         "",
        }
        day["entries"].append(entry)
        day["total_min"]   = sum(e["duration_min"] for e in day["entries"])
        day["total_pages"] = sum(e["pages_read"]   for e in day["entries"])
        day["count"]       = len(day["entries"])

        self._data.sessions_log[date_str] = day
        self._commit()
        return sid

    def update_session_note(self, date_str: str, session_id: str, note: str) -> bool:
        """Add or update a note on a specific session entry."""
        log = self._data.sessions_log or {}
        if date_str not in log: return False
        day = self._migrate_log_entry(log[date_str])
        for e in day["entries"]:
            if e["id"] == session_id:
                e["note"] = note.strip()
                self._data.sessions_log[date_str] = day
                self._commit()
                return True
        return False

    def delete_session_entry(self, date_str: str, session_id: str) -> bool:
        """Delete a single session entry from the given day."""
        log = self._data.sessions_log or {}
        if date_str not in log: return False
        day = self._migrate_log_entry(log[date_str])
        before = len(day["entries"])
        day["entries"] = [e for e in day["entries"] if e["id"] != session_id]
        if len(day["entries"]) == before: return False
        if not day["entries"]:
            del self._data.sessions_log[date_str]
        else:
            day["total_min"]   = sum(e["duration_min"] for e in day["entries"])
            day["total_pages"] = sum(e["pages_read"]   for e in day["entries"])
            day["count"]       = len(day["entries"])
            self._data.sessions_log[date_str] = day
        self._commit()
        return True

    def get_all_session_entries(self) -> List[dict]:
        """Return all sessions sorted newest first for display."""
        log     = self.get_sessions_log()
        entries = []
        for date_str, day in log.items():
            for e in day.get("entries", []):
                entries.append({**e, "date": date_str})
        entries.sort(key=lambda x: (x["date"], x["time"]), reverse=True)
        return entries

    # ── Reading Calendar ──────────────────────────────────────
    def _migrate_entry(self, entry: dict) -> dict:
        if "sessions" in entry: return entry
        import uuid
        return {"sessions": [{
            "id": str(uuid.uuid4())[:8],
            "type": entry.get("type","free"), "time": entry.get("time",""),
            "label": "", "completed": entry.get("completed", False),
        }]}

    def _get_cal(self) -> Dict[str, Any]:
        cal = self._data.reading_calendar or {}
        changed = False; result = {}
        for k, v in cal.items():
            m = self._migrate_entry(v); result[k] = m
            if m is not v: changed = True
        if changed: self._data.reading_calendar = result
        return result

    def get_reading_calendar(self) -> Dict[str, Any]:
        return self._get_cal()

    def get_upcoming_calendar(self) -> Dict[str, Any]:
        """Return calendar entries for today and future dates."""
        now_str = self._now().isoformat()[:16]
        today   = self._today().isoformat()
        cal     = self._get_cal()
        result  = {}
        for date_str, entry in cal.items():
            if date_str < today: continue
            if date_str == today:
                pending = []
                for s in entry.get("sessions", []):
                    t = s.get("time","")
                    if not t or f"{today}T{t}" >= now_str:
                        pending.append(s)
                if pending: result[date_str] = {"sessions": pending}
            else:
                result[date_str] = entry
        return result

    def get_missed_sessions(self) -> List[dict]:
        now_str = self._now().isoformat()[:16]
        today   = self._today().isoformat()
        missed  = []
        for date_str, entry in self._get_cal().items():
            for s in entry.get("sessions", []):
                if s.get("completed"): continue
                t  = s.get("time","")
                dt = f"{date_str}T{t}" if t else f"{date_str}T00:00"
                if dt < now_str:
                    missed.append({"date": date_str, "session_id": s.get("id",""),
                                   "type": s.get("type","free"), "time": t,
                                   "label": s.get("label","")})
        return missed

    def add_calendar_session(self, date_str: str, session_type: str,
                              time_str: str="", label: str="") -> str:
        """Add a calendar session with conflict and past-time checks."""
        import uuid
        now_str = self._now().isoformat()[:16]
        today   = self._today().isoformat()

        if date_str < today:
            return ""

        if date_str == today and time_str:
            session_dt = f"{today}T{time_str[:5]}"
            if session_dt < now_str:
                return "past_time"

        if not self._data.reading_calendar: self._data.reading_calendar = {}
        entry = self._data.reading_calendar.get(date_str, {"sessions":[]})
        entry = self._migrate_entry(entry)

        if time_str:
            for s in entry["sessions"]:
                if s.get("time","")[:5] == time_str[:5]: return "conflict"

        sid = str(uuid.uuid4())[:8]
        entry["sessions"].append({"id":sid,"type":session_type,
                                   "time":time_str[:5] if time_str else "",
                                   "label":label,"completed":False})
        self._data.reading_calendar[date_str] = entry
        self._commit(); return sid

    def remove_calendar_session(self, date_str: str, session_id: str):
        cal = self._data.reading_calendar or {}
        if date_str not in cal: return
        entry = self._migrate_entry(cal[date_str])
        entry["sessions"] = [s for s in entry["sessions"] if s.get("id") != session_id]
        if not entry["sessions"]: del self._data.reading_calendar[date_str]
        else: self._data.reading_calendar[date_str] = entry
        self._commit()

    def remove_calendar_entry(self, date_str: str):
        if self._data.reading_calendar and date_str in self._data.reading_calendar:
            del self._data.reading_calendar[date_str]; self._commit()

    def mark_calendar_completed(self, date_str: str):
        cal = self._data.reading_calendar or {}
        if date_str not in cal: return
        entry = self._migrate_entry(cal[date_str])
        for s in entry["sessions"]:
            if not s.get("completed"): s["completed"] = True; break
        self._data.reading_calendar[date_str] = entry; self._commit()

    def get_calendar_stats(self) -> dict:
        today = self._today().isoformat(); now_str = self._now().isoformat()[:16]
        planned = done = missed = 0
        for date_str, entry in self._get_cal().items():
            for s in entry.get("sessions",[]):
                planned += 1
                if s.get("completed"): done += 1
                else:
                    t  = s.get("time",""); dt = f"{date_str}T{t}" if t else f"{date_str}T00:00"
                    if dt < now_str: missed += 1
        return {"planned":planned,"completed":done,"missed":missed,
                "rate": int(done/planned*100) if planned else 0}

    # ── Room Config ───────────────────────────────────────────
    def get_room_config(self) -> RoomConfig: return self._data.room
    def set_room_config(self, config: dict) -> RoomConfig:
        known = set(RoomConfig.model_fields.keys())
        self._data.room = RoomConfig.model_validate({k:v for k,v in config.items() if k in known})
        self._commit(); return self._data.room
    def update_room_config(self, **kwargs) -> RoomConfig:
        current = self._data.room.model_dump()
        for k,v in kwargs.items():
            if k in current: current[k] = v
        self._data.room = RoomConfig.model_validate(current); self._commit(); return self._data.room
    def is_onboarded(self) -> bool: return self._data.room.onboarded

    # ── Stats ────────────────────────────────────────────────
    def books_read_this_year(self) -> int:
        year = str(self._today().year)
        return sum(1 for b in self._data.books.values()
                   if b.status=="read" and (b.finish_date or "").startswith(year))

    def total_quotes(self) -> int:
        return sum(len(b.quotes) for b in self._data.books.values())

    def all_quotes(self) -> List[dict]:
        quotes = []
        for b in self._data.books.values():
            for idx,q in enumerate(b.quotes):
                quotes.append({"book_id":b.book_id,"quote_idx":idx,"text":q.text,
                                "page":q.page,"date":q.date,"tags":q.tags,
                                "title":b.title,"author":b.authors})
        quotes.sort(key=lambda x: x["date"], reverse=True); return quotes

    def favorite_genre(self) -> str:
        genres = []
        for b in self._data.books.values():
            if b.status=="read":
                for g in str(b.genres).split(","):
                    g=g.strip()
                    if g: genres.append(g)
        return Counter(genres).most_common(1)[0][0] if genres else "N/A"

    def all_user_tags(self) -> List[str]:
        tags = set()
        for b in self._data.books.values():
            for q in b.quotes:
                for t in q.tags: tags.add(t)
        return sorted(tags)

    # ── Coach Plan ───────────────────────────────────────────
    def set_coach_plan(self, plan: Optional[dict]) -> None:
        """Persist the Oracle's reading plan. Pass None to clear it."""
        self._data.coach_plan = plan if plan else None
        self._commit()

    def get_coach_plan(self) -> Optional[dict]:
        """Return the saved coach plan, or None if not set."""
        return self._data.coach_plan

    def reset(self): self._data = LibraryData(); self._commit()
    def export_json(self) -> str: return self.storage.export_json()