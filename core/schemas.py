# ============================================================
# Griffin Library - Data Schemas
# ============================================================
# Pydantic models for all persistent data: books, quotes,
# sessions, goals, streak, room config, and library root.
# ============================================================

from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Book(BaseModel):
    book_id: int = 0
    title: str = ""
    authors: str = ""
    genres: str = ""
    description: str = ""
    avg_rating: float = 0.0
    num_ratings: int = 0
    num_pages: int = 0
    url: str = ""
    status: str = "want"  # "want" | "reading" | "read"
    my_rating: int = 0
    notes: str = ""
    quotes: List["Quote"] = Field(default_factory=list)
    added_date: str = Field(default_factory=lambda: date.today().isoformat())
    start_date: Optional[str] = None
    finish_date: Optional[str] = None
    total_pages: int = 0
    current_page: int = 0
    is_custom: bool = False
    custom_embedding: Optional[List[float]] = None


class Quote(BaseModel):
    text: str
    page: str = ""
    tags: List[str] = Field(default_factory=list)
    date: str = Field(default_factory=lambda: date.today().isoformat())


class Goals(BaseModel):
    yearly_goal: int = 12
    year: int = Field(default_factory=lambda: date.today().year)


class Streak(BaseModel):
    last_date: Optional[str] = None
    count: int = 0


class User(BaseModel):
    name: str = ""


class ReadingSession(BaseModel):
    """A completed reading session stored persistently."""
    session_id: str
    book_id: str = ""
    book_title: str = ""
    is_free: bool = False
    date: str = Field(default_factory=lambda: date.today().isoformat())
    duration_minutes: int = 0
    pages_read: int = 0


class CalendarEntry(BaseModel):
    """A single calendar day entry."""
    type: str = "free"  # "free" | "book"
    completed: bool = False


class RoomConfig(BaseModel):
    # Mood / lighting
    mood: str = "warm"  # warm | bright | quiet | soft | rainy | night
    ambient_on: bool = True
    tablelamp_on: bool = False
    lamp_on: bool = True  # legacy compat

    # Furniture
    chair_color: str = "beige"
    cushion_color: str = "terracotta"
    cushion_pattern: str = "geometric"
    wood_color: str = "medium"
    shelf_color: str = "white"

    # Wall & Floor
    wall_color: str = "sage"
    floor_type: str = "wood"

    # Curtains
    curtain_style: str = "lace_white"

    # PNG Items
    plant_id: Optional[str] = None
    table_lamp_id: Optional[str] = None
    art_id: Optional[str] = None

    # Legacy
    shelf_id: Optional[str] = None

    # User preferences
    language: str = "english"
    onboarded: bool = False


class LibraryData(BaseModel):
    """Root document: all user data."""
    schema_version: int = 5
    user: User = Field(default_factory=User)
    books: Dict[str, Book] = Field(default_factory=dict)
    goals: Goals = Field(default_factory=Goals)
    streak: Streak = Field(default_factory=Streak)
    room: RoomConfig = Field(default_factory=RoomConfig)
    # ── NEW: persistent reading data ──────────────────────────
    sessions: List[ReadingSession] = Field(default_factory=list)
    sessions_log: Dict[str, Any] = Field(default_factory=dict)
    # keys: ISO date strings → {duration_min, pages_read, count}
    reading_calendar: Dict[str, Any] = Field(default_factory=dict)
    # keys: ISO date strings → {type: "free"|"book", completed: bool}
    coach_plan: Optional[Dict[str, Any]] = None