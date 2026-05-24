# ============================================================
# Griffin Library - Custom Book Entry
# ============================================================
# Form to manually add a book not found in the catalog.
# Saves to the user library with optional rating and status.
# ============================================================
import time
import streamlit as st
from .components import safe


def custom_badge() -> str:
    return (
        '<span style="background:var(--accent-soft); color:var(--accent); '
        'font-size:10px; font-weight:700; padding:2px 8px; '
        'border-radius:100px; border:1px solid rgba(0,0,0,0.08); '
        'margin-left:6px; vertical-align:middle;">✍️ Your book</span>'
    )


def render_add_custom_book(lib, rec):
    st.markdown(
        '<div class="section-heading" style="margin-top:2rem;">'
        '✍️ Add a book not in the catalog'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:13px; color:var(--text-muted); '
        'margin-bottom:1.25rem; line-height:1.6;">'
        "Can't find a book in the catalog? Add it manually. "
        "It will appear in your library and sessions."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.form("add_custom_book_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input(
                "Title *",
                placeholder="e.g. The Midnight Library",
                key="_cb_title",
            )
        with col2:
            author = st.text_input(
                "Author *",
                placeholder="e.g. Matt Haig",
                key="_cb_author",
            )

        description = st.text_area(
            "Description (optional)",
            placeholder="Optional: notes about this book - themes, your thoughts, anything useful.",
            height=140,
            key="_cb_description",
        )

        col3, col4, col5 = st.columns(3)
        with col3:
            genres = st.text_input(
                "Genres",
                placeholder="Fiction, Philosophy",
                key="_cb_genres",
            )
        with col4:
            num_pages = st.number_input(
                "Pages",
                min_value=0,
                value=0,
                step=10,
                key="_cb_pages",
            )
        with col5:
            status = st.selectbox(
                "Add to shelf",
                options=["want", "reading", "read"],
                format_func=lambda s: {
                    "want":    "📚 Want to read",
                    "reading": "📖 Currently reading",
                    "read":    "✅ Already read",
                }[s],
                key="_cb_status",
            )

        rating = st.select_slider(
            "Your rating",
            options=[0, 1, 2, 3, 4, 5],
            format_func=lambda v: "No rating" if v == 0 else "★" * v + "☆" * (5 - v),
            value=0,
            key="_cb_rating",
        )

        submitted = st.form_submit_button("Add to my library", use_container_width=True)

    if not submitted:
        return

    errors = []
    if not title.strip():
        errors.append("⚠️ Title is required.")
    if not author.strip():
        errors.append("⚠️ Author is required.")

    if errors:
        for e in errors:
            st.warning(e)
        return

    book_id = f"custom_{int(time.time() * 1000)}"
    pages   = int(num_pages)

    book_data = {
        "book_id":         book_id,
        "title":           title.strip(),
        "authors":         author.strip(),
        "genres":          genres.strip(),
        "description":     description.strip(),
        "avg_rating":      0.0,
        "num_ratings":     0,
        "num_pages":       pages,
        "url":             "",
        "rating_norm":     0.0,
        "popularity_norm": 0.0,
        "is_custom":       True,
        "_embedding":      None,
    }

    lib.add(book_id, book_data, status=status)
    if rating > 0:
        lib.update_rating(book_id, rating)

    # Set total_pages so the sessions timer shows the correct page ceiling.
    if pages > 0:
        lib.update_pages(book_id, total=pages, current=0)

    st.success(f"✅ **{safe(title.strip())}** added to your library.")

    for _k in ["_cb_title", "_cb_author", "_cb_description",
               "_cb_genres", "_cb_pages", "_cb_status", "_cb_rating"]:
        st.session_state.pop(_k, None)
    st.rerun()


def embedding_status_html(book) -> str:
    return ""