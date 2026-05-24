# ============================================================
# Griffin Library - Discover (Search Hub)
# ============================================================
# Dual-mode book search: semantic AI search and classic
# search by title, author, or genre.
# ============================================================

import streamlit as st
import pandas as pd
from datetime import datetime

from core.validation import humanize_error
from .components import render_book_card, safe

_PAGE_SIZE = 6



def render(lib, rec):
    name = lib.get_name() or "friend"

    st.markdown(
        '<div class="page-title">The Scrolls</div>'
        '<div class="page-subtitle">Seek your next tome - by the soul&#39;s longing, or by the tome&#39;s true name.</div>',
        unsafe_allow_html=True,
    )

    defaults = {
        "ai_results": [], "ai_shown": _PAGE_SIZE,
        "ai_query": "", "ai_concepts": [],
        "ai_response": "", "ai_is_error": False,
        "classic_results": [], "classic_shown": _PAGE_SIZE,
        "classic_summary": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    tab_ai, tab_classic = st.tabs(["✨ AI Search", "🔎 Classic Search"])

    with tab_ai:
        _render_ai_banner(name)
        _ai_search_tab(lib, rec, name)

    with tab_classic:
        _render_classic_banner()
        _classic_search_tab(lib, rec)


# ════════════════════════════════════════════════════════════
# Banners
# ════════════════════════════════════════════════════════════
def _render_ai_banner(name):
    st.markdown("""
    <div class="page-mode-banner ai" style="margin-top:1rem; margin-bottom:1.75rem;">
        <div class="page-mode-icon">✨</div>
        <div class="page-mode-text">
            <strong>Oracle Search.</strong> Describe a feeling, theme, or longing in plain words - 
            <em>"a quiet meditation on grief"</em> or <em>"sci-fi that questions reality"</em>.
            The engine reads meaning, not keywords.
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_classic_banner():
    st.markdown("""
    <div class="page-mode-banner classic" style="margin-top:1rem; margin-bottom:1.75rem;">
        <div class="page-mode-icon">🔎</div>
        <div class="page-mode-text">
            <strong>Scroll Search.</strong> Look up a specific <strong>tome title</strong>,
            an <strong>author's name</strong>, or pick a <strong>genre</strong> from the list.
            No AI - just exact matches and filters.
        </div>
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# AI Search Tab
# ════════════════════════════════════════════════════════════
def _ai_search_tab(lib, rec, name):
    with st.form("ai_search_form"):
        query = st.text_area(
            "What are you in the mood for?",
            value=st.session_state.get("ai_query", ""),
            height=100,
            placeholder='e.g. "a slow-burn literary novel about loneliness"',
            label_visibility="collapsed",
        )

        # ── ONE simple choice instead of three competing filters ──
        col1, col2 = st.columns([2, 1])
        with col1:
            mode = st.selectbox(
                "How should I rank results?",
                options=["best_match", "best_rated", "most_popular"],
                format_func=lambda x: {
                    "best_match":    "🎯  Best match for me",
                    "best_rated":    "⭐  Finest match, highest honour",
                    "most_popular":  "🌍  Most celebrated reads",
                }[x],
                key="ai_mode",
                help=(
                    "Best match - the AI picks the closest fit to your description.\n\n"
                    "Finest match, highest honour - same, but only books rated 4★ and above.\n\n"
                    "Most celebrated - same, but the well-known books float to the top."
                ),
            )
        with col2:
            min_rating = st.slider(
                "Minimum rating",
                0.0, 5.0, 0.0, 0.5,
                key="ai_min_rating",
                help="Hide tomes below this honour, no matter how well they match.",
            )

        submitted = st.form_submit_button("🔮 Seek the Tome", use_container_width=True)

    # ── Translate user-friendly mode → engine parameters ──
    sort_by = "relevance"
    diversify = True
    effective_min_rating = min_rating

    if mode == "best_match":
        sort_by = "relevance"
        diversify = True
    elif mode == "best_rated":
        sort_by = "relevance"
        diversify = True
        effective_min_rating = max(min_rating, 4.0)  # enforce 4.0 floor
    elif mode == "most_popular":
        sort_by = "popularity"
        diversify = False  # popular books are already varied

    if submitted:
        q = query.strip()
        if not q:
            st.warning("Tell me what you're looking for.")
        else:
            with st.spinner("Searching the catalog..."):
                response = rec.search(
                    query=q,
                    sort_by=sort_by,
                    min_rating=effective_min_rating,
                    diversify=diversify,
                )

            st.session_state["ai_results"]  = response["results"]
            st.session_state["ai_concepts"] = response.get("query_concepts", [])
            st.session_state["ai_query"]    = q
            st.session_state["ai_shown"]    = _PAGE_SIZE
            st.session_state["ai_mode_used"] = mode

            if not response["ok"]:
                st.session_state["ai_is_error"] = True
                st.session_state["ai_response"] = humanize_error(response["error"], name)
            else:
                st.session_state["ai_is_error"] = len(response["results"]) == 0
                st.session_state["ai_response"] = (
                    "" if response["results"] else humanize_error("no_match", name)
                )
            st.rerun()

    if st.session_state.get("ai_response") and st.session_state.get("ai_is_error"):
        st.markdown(
            f'<div class="empty-state">{safe(st.session_state["ai_response"])}</div>',
            unsafe_allow_html=True,
        )

    results = st.session_state["ai_results"]
    if results:
        _render_ai_results_summary(
            results,
            st.session_state["ai_concepts"],
        )
        _render_results_grid(
            lib, results,
            shown=st.session_state["ai_shown"],
            prefix="ai",
            show_rank=True,
            show_ai_match=True,
            concepts=st.session_state["ai_concepts"],
        )

def _render_ai_results_summary(results, concepts):
    n = len(results)
    top_score = results[0].get("semantic_score", 0)
    top_conf  = results[0].get("confidence", "")
    top_pct = int(top_score * 100)

    # Confidence color
    if top_pct >= 70:
        conf_color = "var(--success)"
        conf_label = "Strong matches"
    elif top_pct >= 50:
        conf_color = "var(--ai)"
        conf_label = "Good matches"
    else:
        conf_color = "var(--warning)"
        conf_label = "Loose matches - try refining your description"

    concept_chips = ""
    if concepts:
        chips_html = " ".join(
            f'<span style="background:var(--ai-soft);color:var(--ai);'
            f'border:1px solid rgba(124,58,237,0.25);border-radius:100px;'
            f'padding:3px 10px;font-size:11px;font-weight:600;margin-right:4px;">'
            f'{safe(c)}</span>'
            for c in concepts[:5]
        )
        concept_chips = (
            f'<div style="margin-top:10px;font-size:12px;color:var(--text-muted);">'
            f'<span style="font-weight:600;">The AI understood:</span> {chips_html}'
            f'</div>'
        )

    st.markdown(
        f'<div style="background:var(--surface);border:1px solid var(--border);'
        f'border-left:3px solid {conf_color};border-radius:12px;'
        f'padding:14px 18px;margin:1.5rem 0 1rem;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'flex-wrap:wrap;gap:10px;">'
        f'<div>'
        f'<span class="results-badge results-badge-ai">{n} matches</span>'
        f'<span style="font-size:13px;color:var(--text-muted);margin-left:10px;">'
        f'<strong style="color:{conf_color};">{conf_label}</strong> · top match {top_pct}%'
        f'</span>'
        f'</div></div>'
        f'{concept_chips}'
        f'</div>',
        unsafe_allow_html=True,
    )

# ════════════════════════════════════════════════════════════
# Classic Search Tab - title | author | genre (one mode at a time)
# ════════════════════════════════════════════════════════════
def _classic_search_tab(lib, rec):
    if rec is None or not hasattr(rec, "df"):
        st.info("Catalog still loading...")
        return

    df = rec.df

    # ── Mode selector - OUTSIDE the form so it updates instantly ──
    mode = st.radio(
        "Search by",
        options=["title", "author", "genre"],
        format_func=lambda x: {
            "title":  "Book title",
            "author": "Author name",
            "genre":  "Genre",
        }[x],
        horizontal=True,
        key="classic_mode",
    )

    # ── Form contains only the field for the chosen mode + filters ──
    with st.form("classic_search_form"):
        text_query = ""
        selected_genre = ""

        if mode == "title":
            text_query = st.text_input(
                "Book title",
                placeholder='e.g. "Norwegian Wood"',
                key="classic_title_query",
            )
        elif mode == "author":
            text_query = st.text_input(
                "Author name",
                placeholder='e.g. "Murakami"',
                key="classic_author_query",
            )
        else:  # genre
            genres = rec.all_genres() if hasattr(rec, "all_genres") else []
            selected_genre = st.selectbox(
                "Pick a genre",
                [""] + genres,
                index=0,
                key="classic_genre_pick",
            )

        col1, col2 = st.columns([1, 1])
        with col1:
            min_rating = st.slider("Min rating", 0.0, 5.0, 3.5, 0.25, key="classic_min_rating")
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                ["popularity", "rating", "title"],
                format_func=lambda x: {
                    "popularity": "Most Popular",
                    "rating":     "Highest Rated",
                    "title":      "Title A–Z",
                }[x],
                key="classic_sort",
            )

        submitted = st.form_submit_button("Search", use_container_width=True)

    # ── Process submission ──────────────────────────────────────
    if submitted:
        if mode in ("title", "author") and not text_query.strip():
            st.warning(f"Type a {'title' if mode == 'title' else 'name'} to search.")
            return
        if mode == "genre" and not selected_genre:
            st.warning("Pick a genre first.")
            return

        results = _do_classic_search(
            df=df,
            mode=mode,
            text_query=text_query,
            selected_genre=selected_genre,
            min_rating=min_rating,
            sort_by=sort_by,
        )

        st.session_state["classic_results"] = results
        st.session_state["classic_shown"]   = _PAGE_SIZE
        if mode == "title":
            st.session_state["classic_summary"] = f'Title contains "{text_query.strip()}"'
        elif mode == "author":
            st.session_state["classic_summary"] = f'Author contains "{text_query.strip()}"'
        else:
            st.session_state["classic_summary"] = f'Genre: {selected_genre}'
        st.rerun()

    results = st.session_state.get("classic_results", [])
    summary = st.session_state.get("classic_summary", "")

    if results:
        st.markdown(
            f'<div style="margin:1.5rem 0 1rem;display:flex;align-items:center;'
            f'gap:12px;flex-wrap:wrap;">'
            f'<span class="results-badge">{len(results)} books</span>'
            f'<span style="font-size:12.5px;color:var(--text-muted);">{safe(summary)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _render_results_grid(
            lib, results,
            shown=st.session_state["classic_shown"],
            prefix="classic",
            show_rank=False,
            show_ai_match=False,
            concepts=[],
        )
    elif summary:
        st.markdown(
            '<div class="empty-state">No books matched. Try loosening the rating filter '
            'or check your spelling.</div>',
            unsafe_allow_html=True,
        )


def _do_classic_search(df, mode, text_query, selected_genre, min_rating, sort_by, limit=60):
    filtered = df.copy()

    if mode == "title":
        q = text_query.strip().lower()
        filtered = filtered[
            filtered["title"].fillna("").str.lower().str.contains(q, regex=False)
        ]
    elif mode == "author":
        q = text_query.strip().lower()
        filtered = filtered[
            filtered["authors"].fillna("").str.lower().str.contains(q, regex=False)
        ]
    elif mode == "genre":
        g = selected_genre.lower()
        filtered = filtered[
            filtered["genres"].fillna("").str.lower().str.contains(g, regex=False)
        ]

    if min_rating > 0:
        filtered = filtered[
            pd.to_numeric(filtered["avg_rating"], errors="coerce").fillna(0) >= min_rating
        ]

    if sort_by == "popularity":
        filtered = filtered.sort_values("num_ratings", ascending=False)
    elif sort_by == "rating":
        filtered = filtered.sort_values("avg_rating", ascending=False)
    else:
        filtered = filtered.sort_values("title", ascending=True)

    filtered = filtered.head(limit)

    results = []
    for _, row in filtered.iterrows():
        book_id = row.get("book_id")
        if pd.isna(book_id):
            continue
        try:
            book_id_str = str(int(book_id))
        except Exception:
            book_id_str = str(book_id)

        results.append({
            "book_id":     book_id_str,
            "title":       str(row.get("title", "Unknown")),
            "authors":     str(row.get("authors", "")),
            "description": str(row.get("description", "") or ""),
            "genres":      str(row.get("genres", "") or ""),
            "avg_rating":  float(row.get("avg_rating") or 0),
            "num_ratings": int(row.get("num_ratings") or 0),
            "num_pages":   int(row.get("num_pages") or 0),
            "url":         str(row.get("url", "") or ""),
        })

    return results


# ════════════════════════════════════════════════════════════
# Shared results grid
# ════════════════════════════════════════════════════════════
def _render_results_grid(lib, results, shown, prefix, show_rank, show_ai_match, concepts):
    visible = results[:shown]
    rows = [visible[i:i + 3] for i in range(0, len(visible), 3)]

    for row_idx, row_books in enumerate(rows):
        base_i = row_idx * 3
        cols = st.columns(3)

        for col_idx, book in enumerate(row_books):
            i = base_i + col_idx
            in_lib = lib.get(book["book_id"]) is not None
            rank = (i + 1) if show_rank else None

            with cols[col_idx]:
                st.markdown(
                    render_book_card(
                        book,
                        in_library=in_lib,
                        query_concepts=concepts,
                        show_ai_match=show_ai_match,
                        rank=rank,
                    ),
                    unsafe_allow_html=True,
                )

        for col_idx, book in enumerate(row_books):
            i = base_i + col_idx
            in_lib = lib.get(book["book_id"]) is not None

            with cols[col_idx]:
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if not in_lib:
                        if st.button(
                            "Add to Collection",
                            key=f"{prefix}_add_{book['book_id']}_{i}",
                            use_container_width=True,
                        ):
                            lib.add(book["book_id"], book, status="want")
                            st.rerun()
                    else:
                        st.markdown(
                            '<div style="text-align:center;padding:6px;font-size:12px;'
                            'color:var(--success);font-weight:600;">Added</div>',
                            unsafe_allow_html=True,
                        )
                with btn_col2:
                    if book.get("url"):
                        st.markdown(
                            f'<div style="text-align:center;padding:6px;">'
                            f'<a href="{safe(book["url"])}" target="_blank" '
                            f'style="font-size:12px;color:var(--text-muted);text-decoration:none;">'
                            f'View Tome ↗</a></div>',
                            unsafe_allow_html=True,
                        )

        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    if shown < len(results):
        if st.button("Load more results", key=f"{prefix}_more", use_container_width=True):
            st.session_state[f"{prefix}_shown"] += _PAGE_SIZE
            st.rerun()