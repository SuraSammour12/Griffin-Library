# EverQuote core package
# Pure business logic - no UI dependencies.

from .library import Library
from .recommender import Recommender, confidence_label
from .quote_search import QuoteSearchEngine
from .schemas import LibraryData, Book, Quote, Goals, Streak
from .validation import is_meaningful_query, humanize_error
from .insights import generate_insights

__all__ = [
    "Library",
    "Recommender",
    "QuoteSearchEngine",
    "LibraryData",
    "Book",
    "Quote",
    "Goals",
    "Streak",
    "is_meaningful_query",
    "humanize_error",
    "generate_insights",
    "confidence_label",
]
