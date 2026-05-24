# ============================================================
# Griffin Library - Inscriptions (Quotes)
# ============================================================
# Displays saved quotes with semantic search, tag filters,
# and image export (Render as Relic).
# ============================================================

import streamlit as st
from datetime import date
from .components import safe


def render(lib, quote_search):
    name = lib.get_name() or "friend"
    all_quotes = lib.all_quotes()

    st.html(
        '<div class="page-title">Inscriptions</div>'
        '<div class="page-subtitle">The passages you preserved - ready to illuminate your path again. '
        'Each may be rendered as a relic worthy of sharing.</div>'
    )

    if not all_quotes:
        st.html(
            f'<div class="empty-state">'
            f'No inscriptions yet, {safe(name)}. The passages that stir the soul deserve to be preserved. '
            f'Inscribe them from <strong>My Collection</strong>, then come back here to search '
            f'them semantically or export them as images.'
            f'</div>'
        )
        return

    _render_quote_of_day(all_quotes)

    tab_search, tab_all, tab_tags = st.tabs([
        "Oracle Search",
        f"All Inscriptions ({len(all_quotes)})",
        "Seals",
    ])

    with tab_search:
        _render_search_tab(lib, quote_search, name, all_quotes)

    with tab_all:
        _render_all_tab(lib, all_quotes)

    with tab_tags:
        _render_tags_tab(lib, all_quotes)


def _render_quote_of_day(all_quotes):
    if not all_quotes:
        return
    seed = date.today().toordinal()
    pick = all_quotes[seed % len(all_quotes)]

    st.html(f"""
    <div style="background: linear-gradient(135deg, var(--ai-soft) 0%, var(--accent-soft) 100%);
                border: 1px solid rgba(124,58,237,0.15);
                border-radius: 16px; padding: 1.75rem 2rem; margin-bottom: 1.5rem;
                position: relative; overflow:hidden;">
        <div style="position:absolute; top:0; left:0; width:4px; height:100%;
                    background: linear-gradient(180deg, var(--ai), var(--accent));"></div>
        <div style="font-size:11px; color:var(--ai); font-weight:700;
                    text-transform:uppercase; letter-spacing:1.5px; margin-bottom:14px;">
            Inscription of the Hour
        </div>
        <div style="font-family: 'DM Serif Display', serif; font-size:22px;
                    color:var(--text); line-height:1.5; margin-bottom:16px;
                    font-style: italic;">
            "{safe(pick['text'])}"
        </div>
        <div style="font-size:13px; color:var(--text-muted); font-weight:500;">
            — {safe(pick['title'])}{f" · {safe(pick['author'])}" if pick.get('author') else ""}
        </div>
    </div>
    """)


def _render_search_tab(lib, quote_search, name, all_quotes):
    st.html(f"""
    <div style="background: var(--surface); border: 1px solid var(--border);
                border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem;
                border-left: 3px solid var(--ai);">
        <div style="font-size:13px; color:var(--text-muted); line-height:1.6;">
            <strong style="color:var(--ai);">Semantic search</strong> finds quotes by meaning,
            not just keywords. Try <em>"the line about courage and fear"</em> or
            <em>"something hopeful about loss"</em>, {safe(name)}.
        </div>
    </div>
    """)

    if quote_search is None:
        st.info("The Oracle's search engine is awakening. Browse the All Inscriptions tab while the Oracle stirs.")
        return

    with st.form("quote_search_form"):
        query = st.text_input(
            "Search your inscriptions",
            placeholder='e.g. "the part about resilience and second chances"',
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Search", use_container_width=True)

    if submitted and query.strip():
        with st.spinner("Searching your quote collection..."):
            results = quote_search.search(lib, query.strip(), top_k=10)

        if not results:
            st.html('<div class="empty-state">No matching inscriptions. Try a different phrase or check '
                'the All tab.</div>')
        else:
            st.html(f'<div style="margin: 1rem 0;">'
                f'<span class="results-badge results-badge-ai">{len(results)} inscriptions found</span>'
                f'</div>')
            for r in results:
                _render_quote_card(r, show_score=True, key_prefix=f"sq_{r['book_id']}_{r['quote_idx']}")


def _render_all_tab(lib, all_quotes):
    n_books = len(set(q["title"] for q in all_quotes))
    st.html(f"""
    <div style="display:flex; align-items:center; gap:12px; margin: 1rem 0;">
        <span class="results-badge">{len(all_quotes)} quotes</span>
        <span style="font-size:12px; color:var(--text-hint);">
            across {n_books} {'book' if n_books == 1 else 'books'}
        </span>
    </div>
    """)

    for q in all_quotes:
        _render_quote_card(q, show_score=False, key_prefix=f"all_{q['book_id']}_{q['quote_idx']}")


def _render_tags_tab(lib, all_quotes):
    tags = lib.all_user_tags()

    if not tags:
        st.html('<div class="empty-state">No seals yet. Add seals to inscriptions from My Library to '
            'organize them here.</div>')
        return

    selected_tag = st.selectbox(
        "Filter by tag",
        ["All"] + tags,
        key="quotes_tag_filter",
    )

    if selected_tag == "All":
        filtered = all_quotes
    else:
        filtered = [q for q in all_quotes if selected_tag in q.get("tags", [])]

    st.html(f'<div style="margin: 1rem 0;">'
        f'<span class="results-badge">{len(filtered)} quotes</span>'
        f'</div>')

    for q in filtered:
        _render_quote_card(q, show_score=False, key_prefix=f"tag_{q['book_id']}_{q['quote_idx']}")


def _render_quote_card(q, show_score=False, key_prefix=""):
    score_html = ""
    if show_score and "score" in q:
        score = int(q["score"] * 100)
        score_html = (
            f'<span style="background:var(--ai-soft); color:var(--ai); '
            f'font-size:10.5px; font-weight:700; padding:2px 8px; border-radius:100px; '
            f'border:1px solid rgba(124,58,237,0.25); margin-left:8px;">'
            f'{score}% match</span>'
        )

    tags_html = ""
    if q.get("tags"):
        tags_html = "".join(
            f'<span class="tag-chip">#{safe(t)}</span>' for t in q["tags"]
        )

    page_label = f"page {safe(q['page'])}" if q.get('page') else ""
    date_label = safe(q.get('date', ''))
    meta = " · ".join(p for p in [page_label, date_label] if p)

    quote_class = "quote-card quote-card-ai" if show_score else "quote-card"

    st.html(
        f'<div class="eq-card" style="margin-bottom: 1rem;">'
        f'<div class="{quote_class}" style="margin-bottom: 14px;">'
        f'"{safe(q["text"])}"'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; flex-wrap:wrap;">'
        f'<div style="flex:1; min-width:200px;">'
        f'<div style="font-size:14px; font-weight:600; color:var(--text);">'
        f'{safe(q["title"])}{score_html}'
        f'</div>'
        f'<div style="font-size:12px; color:var(--text-muted); margin-top:2px;">'
        f'{safe(q.get("author", ""))}'
        f'</div>'
        f'<div style="margin-top:8px;">{tags_html}</div>'
        f'</div>'
        f'<div style="font-size:11px; color:var(--text-hint); text-align:right;">'
        f'{meta}'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    if key_prefix:
        col1, col2, _ = st.columns([1.2, 1, 2])
        with col1:
            if st.button("Render as Relic", key=f"{key_prefix}_export", use_container_width=True):
                st.session_state[f"_export_quote_{key_prefix}"] = q

        if st.session_state.get(f"_export_quote_{key_prefix}"):
            _render_image_export(q, key_prefix)


def _render_image_export(quote: dict, key_prefix: str):
    from core.quote_image import render_quote_image, PALETTES

    palette = st.selectbox(
        "Relic Style",
        list(PALETTES.keys()),
        format_func=lambda x: f"{x.title()}",
        key=f"{key_prefix}_palette",
    )

    try:
        png = render_quote_image(
            text=quote["text"],
            title=quote.get("title", ""),
            author=quote.get("author", ""),
            palette=palette,
        )
        st.image(png, use_container_width=True)
        st.download_button(
            "Claim Relic",
            data=png,
            file_name=f"griffin_library_{quote['book_id']}_{quote['quote_idx']}.png",
            mime="image/png",
            key=f"{key_prefix}_download",
        )
    except Exception as e:
        st.error(f"Image export failed: {e}")

    if st.button("Close", key=f"{key_prefix}_close"):
        st.session_state.pop(f"_export_quote_{key_prefix}", None)
        st.rerun()