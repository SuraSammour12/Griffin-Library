# ============================================================
# Griffin Library - For You (Personalized Recommendations)
# ============================================================
# Builds a taste profile from the user library and returns
# the top AI-matched books not yet in their collection.
# ============================================================

import streamlit as st
from .components import render_book_card, safe


def render(lib, rec):
    name = lib.get_name() or "friend"

    st.markdown("""
    <div class="page-title">For You</div>
    <div class="page-subtitle">Tomes chosen by the Oracle from the depths of your chronicle. The Oracle grows wiser with every verdict you render.</div>
    """, unsafe_allow_html=True)

    if rec is None:
        st.markdown(
            '<div class="empty-state">The Oracle is consulting the ancient archives. A moment, Scholar. '
            'Give it a moment.</div>',
            unsafe_allow_html=True,
        )
        return

    rated = [b for b in lib.get_all().values() if b.my_rating > 0 or b.status in ("read", "reading")]

    if len(rated) < 1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, var(--ai-soft) 0%, var(--accent-soft) 100%);
                    border: 1px solid rgba(124,58,237,0.2);
                    border-radius: 14px; padding: 2rem; text-align:center;">
            <div style="font-size:18px; font-weight:700; color:var(--text);
                        margin-bottom:8px; letter-spacing:-0.3px;">
                The Oracle must first learn your soul
            </div>
            <div style="font-size:14px; color:var(--text-muted); line-height:1.6;
                        max-width:480px; margin: 0 auto;">
                Acquire tomes to your collection - especially ones you've already read and rated -
                and the Oracle will reveal tomes forged for your spirit, {safe(name)}.
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    with st.spinner("Building your taste profile and finding matches..."):
        response = rec.recommend_for_you(lib, top_k=12)

    if not response["ok"]:
        if response["error"] == "no_profile":
            st.warning("Couldn't build a taste profile yet. Acquire a few books and try again.")
        else:
            st.error("Something went wrong generating recommendations. Try refreshing.")
        return

    results = response["results"]
    sources = response["based_on"]

    if not results:
        st.markdown(
            '<div class="empty-state">All worthy tomes are already in your vaults - '
            'A Scholar of true discernment. Acquire more tomes to keep the Oracle&#39;s visions renewed.</div>',
            unsafe_allow_html=True,
        )
        return

    if sources:
        source_titles = ", ".join(f"<strong>{safe(s['title'])}</strong>" for s in sources[:3])
        more = f" + {len(sources) - 3} more" if len(sources) > 3 else ""
        st.markdown(f"""
        <div style="background: var(--surface); border: 1px solid var(--border);
                    border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1.5rem;
                    border-left: 3px solid var(--ai);">
            <div style="font-size:11px; color:var(--ai); font-weight:600;
                        text-transform:uppercase; letter-spacing:1px; margin-bottom:6px;">
                Scholar&#39;s Profile
            </div>
            <div style="font-size:13px; color:var(--text-muted); line-height:1.6;">
                Forged from your affinity for {source_titles}{more}.
                Tomes you judged highly carry greater weight in the Oracle&#39;s vision.
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(
        f'<div style="margin-bottom: 1rem;">'
        f'<span class="results-badge results-badge-ai">{len(results)} tomes chosen for you</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)
    for i, book in enumerate(results):
        with cols[i % 3]:
            st.markdown(
                render_book_card(book, in_library=False, show_ai_match=True),
                unsafe_allow_html=True,
            )

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("Acquire", key=f"foryou_add_{book['book_id']}_{i}", use_container_width=True):
                    lib.add(book["book_id"], book, status="want")
                    st.rerun()
            with btn_col2:
                if book.get("url"):
                    st.markdown(
                        f'<div style="text-align:center; padding:6px;">'
                        f'<a href="{safe(book["url"])}" target="_blank" '
                        f'style="font-size:12px; color:var(--text-muted); text-decoration:none;">'
                        f'View Tome ↗</a></div>',
                        unsafe_allow_html=True,
                    )
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    with st.expander("How does the Oracle see?"):
        st.markdown("""
        Your **Scholar's essence** is a 768-dimensional embedding built from books in your library:

        - **Tomes you sealed and judged 5★** carry the most weight
        - **Tomes currently open** count as moderate signal
        - **Tomes on your acquisition list** count as light signal

        The Oracle weaves these into a single vector representing your taste, then searches the
        catalog for the nearest undiscovered tomes. **MMR re-ranking** ensures variety so you don't
        see ten near-identical books.

        The more you judge, the keener the Oracle's sight.
        """)