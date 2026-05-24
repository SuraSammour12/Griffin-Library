# ============================================================
# Griffin Library - Reusable View Components
# ============================================================
# Shared UI helpers: book cards, AI badges, genre chips,
# insight cards, and HTML escape utility.
# ============================================================

import html
import streamlit as st
from typing import List, Optional


def safe(text) -> str:
    return html.escape(str(text or ""))


def ai_match_badge(score: float, confidence: str, strong: bool = False) -> str:
    cls = "ai-match ai-match-strong" if strong else "ai-match"
    pct = int(round(score * 100))
    return (
        f'<div style="height:24px;" class="{cls}">'
        f'<span class="ai-match-dot"></span>'
        f'AI Match · {pct}% · {safe(confidence)}'
        f'</div>'
    )


def ai_score_bar(score: float) -> str:
    pct = max(0, min(100, int(round(score * 100))))
    return (
        f'<div class="ai-score-bar" style="margin-bottom:10px;">'
        f'<div class="ai-score-fill" style="width:{pct}%"></div>'
        f'</div>'
    )


def reasons_list(reasons: List[str]) -> str:
    capped = (reasons or [])[:2]
    items = "".join(f'<div class="ai-reason">{safe(r)}</div>' for r in capped)
    return f'<div style="height:52px; overflow:hidden; margin: 6px 0 10px;">{items}</div>'


def genre_chips(genres_str: str, query_concepts: Optional[List[str]] = None, limit: int = 3) -> str:
    query_concepts = [c.lower() for c in (query_concepts or [])]
    chips = []
    for g in str(genres_str).split(",")[:limit]:
        g = g.strip()
        if not g:
            continue
        cls = "genre-chip-matched" if g.lower() in query_concepts else ""
        chips.append(f'<span class="genre-chip {cls}">{safe(g)}</span>')
    return f'<div style="height:32px; overflow:hidden; margin: 4px 0;">{"".join(chips)}</div>'


def render_book_card(
    book: dict,
    in_library: bool,
    query_concepts: Optional[List[str]] = None,
    show_ai_match: bool = True,
    rank: Optional[int] = None,
) -> str:

    raw_title = book.get("title", "Unknown")
    title = safe(raw_title[:60] + ("…" if len(raw_title) > 60 else ""))

    author = safe(book.get("authors", ""))

    raw_desc = book.get("description") or ""
    desc = safe(raw_desc[:140]) + ("…" if len(raw_desc) > 140 else "")

    rating_str = f"★ {book.get('avg_rating', 0):.1f}"
    num_ratings = int(book.get("num_ratings", 0) or 0)
    pages = int(book.get("num_pages", 0) or 0)

    if show_ai_match and "semantic_score" in book:
        score = book.get("semantic_score", 0)
        conf = book.get("confidence", "Match")
        badge_html = ai_match_badge(score, conf, strong=(score >= 0.65))
        badge_html += ai_score_bar(score)
    else:
        badge_html = '<div style="height:44px;"></div>'

    chips = genre_chips(book.get("genres", ""), query_concepts)
    reasons = reasons_list(book.get("match_reasons", []))

    rank_html = ""
    if rank is not None:
        rank_html = (
            f'<div style="position:absolute; top:14px; right:14px; '
            f'background:var(--ai); color:white; width:24px; height:24px; '
            f'border-radius:50%; display:flex; align-items:center; justify-content:center; '
            f'font-size:11px; font-weight:700; box-shadow: 0 2px 8px var(--ai-glow);">'
            f'{rank}</div>'
        )

    library_badge = ""
    if in_library:
        library_badge = (
            '<div style="height:28px; display:flex; align-items:center;">'
            '<span style="background:#D1FAE5; color:#065F46; border-radius:100px; '
            'padding:3px 10px; font-size:10.5px; font-weight:600;">✓ In your library</span>'
            '</div>'
        )
    else:
        library_badge = '<div style="height:28px;"></div>'

    title_block = (
        '<div style="height:44px; overflow:hidden; '
        'font-size:15px; font-weight:700; color:var(--text); '
        'line-height:1.35; letter-spacing:-0.2px;" '
        f'class="book-card-title">{title}</div>'
    )

    author_block = (
        f'<div style="height:20px; overflow:hidden;" '
        f'class="book-card-author">{author}</div>'
    )

    desc_block = (
        f'<div style="height:80px; overflow:hidden; font-size:12.5px; '
        f'color:var(--text-muted); line-height:1.5; margin: 6px 0 8px;">'
        f'{desc}</div>'
    )

    return (
        '<div class="book-card">'
        f'{rank_html}'
        f'{badge_html}'
        f'{library_badge}'
        f'{title_block}'
        f'{author_block}'
        f'{chips}'
        f'{desc_block}'
        f'{reasons}'
        '<div class="book-card-footer">'
        f'<span>{rating_str} · {num_ratings:,} ratings</span>'
        f'<span>{pages if pages else "-"} pages</span>'
        '</div>'
        '</div>'
    )


def render_insight_card(insight: dict) -> str:
    return (
        '<div class="insight-card">'
        f'<div class="insight-card-icon">{safe(insight.get("icon", "✨"))}</div>'
        f'<div class="insight-card-title">{safe(insight.get("title", ""))}</div>'
        f'<div class="insight-card-body">{insight.get("body", "")}</div>'
        '</div>'
    )
