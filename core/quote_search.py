# ============================================================
# Griffin Library - Quote Search Engine
# ============================================================
# Semantic search over the user's personal quote collection.
# Embeddings are cached in-process and rebuilt incrementally.
# Supports meaning-based queries and similar-quote discovery.
# ============================================================

import logging
from typing import List, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class QuoteSearchEngine:
    """In-memory semantic search over user-saved quotes.

    Uses the same sentence-transformer the Recommender already loaded,
    so there's no extra model cost.
    """

    def __init__(self, model):
        self.model = model
        # cache: (book_id, quote_idx) -> {"emb": np.ndarray, "text": str, ...}
        self._cache: Dict[Tuple[int, int], dict] = {}
        self._cache_signature: Optional[str] = None

    # ─────────────────────────────────────────────────────────
    # Indexing
    # ─────────────────────────────────────────────────────────
    def _signature_for(self, library) -> str:
        """Cheap fingerprint of all quotes - invalidates cache when changed."""
        parts = []
        for book in library.get_all().values():
            for q in book.quotes:
                parts.append(f"{book.book_id}|{q.text[:50]}|{q.date}")
        return "::".join(parts)

    def _ensure_indexed(self, library) -> None:
        """Rebuild embeddings cache only if the quote set changed."""
        sig = self._signature_for(library)
        if sig == self._cache_signature and self._cache:
            return

        new_cache: Dict[Tuple[int, int], dict] = {}

        # Collect quotes that need encoding
        to_encode: List[Tuple[Tuple[int, int], dict]] = []
        for book in library.get_all().values():
            for idx, q in enumerate(book.quotes):
                key = (int(book.book_id), idx)
                if key in self._cache and self._cache[key]["text"] == q.text:
                    new_cache[key] = self._cache[key]
                else:
                    to_encode.append((key, {
                        "text": q.text,
                        "page": q.page,
                        "date": q.date,
                        "tags": list(q.tags),
                        "title": book.title,
                        "author": book.authors,
                        "book_id": int(book.book_id),
                        "quote_idx": idx,
                    }))

        if to_encode:
            texts = [meta["text"] for _, meta in to_encode]
            try:
                embs = self.model.encode(
                    texts, normalize_embeddings=True, show_progress_bar=False
                ).astype(np.float32)
                for (key, meta), emb in zip(to_encode, embs):
                    meta["emb"] = emb
                    new_cache[key] = meta
            except Exception:
                logger.exception("Failed encoding new quotes")

        self._cache = new_cache
        self._cache_signature = sig

    # ─────────────────────────────────────────────────────────
    # Search
    # ─────────────────────────────────────────────────────────
    def search(
        self,
        library,
        query: str,
        top_k: int = 10,
        min_score: float = 0.30,
        tag_filter: Optional[str] = None,
    ) -> List[dict]:
        """Find quotes most relevant to the query.

        Returns list of dicts with keys:
            text, page, date, tags, title, author, book_id, quote_idx, score
        """
        if not query or not query.strip():
            return []

        self._ensure_indexed(library)
        if not self._cache:
            return []

        try:
            q_emb = self.model.encode(
                [query.strip()], normalize_embeddings=True, show_progress_bar=False
            ).astype(np.float32)[0]
        except Exception:
            logger.exception("Failed encoding quote query")
            return []

        scored = []
        for key, meta in self._cache.items():
            if tag_filter and tag_filter not in meta.get("tags", []):
                continue
            sim = float(np.dot(q_emb, meta["emb"]))
            if sim >= min_score:
                scored.append({
                    "text": meta["text"],
                    "page": meta["page"],
                    "date": meta["date"],
                    "tags": meta["tags"],
                    "title": meta["title"],
                    "author": meta["author"],
                    "book_id": meta["book_id"],
                    "quote_idx": meta["quote_idx"],
                    "score": sim,
                })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # ─────────────────────────────────────────────────────────
    # Discovery: find similar quotes to a given one
    # ─────────────────────────────────────────────────────────
    def find_similar(
        self,
        library,
        book_id: int,
        quote_idx: int,
        top_k: int = 5,
    ) -> List[dict]:
        """Given an existing quote, find others in the user's library
        that resonate with it semantically."""
        self._ensure_indexed(library)
        target_key = (int(book_id), int(quote_idx))
        if target_key not in self._cache:
            return []
        target_emb = self._cache[target_key]["emb"]

        scored = []
        for key, meta in self._cache.items():
            if key == target_key:
                continue
            sim = float(np.dot(target_emb, meta["emb"]))
            scored.append({**meta, "score": sim})

        scored.sort(key=lambda x: x["score"], reverse=True)
        # Strip the embedding before returning
        return [
            {k: v for k, v in r.items() if k != "emb"}
            for r in scored[:top_k]
        ]

    def stats(self) -> dict:
        return {
            "indexed_quotes": len(self._cache),
            "cache_signature": self._cache_signature[:30] if self._cache_signature else "",
        }
