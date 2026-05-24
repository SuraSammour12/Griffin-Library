# ============================================================
# Griffin Library - AI Recommender Engine
# ============================================================
# Semantic book search with hybrid scoring (semantic + rating
# + popularity), MMR diversity re-ranking, match explanations,
# personalized taste profiles, and confidence bands.
# ============================================================

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import numpy as np
import pandas as pd

from .validation import is_meaningful_query

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Confidence bands (calibrated heuristics on cosine similarity)
# ─────────────────────────────────────────────────────────────
# These bands map raw cosine scores to user-facing confidence levels.
# Calibrated empirically on mpnet-base-v2 with the Goodreads catalog.
CONFIDENCE_BANDS = [
    (0.65, "Strong match"),
    (0.50, "Good match"),
    (0.40, "Possible match"),
    (0.00, "Weak match"),
]


def confidence_label(score: float) -> str:
    for threshold, label in CONFIDENCE_BANDS:
        if score >= threshold:
            return label
    return "Weak match"


# ─────────────────────────────────────────────────────────────
# Recommender
# ─────────────────────────────────────────────────────────────
class Recommender:
    """Semantic book recommender backed by sentence-transformers + FAISS.

    Public API:
      • search(query, ...)           -> SearchResult dict
      • recommend_for_you(library)   -> personalized list
      • explain_match(query, book)   -> why-this-book breakdown
      • all_genres()                 -> list[str]
    """

    def __init__(
        self,
        model_name: str = "all-mpnet-base-v2",
        index_path: Optional[Path] = None,
        catalog_path: Optional[Path] = None,
    ):
        from sentence_transformers import SentenceTransformer
        import faiss

        self.faiss = faiss

        base = Path(__file__).parent.parent
        self.index_path = index_path or (base / "models" / "book_index.faiss")
        self.catalog_path = catalog_path or (base / "models" / "books_cleaned.pkl")

        try:
            logger.info("Loading sentence-transformer: %s", model_name)
            self.model = SentenceTransformer(model_name)
            self.index = faiss.read_index(str(self.index_path))
            self.df = pd.read_pickle(str(self.catalog_path)).reset_index(drop=True)
            logger.info("Recommender ready (%d books indexed).", len(self.df))
        except Exception:
            logger.exception("Recommender initialization failed")
            raise

        # Pre-extract catalog vocab for explanations
        self._build_concept_index()

    # ─────────────────────────────────────────────────────────
    # Concept index (used for "Why this book" explanations)
    # ─────────────────────────────────────────────────────────
    def _build_concept_index(self):
        """Build a flat list of (genre/theme) tokens for fast intersection."""
        self._book_genres = []
        for _, row in self.df.iterrows():
            tokens = set()
            for g in str(row.get("genres", "")).split(","):
                g = g.strip().lower()
                if g:
                    tokens.add(g)
            self._book_genres.append(tokens)

    # ─────────────────────────────────────────────────────────
    # Encoding helper
    # ─────────────────────────────────────────────────────────
    def _encode(self, text: str) -> np.ndarray:
        return self.model.encode([text], normalize_embeddings=True).astype(np.float32)

    # ─────────────────────────────────────────────────────────
    # Main search
    # ─────────────────────────────────────────────────────────
    def search(
        self,
        query: str,
        genre_filter: Optional[str] = None,
        min_rating: float = 0.0,
        sort_by: str = "relevance",
        rating_weight: float = 0.25,
        popularity_weight: float = 0.10,
        max_results: int = 30,
        min_semantic_score: float = 0.38,
        diversify: bool = True,
        diversity_lambda: float = 0.75,
    ) -> dict:
        """Hybrid semantic search.

        Returns:
            {
                "ok": bool,
                "error": Optional[str],   # reason code
                "results": [ {...book + scores}, ... ],
                "query_concepts": [str, ...],
            }
        """
        try:
            if not query or not query.strip():
                return self._empty("empty_query")
            query = query.strip()

            valid, reason = is_meaningful_query(query)
            if not valid:
                return self._empty(reason)

            query_vec = self._encode(query)
            query_concepts = self._extract_concepts(query)

            # FAISS retrieval - pull a generous candidate pool
            k = min(len(self.df), 300)
            scores, indices = self.index.search(query_vec, k)
            scores, indices = scores[0], indices[0]

            if len(scores) == 0 or float(scores[0]) < 0.35:
                return {
                    "ok": True, "error": "no_match",
                    "results": [], "query_concepts": query_concepts,
                }

            # Build candidate list with hybrid scoring
            candidates = []
            for score, idx in zip(scores, indices):
                if idx == -1 or idx >= len(self.df):
                    continue
                if float(score) < min_semantic_score:
                    break

                row = self.df.iloc[idx]

                if genre_filter and genre_filter.lower() not in str(row.get("genres", "")).lower():
                    continue
                if float(row.get("avg_rating", 0)) < min_rating:
                    continue

                semantic = float(score)
                rating_norm = float(row.get("rating_norm", row.get("avg_rating", 0) / 5.0))
                pop_norm = float(row.get("popularity_norm", 0))

                hybrid = (
                    semantic * (1 - rating_weight - popularity_weight)
                    + rating_norm * rating_weight
                    + pop_norm * popularity_weight
                )

                candidates.append({
                    "_idx": int(idx),
                    "book_id": int(row["book_id"]),
                    "title": str(row.get("title", "")),
                    "authors": str(row.get("authors", "")),
                    "genres": str(row.get("genres", "")),
                    "avg_rating": float(row.get("avg_rating", 0)),
                    "num_ratings": int(row.get("num_ratings", 0)),
                    "num_pages": int(row.get("num_pages", 0) or 0),
                    "description": str(row.get("description", "")),
                    "url": str(row.get("url", "")),
                    "semantic_score": semantic,
                    "hybrid_score": float(hybrid),
                    "confidence": confidence_label(semantic),
                })

            if not candidates:
                return {
                    "ok": True, "error": "no_match",
                    "results": [], "query_concepts": query_concepts,
                }

            # Sort
            if sort_by == "rating":
                candidates.sort(key=lambda x: x["avg_rating"], reverse=True)
            elif sort_by == "popularity":
                candidates.sort(key=lambda x: x["num_ratings"], reverse=True)
            else:
                candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

            # MMR diversity (only when sorting by relevance)
            if diversify and sort_by == "relevance" and len(candidates) > max_results:
                candidates = self._mmr_rerank(
                    candidates, query_vec[0], diversity_lambda, max_results * 2
                )

            # Attach explanations
            results = candidates[:max_results]
            for r in results:
                r["match_reasons"] = self._explain_match(query_concepts, r)
                r.pop("_idx", None)

            return {
                "ok": True,
                "error": None,
                "results": results,
                "query_concepts": query_concepts,
            }

        except Exception:
            logger.exception("Search failed")
            return self._empty("internal_error")

    # ─────────────────────────────────────────────────────────
    # MMR diversity
    # ─────────────────────────────────────────────────────────
    def _mmr_rerank(
        self,
        candidates: List[dict],
        query_vec: np.ndarray,
        lambda_param: float,
        top_k: int,
    ) -> List[dict]:
        """Maximal Marginal Relevance: balance relevance vs diversity."""
        if not candidates:
            return []

        # Reconstruct embeddings from the FAISS index for selected candidates
        idxs = [c["_idx"] for c in candidates]
        try:
            embs = np.vstack([self.index.reconstruct(i) for i in idxs])
        except Exception:
            # If reconstruct unsupported, fall back to no diversity
            logger.warning("MMR rerank skipped: index.reconstruct() unavailable, returning candidates as-is")
            return candidates

        selected = [0]  # start with top-relevance candidate
        remaining = list(range(1, len(candidates)))

        while len(selected) < top_k and remaining:
            best_score = -np.inf
            best_idx = remaining[0]

            for r in remaining:
                relevance = candidates[r]["hybrid_score"]
                max_sim = max(float(np.dot(embs[r], embs[s])) for s in selected)
                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
                if mmr > best_score:
                    best_score = mmr
                    best_idx = r

            selected.append(best_idx)
            remaining.remove(best_idx)

        return [candidates[i] for i in selected]

    # ─────────────────────────────────────────────────────────
    # Explanations: "Why this book?"
    # ─────────────────────────────────────────────────────────
    def _extract_concepts(self, query: str) -> List[str]:
        """Pull mood/theme/genre keywords from a query.

        Lightweight: matches against catalog vocabulary so we never invent
        concepts the catalog doesn't know.
        """
        q = query.lower()
        # Build vocabulary once
        if not hasattr(self, "_vocab"):
            self._vocab = set()
            for tokens in self._book_genres:
                self._vocab.update(tokens)

        concepts = []
        for term in self._vocab:
            if len(term) >= 4 and term in q:
                concepts.append(term)

        # Also check for single mood/theme keywords commonly used in queries
        mood_words = {
            "dark", "light", "happy", "sad", "funny", "serious", "romantic",
            "thrilling", "mysterious", "philosophical", "epic", "cozy",
            "gripping", "emotional", "uplifting", "dystopian", "magical",
            "historical", "literary", "fast-paced", "slow", "introspective",
            "adventure", "war", "love", "friendship", "family", "coming-of-age",
        }
        for w in mood_words:
            if w in q and w not in concepts:
                concepts.append(w)

        return concepts[:6]

    def _explain_match(self, query_concepts: List[str], book: dict) -> List[str]:
        """Return human-readable reasons this book matched the query."""
        reasons = []
        book_genres = [g.strip().lower() for g in str(book.get("genres", "")).split(",") if g.strip()]
        book_desc = str(book.get("description", "")).lower()

        # Genre/theme overlap
        overlap = [c for c in query_concepts if c in book_genres or c in book_desc]
        if overlap:
            reasons.append(f"Matches: {', '.join(overlap[:3])}")

        # Strong semantic similarity
        sem = book.get("semantic_score", 0)
        if sem >= 0.65:
            reasons.append(f"Highly aligned with your description ({int(sem*100)}%)")
        elif sem >= 0.50:
            reasons.append(f"Aligned with your description ({int(sem*100)}%)")

        # Reader signal
        if book.get("avg_rating", 0) >= 4.2 and book.get("num_ratings", 0) > 10000:
            reasons.append(f"Beloved by readers (★ {book['avg_rating']:.1f}, {book['num_ratings']:,} ratings)")
        elif book.get("avg_rating", 0) >= 4.0:
            reasons.append(f"Highly rated (★ {book['avg_rating']:.1f})")

        return reasons[:3]

    # ─────────────────────────────────────────────────────────
    # Personalized "For You" recommendations
    # ─────────────────────────────────────────────────────────
    def recommend_for_you(
        self,
        library,  # Library instance
        top_k: int = 12,
        min_rating: float = 0.0,
    ) -> dict:
        """Generate personalized recommendations from user's reading history.

        Strategy:
          1. Build user taste vector from rated books (weighted by rating).
          2. Search FAISS for nearest catalog books.
          3. Filter out books already in library.
          4. Apply MMR diversity.
          5. Attach explanations referencing source books.
        """
        try:
            taste_vec, source_books = self._build_user_profile(library)
            if taste_vec is None:
                return {
                    "ok": False, "error": "no_profile",
                    "results": [], "based_on": [],
                }

            # Single FAISS search using the clean catalog-only taste vector
            k = min(len(self.df), top_k * 8)
            scores, indices = self.index.search(taste_vec.reshape(1, -1), k)

            owned_ids    = set(int(b.book_id) for b in library.get_all().values()
                               if not getattr(b, "is_custom", False))
            owned_titles = set(b.title.lower() for b in library.get_all().values())

            candidates = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1 or idx >= len(self.df):
                    continue
                row     = self.df.iloc[idx]
                book_id = int(row["book_id"])
                if book_id in owned_ids:
                    continue
                if str(row.get("title", "")).lower() in owned_titles:
                    continue
                if float(row.get("avg_rating", 0)) < min_rating:
                    continue

                semantic = float(score)   # cosine similarity from FAISS
                hybrid   = (semantic * 0.65
                            + float(row.get("rating_norm", 0)) * 0.25
                            + float(row.get("popularity_norm", 0)) * 0.10)

                candidates.append({
                    "_idx":          int(idx),
                    "book_id":       book_id,
                    "title":         str(row.get("title", "")),
                    "authors":       str(row.get("authors", "")),
                    "genres":        str(row.get("genres", "")),
                    "avg_rating":    float(row.get("avg_rating", 0)),
                    "num_ratings":   int(row.get("num_ratings", 0)),
                    "num_pages":     int(row.get("num_pages", 0) or 0),
                    "description":   str(row.get("description", "")),
                    "url":           str(row.get("url", "")),
                    "semantic_score": semantic,
                    "hybrid_score":  hybrid,
                    "confidence":    confidence_label(semantic),
                })

            if not candidates:
                return {
                    "ok": True, "error": None,
                    "results": [], "based_on": source_books,
                }

            candidates.sort(key=lambda x: x["hybrid_score"], reverse=True)

            # MMR re-ranking: lambda_param controls relevance vs diversity
            # 0.45 = 55% relevance, 45% diversity - good balance that still
            # shows programming books when user rates programming 5★
            candidates = self._mmr_rerank(
                candidates, taste_vec, lambda_param=0.45, top_k=top_k * 2
            )

            results = candidates[:top_k]
            for r in results:
                r["match_reasons"] = self._explain_taste_match(r, source_books)
                r.pop("_idx", None)

            return {
                "ok": True,
                "error": None,
                "results": results,
                "based_on": source_books,
            }
        except Exception:
            logger.exception("recommend_for_you failed")
            return {"ok": False, "error": "internal_error", "results": [], "based_on": []}

    def _build_user_profile(self, library) -> Tuple[Optional[np.ndarray], List[dict]]:
        """Construct a taste embedding from books the user has rated/finished.

        Weights:
          • Finished books with rating: weight = rating / 5.0
          • Currently reading: weight = 0.5
          • Want to read: weight = 0.2
          • Custom books: same weights but embedding comes from stored vector
        """
        weighted = []
        sources = []

        for book in library.get_all().values():
            emb = None

            # Custom books are excluded from taste profile -
            # their embeddings come from short user descriptions
            # and don't align with FAISS catalog embeddings reliably.
            if getattr(book, "is_custom", False):
                continue

            # Catalog book: reconstruct embedding from FAISS
            try:
                book_id_int = int(book.book_id)
                row_idx = self.df.index[self.df["book_id"] == book_id_int]
                if len(row_idx) == 0:
                    continue
                idx = int(row_idx[0])
                emb = self.index.reconstruct(idx)
            except Exception:
                continue

            if emb is None:
                continue

            # Weight strategy:
            # Rating always takes priority regardless of status.
            # High ratings (4-5★) are amplified exponentially.
            # Unrated books contribute weakly as weak taste signals.
            weight = 0.0
            r = book.my_rating  # 0-5

            if r >= 4:
                # High rated - dominant signal (4★=0.8, 5★=1.0 then squared for emphasis)
                weight = (r / 5.0) ** 2  # 4★→0.64, 5★→1.0
            elif r >= 3:
                weight = r / 5.0         # 3★→0.6
            elif r >= 1:
                # Low rated (1-2★) - negative taste signal, we EXCLUDE these
                # so they don't pull the profile toward genres the user dislikes
                weight = 0.0
            else:
                # No rating - use status as weak signal
                if book.status == "read":
                    weight = 0.4   # finished but didn't rate
                elif book.status == "reading":
                    weight = 0.3
                elif book.status == "want":
                    weight = 0.1

            if weight > 0:
                weighted.append(emb * weight)
                sources.append({
                    "book_id": book.book_id,
                    "title": book.title,
                    "weight": round(weight, 3),
                    "status": book.status,
                    "rating": r,
                    "is_custom": getattr(book, "is_custom", False),
                })

        if not weighted:
            return None, []

        # Divide by sum of raw weights, not count - ensures 5★ >> two 1★ books
        raw_weights = np.array([np.linalg.norm(w) for w in weighted], dtype=np.float32)
        total_w     = raw_weights.sum() if raw_weights.sum() > 0 else 1.0
        profile     = (np.sum(weighted, axis=0) / total_w).astype(np.float32)
        norm = np.linalg.norm(profile)
        if norm > 0:
            profile = profile / norm

        # Sort sources by weight (most influential first)
        sources.sort(key=lambda x: x["weight"], reverse=True)
        return profile, sources[:5]

    def _explain_taste_match(self, book: dict, sources: List[dict]) -> List[str]:
        """Build personalized 'because you loved X' style explanations."""
        reasons = []
        if sources:
            # Show the highest-weighted source (the one the user rated highest)
            top = sources[0]
            r   = top.get("rating", 0)
            if r >= 4:
                reasons.append(f"Because you loved *{top['title']}* (★{r})")
            else:
                reasons.append(f"Because you enjoyed *{top['title']}*")
        if book.get("avg_rating", 0) >= 4.3:
            reasons.append(f"Beloved by readers (★ {book['avg_rating']:.1f})")
        sem = book.get("semantic_score", 0)
        if sem >= 0.55:
            reasons.append(f"{int(sem*100)}% match with your taste")
        return reasons[:3]

    # ─────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────
    def all_genres(self) -> List[str]:
        genres = set()
        for g in self.df["genres"].dropna():
            for item in str(g).split(","):
                item = item.strip()
                if item:
                    genres.add(item)
        return sorted(genres)

    def _empty(self, error: str) -> dict:
        return {"ok": False, "error": error, "results": [], "query_concepts": []}