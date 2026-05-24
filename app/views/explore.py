# ============================================================
# Griffin Library - Explore (Catalog Insights)
# ============================================================
# Read-only analytics view: KPIs, top books, authors,
# genres, and rating distributions from the full catalog.
# ============================================================

import streamlit as st
import pandas as pd
from .components import safe


def render(lib, rec):
    st.markdown(
        '<div class="page-title">The Archives</div>'
        '<div class="page-subtitle">A guided look at the catalog - numbers, top picks, and patterns.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="page-mode-banner classic">
        <div class="page-mode-icon">📊</div>
        <div class="page-mode-text">
            <strong>Insights mode.</strong> Browse highlights and statistics across the whole catalog.
            To search for a specific book, author, or vibe - go to <strong>Discover</strong>.
        </div>
    </div>
    """, unsafe_allow_html=True)

    if rec is None or not hasattr(rec, "df"):
        st.info("Catalog still loading...")
        return

    df = rec.df.copy()

    for col, default in [
        ("title", ""), ("authors", ""), ("genres", ""),
        ("avg_rating", 0.0), ("num_ratings", 0), ("num_pages", 0),
    ]:
        if col not in df.columns:
            df[col] = default

    df["avg_rating"]  = pd.to_numeric(df["avg_rating"],  errors="coerce").fillna(0.0)
    df["num_ratings"] = pd.to_numeric(df["num_ratings"], errors="coerce").fillna(0).astype(int)
    df["num_pages"]   = pd.to_numeric(df["num_pages"],   errors="coerce").fillna(0).astype(int)

    # ══════════════════════════════════════════════════════
    # 1) KPIs
    # ══════════════════════════════════════════════════════
    _render_kpis(df, rec)

    st.markdown("<hr class='eq-divider'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════
    # 2) Tabs: Top Picks / Authors / Genres / Distributions
    # ══════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4 = st.tabs([
        "Top Books", "Top Authors", "Genres", "Distributions"
    ])

    with tab1:
        _render_top_books(df)

    with tab2:
        _render_top_authors(df)

    with tab3:
        _render_genres(df, rec)

    with tab4:
        _render_distributions(df)


# ════════════════════════════════════════════════════════════
# KPIs
# ════════════════════════════════════════════════════════════
def _render_kpis(df, rec):
    n_books = len(df)

    authors_series = df["authors"].fillna("").astype(str)
    unique_authors = set()
    for a in authors_series:
        for piece in a.split(","):
            piece = piece.strip()
            if piece:
                unique_authors.add(piece)
    n_authors = len(unique_authors)

    try:
        n_genres = len(rec.all_genres())
    except Exception:
        n_genres = 0

    avg_rating = round(float(df["avg_rating"].mean()), 2) if n_books else 0
    total_ratings = int(df["num_ratings"].sum())

    avg_pages = int(df.loc[df["num_pages"] > 0, "num_pages"].mean()) if (df["num_pages"] > 0).any() else 0

    st.markdown('<div class="section-heading">At a Glance</div>', unsafe_allow_html=True)

    cols = st.columns(3)
    metrics_top = [
        (f"{n_books:,}",     "Books in catalog"),
        (f"{n_authors:,}",   "Unique authors"),
        (f"{n_genres:,}",    "Genres"),
    ]
    for col, (val, label) in zip(cols, metrics_top):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{val}</div>
                <div class="stat-label">{safe(label)}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)

    cols = st.columns(3)
    metrics_bottom = [
        (f"★ {avg_rating}",         "Average rating"),
        (f"{total_ratings/1_000_000:.1f}M" if total_ratings >= 1_000_000 else f"{total_ratings:,}",
                                    "Total ratings"),
        (f"{avg_pages}",            "Avg. pages / book"),
    ]
    for col, (val, label) in zip(cols, metrics_bottom):
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{val}</div>
                <div class="stat-label">{safe(label)}</div>
            </div>
            """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════
# Top Books
# ════════════════════════════════════════════════════════════
def _render_top_books(df):
    st.markdown(
        '<div style="font-size:13px; color:var(--text-muted); margin: 0.5rem 0 1rem; line-height:1.6;">'
        'The catalog\'s most-acclaimed and most-popular books, side by side.</div>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-heading">Highest Rated</div>', unsafe_allow_html=True)
        eligible = df[df["num_ratings"] >= 1000]
        if eligible.empty:
            eligible = df
        top_rated = eligible.sort_values("avg_rating", ascending=False).head(10)
        _render_book_list(top_rated, metric="rating")

    with col_b:
        st.markdown('<div class="section-heading">Most Popular</div>', unsafe_allow_html=True)
        top_pop = df.sort_values("num_ratings", ascending=False).head(10)
        _render_book_list(top_pop, metric="popularity")


def _render_book_list(rows, metric="rating"):
    if rows is None or len(rows) == 0:
        st.markdown(
            '<div class="empty-state">No data available.</div>',
            unsafe_allow_html=True,
        )
        return

    for rank, (_, row) in enumerate(rows.iterrows(), start=1):
        title = safe(str(row.get("title", "Unknown"))[:70])
        author = safe(str(row.get("authors", "")).split(",")[0].strip())
        rating = float(row.get("avg_rating") or 0)
        n_ratings = int(row.get("num_ratings") or 0)

        if metric == "rating":
            metric_html = (
                f'<div style="font-size:14px; color:var(--warning); font-weight:700;">★ {rating:.2f}</div>'
                f'<div style="font-size:10.5px; color:var(--text-hint); margin-top:1px;">{n_ratings:,} ratings</div>'
            )
        else:
            if n_ratings >= 1_000_000:
                pop_str = f"{n_ratings/1_000_000:.1f}M"
            elif n_ratings >= 1000:
                pop_str = f"{n_ratings/1000:.0f}K"
            else:
                pop_str = f"{n_ratings:,}"
            metric_html = (
                f'<div style="font-size:14px; color:var(--primary); font-weight:700;">{pop_str}</div>'
                f'<div style="font-size:10.5px; color:var(--text-hint); margin-top:1px;">★ {rating:.2f}</div>'
            )

        st.markdown(
            f'<div class="eq-card" style="display:flex; align-items:center; gap:12px; '
            f'padding:0.75rem 1rem; margin-bottom:0.5rem;">'
            f'<div style="flex-shrink:0; width:26px; height:26px; border-radius:50%; '
            f'background:var(--primary-soft); color:var(--primary); display:flex; '
            f'align-items:center; justify-content:center; font-size:12px; font-weight:700;">'
            f'{rank}</div>'
            f'<div style="flex:1; min-width:0;">'
            f'<div style="font-size:13.5px; font-weight:600; color:var(--text); '
            f'line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{title}</div>'
            f'<div style="font-size:11.5px; color:var(--text-muted); margin-top:2px; '
            f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{author}</div>'
            f'</div>'
            f'<div style="text-align:right; flex-shrink:0;">{metric_html}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════
# Top Authors
# ════════════════════════════════════════════════════════════
def _render_top_authors(df):
    st.markdown(
        '<div style="font-size:13px; color:var(--text-muted); margin: 0.5rem 0 1rem; line-height:1.6;">'
        'Authors with the most books in the catalog and their average ratings.</div>',
        unsafe_allow_html=True,
    )

    df_authors = df.copy()
    df_authors["primary_author"] = df_authors["authors"].fillna("").astype(str).apply(
        lambda s: s.split(",")[0].strip() if s else ""
    )
    df_authors = df_authors[df_authors["primary_author"] != ""]

    grouped = df_authors.groupby("primary_author").agg(
        book_count=("title", "count"),
        avg_rating=("avg_rating", "mean"),
        total_ratings=("num_ratings", "sum"),
    ).reset_index()

    if grouped.empty:
        st.markdown('<div class="empty-state">No authors found.</div>', unsafe_allow_html=True)
        return

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<div class="section-heading">Most Prolific</div>', unsafe_allow_html=True)
        top_count = grouped.sort_values("book_count", ascending=False).head(10)
        _render_author_list(top_count, sort_metric="count")

    with col_b:
        st.markdown('<div class="section-heading">Most Read (by ratings)</div>', unsafe_allow_html=True)
        elig = grouped[grouped["book_count"] >= 2]
        if elig.empty:
            elig = grouped
        top_pop_authors = elig.sort_values("total_ratings", ascending=False).head(10)
        _render_author_list(top_pop_authors, sort_metric="ratings")


def _render_author_list(rows, sort_metric="count"):
    for rank, (_, row) in enumerate(rows.iterrows(), start=1):
        name = safe(row["primary_author"])
        book_count = int(row["book_count"])
        avg_r = float(row["avg_rating"])
        total_r = int(row["total_ratings"])

        if sort_metric == "count":
            primary_val = f"{book_count}"
            primary_label = "books"
        else:
            if total_r >= 1_000_000:
                primary_val = f"{total_r/1_000_000:.1f}M"
            elif total_r >= 1000:
                primary_val = f"{total_r/1000:.0f}K"
            else:
                primary_val = f"{total_r:,}"
            primary_label = "ratings"

        st.markdown(
            f'<div class="eq-card" style="display:flex; align-items:center; gap:12px; '
            f'padding:0.75rem 1rem; margin-bottom:0.5rem;">'
            f'<div style="flex-shrink:0; width:26px; height:26px; border-radius:50%; '
            f'background:var(--ai-soft); color:var(--ai); display:flex; '
            f'align-items:center; justify-content:center; font-size:12px; font-weight:700;">'
            f'{rank}</div>'
            f'<div style="flex:1; min-width:0;">'
            f'<div style="font-size:13.5px; font-weight:600; color:var(--text); '
            f'white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{name}</div>'
            f'<div style="font-size:11px; color:var(--text-muted); margin-top:2px;">'
            f'★ {avg_r:.2f} avg · {book_count} book{"s" if book_count != 1 else ""}</div>'
            f'</div>'
            f'<div style="text-align:right; flex-shrink:0;">'
            f'<div style="font-size:14px; color:var(--ai); font-weight:700;">{primary_val}</div>'
            f'<div style="font-size:10.5px; color:var(--text-hint);">{primary_label}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ════════════════════════════════════════════════════════════
# Genres
# ════════════════════════════════════════════════════════════
def _render_genres(df, rec):
    st.markdown(
        '<div style="font-size:13px; color:var(--text-muted); margin: 0.5rem 0 1rem; line-height:1.6;">'
        'How the catalog is distributed across genres.</div>',
        unsafe_allow_html=True,
    )

    try:
        genre_list = rec.all_genres()
    except Exception:
        genre_list = []

    if not genre_list:
        st.markdown('<div class="empty-state">No genres available.</div>', unsafe_allow_html=True)
        return

    genres_lower = df["genres"].fillna("").astype(str).str.lower()

    counts = []
    for g in genre_list:
        cnt = int(genres_lower.str.contains(g.lower(), regex=False).sum())
        if cnt > 0:
            counts.append({"genre": g, "count": cnt})

    if not counts:
        st.markdown('<div class="empty-state">No genre counts available.</div>', unsafe_allow_html=True)
        return

    counts_df = pd.DataFrame(counts).sort_values("count", ascending=False).head(15)

    try:
        import altair as alt

        chart = (
            alt.Chart(counts_df)
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X("count:Q", title="Number of books"),
                y=alt.Y("genre:N", sort="-x", title=None),
                color=alt.Color(
                    "count:Q",
                    scale=alt.Scale(scheme="purples"),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("genre:N", title="Genre"),
                    alt.Tooltip("count:Q", title="Books", format=","),
                ],
            )
            .properties(height=420)
            .configure_axis(
                labelColor="#5C4A35",
                titleColor="#2D2010",
                labelFontSize=12,
                titleFontSize=12,
            )
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        for _, row in counts_df.iterrows():
            pct = int(row["count"] / counts_df["count"].max() * 100)
            st.markdown(
                f'<div style="margin-bottom:8px;">'
                f'<div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:3px;">'
                f'<span style="color:var(--text);">{safe(row["genre"])}</span>'
                f'<span style="color:var(--text-muted);">{int(row["count"]):,}</span>'
                f'</div>'
                f'<div class="eq-progress-wrap"><div class="eq-progress-fill" style="width:{pct}%;"></div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ════════════════════════════════════════════════════════════
# Distributions
# ════════════════════════════════════════════════════════════
def _render_distributions(df):
    st.markdown(
        '<div style="font-size:13px; color:var(--text-muted); margin: 0.5rem 0 1rem; line-height:1.6;">'
        'How ratings and book lengths are distributed across the catalog.</div>',
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    # ── Ratings distribution ──
    with col_a:
        st.markdown('<div class="section-heading">Average Rating Distribution</div>', unsafe_allow_html=True)
        ratings_df = df[df["avg_rating"] > 0][["avg_rating"]].copy()

        try:
            import altair as alt
            chart = (
                alt.Chart(ratings_df)
                .mark_bar(cornerRadiusEnd=3)
                .encode(
                    x=alt.X("avg_rating:Q", bin=alt.Bin(maxbins=20), title="Average rating"),
                    y=alt.Y("count():Q", title="Books"),
                    color=alt.value("#2E6DA4"),
                    tooltip=[
                        alt.Tooltip("avg_rating:Q", bin=alt.Bin(maxbins=20), title="Rating"),
                        alt.Tooltip("count():Q", title="Books", format=","),
                    ],
                )
                .properties(height=280)
                .configure_view(strokeWidth=0)
            )
            st.altair_chart(chart, use_container_width=True)
        except Exception:
            st.bar_chart(ratings_df["avg_rating"].value_counts().sort_index())

    # ── Pages distribution ──
    with col_b:
        st.markdown('<div class="section-heading">Pages per Book</div>', unsafe_allow_html=True)

        total_books = len(df)
        with_pages = (df["num_pages"] > 0).sum()
        without_pages = total_books - with_pages
        pct_with = int(with_pages / total_books * 100) if total_books else 0

        st.markdown(
            f'<div style="font-size:11.5px; color:var(--text-muted); margin-bottom:10px; ' 
            f'padding:8px 12px; background:var(--surface-alt); border-radius:8px; line-height:1.6;">' 
            f'<strong>{with_pages:,}</strong> of {total_books:,} books have page data ({pct_with}%). ' 
            f'<span style="color:var(--text-hint);">{without_pages:,} books not counted.</span>' 
            f'</div>',
            unsafe_allow_html=True,
        )

        pages_df = df[(df["num_pages"] > 0) & (df["num_pages"] <= 1500)][["num_pages"]].copy()

        if pages_df.empty:
            st.markdown('<div class="empty-state">No page data available.</div>', unsafe_allow_html=True)
        else:
            try:
                import altair as alt
                chart = (
                    alt.Chart(pages_df)
                    .mark_bar(cornerRadiusEnd=3)
                    .encode(
                        x=alt.X("num_pages:Q", bin=alt.Bin(maxbins=25), title="Number of pages"),
                        y=alt.Y("count():Q", title="Books (with page data)"),
                        color=alt.value("#7C3AED"),
                        tooltip=[
                            alt.Tooltip("num_pages:Q", bin=alt.Bin(maxbins=25), title="Pages"),
                            alt.Tooltip("count():Q", title="Books", format=","),
                        ],
                    )
                    .properties(height=280)
                    .configure_view(strokeWidth=0)
                )
                st.altair_chart(chart, use_container_width=True)
            except Exception:
                st.bar_chart(pages_df["num_pages"].value_counts().sort_index())

    # ── Rating vs Popularity scatter ──
    st.markdown(
        '<div class="section-heading" style="margin-top:1.5rem;">Rating vs. Popularity</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:12px; color:var(--text-muted); margin-bottom: 8px; line-height:1.5;">'
        'Each dot is a book. The popular and well-loved ones cluster in the top-right.</div>',
        unsafe_allow_html=True,
    )

    scatter_df = df[(df["avg_rating"] > 0) & (df["num_ratings"] > 0)].copy()
    if len(scatter_df) > 2000:
        scatter_df = scatter_df.sample(2000, random_state=42)

    try:
        import altair as alt
        scatter = (
            alt.Chart(scatter_df)
            .mark_circle(opacity=0.45)
            .encode(
                x=alt.X(
                    "num_ratings:Q",
                    scale=alt.Scale(type="log"),
                    title="Number of ratings (log scale)",
                ),
                y=alt.Y(
                    "avg_rating:Q",
                    scale=alt.Scale(domain=[2.5, 5.0]),
                    title="Average rating",
                ),
                color=alt.Color(
                    "avg_rating:Q",
                    scale=alt.Scale(scheme="purples"),
                    legend=None,
                ),
                size=alt.Size(
                    "num_ratings:Q",
                    scale=alt.Scale(range=[20, 250]),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("title:N", title="Title"),
                    alt.Tooltip("authors:N", title="Author"),
                    alt.Tooltip("avg_rating:Q", title="Rating", format=".2f"),
                    alt.Tooltip("num_ratings:Q", title="# Ratings", format=","),
                ],
            )
            .properties(height=380)
            .configure_view(strokeWidth=0)
        )
        st.altair_chart(scatter, use_container_width=True)
    except Exception:
        st.info("Interactive chart unavailable - install altair to view it.")