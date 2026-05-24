# ============================================================
# Griffin Library - The Chronicle (Stats + Sessions Log)
# ============================================================
# Two-tab view: reading statistics with AI insights,
# and a full filterable session history log.
# ============================================================

import streamlit as st
from collections import Counter
from datetime import date, timedelta

from core.insights import generate_insights
from .components import safe, render_insight_card


def render(lib):
    name  = lib.get_name() or "friend"
    books = lib.get_all()

    st.markdown("""
    <div class="page-title">The Chronicle</div>
    <div class="page-subtitle">Your deeds inscribed. Your legend measured.</div>
    """, unsafe_allow_html=True)

    tab_stats, tab_sessions = st.tabs(["📊 Stats", "🕯️ Sessions Log"])

    with tab_stats:
        _render_stats(lib, name, books)

    with tab_sessions:
        _render_sessions_log(lib)


# ─────────────────────────────────────────────────────────────
# SESSIONS LOG TAB
# ─────────────────────────────────────────────────────────────

def _render_sessions_log(lib):
    
    st.markdown(
        '<div style="font-size:13px;color:var(--text-muted);'
        'margin-bottom:1rem;line-height:1.6;">'
        'Every session logged - type, book, duration, pages, and notes.</div>',
        unsafe_allow_html=True,
    )

    try:
        log = lib.get_sessions_log() or {}
    except AttributeError:
        log = {}

    if not log:
        st.markdown(
            '<div class="empty-state">No sessions yet. '
            'Start one from <strong>Home</strong>.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Totals ────────────────────────────────────────────────
    all_entries = lib.get_all_session_entries()
    total_mins  = sum(e["duration_min"] for e in all_entries)
    total_pages = sum(e["pages_read"]   for e in all_entries)
    total_sess  = len(all_entries)
    total_days  = len(log)

    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Sessions", total_sess)
    with c2:
        h,m = divmod(total_mins, 60)
        st.metric("Reading time", f"{h}h {m}m" if h else f"{m}m")
    with c3: st.metric("Pages read", total_pages)
    with c4: st.metric("Active days", total_days)

    if total_sess > 0:
        avg = round(total_mins / total_sess, 1)
        book_sess = sum(1 for e in all_entries if e["type"]=="book")
        st.markdown(
            f'<div style="font-size:12px;color:var(--text-muted);margin:0.5rem 0 1rem;">'
            f'Avg session: <strong>{avg} min</strong> &nbsp;·&nbsp; '
            f'📚 {book_sess} book · 🌿 {total_sess-book_sess} free</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr class='eq-divider'>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────
    fc1, fc2, fc3 = st.columns([2, 1.5, 1.5])
    with fc1:
        search_date = st.text_input(
            "Filter by date", placeholder="e.g. 2026-05 or 2026-05-21",
            key="sess_search_date", label_visibility="collapsed"
        )
    with fc2:
        min_dur = st.number_input(
            "Min duration (min)", min_value=0, value=0, step=5,
            key="sess_min_dur", label_visibility="collapsed"
        )
    with fc3:
        type_filter = st.selectbox(
            "Type", ["All","📚 Book","🌿 Free"],
            key="sess_type_filter", label_visibility="collapsed"
        )

    filtered = all_entries
    if search_date.strip():
        filtered = [e for e in filtered if e["date"].startswith(search_date.strip())]
    if min_dur > 0:
        filtered = [e for e in filtered if e["duration_min"] >= min_dur]
    if type_filter == "📚 Book":
        filtered = [e for e in filtered if e["type"] == "book"]
    elif type_filter == "🌿 Free":
        filtered = [e for e in filtered if e["type"] == "free"]

    st.markdown(
        f'<div style="font-size:12px;color:var(--text-muted);margin:0.5rem 0 1rem;">'
        f'Showing {len(filtered)} of {total_sess} sessions</div>',
        unsafe_allow_html=True,
    )

    # ── Session cards ─────────────────────────────────────────
    today_d     = date.today()
    yesterday_d = today_d - timedelta(days=1)

    for entry in filtered:
        date_str = entry["date"]
        try:
            d = date.fromisoformat(date_str)
            if d == today_d:        day_label = f"Today · {d.strftime('%B %d')}"
            elif d == yesterday_d:  day_label = f"Yesterday · {d.strftime('%B %d')}"
            else:                   day_label = d.strftime("%a, %b %d, %Y")
        except:
            day_label = date_str

        is_book   = entry["type"] == "book"
        icon      = "📚" if is_book else "🌿"
        dur       = entry["duration_min"]
        pages     = entry["pages_read"]
        bk_title  = entry.get("book_title","")
        sp        = entry.get("start_page",0)
        ep        = entry.get("end_page",0)
        note      = entry.get("note","")
        sid       = entry["id"]
        t         = entry.get("time","")

        # Pages range label
        pages_label = ""
        if is_book and ep > sp:
            pages_label = f"p.{sp}→{ep} ({pages} pages)"
        elif pages > 0:
            pages_label = f"{pages} pages"

        border = "var(--primary)" if date_str == today_d.isoformat() else "var(--border)"

        time_suffix    = f" · {t}" if t else ""
        book_label     = safe(bk_title) if is_book and bk_title else "Free reading"
        pages_html     = (f'<div style="font-size:11px;color:var(--text-hint);margin-top:2px;">'
                          f'{safe(pages_label)}</div>') if pages_label else ""
        note_html      = (f'<div style="font-size:11px;color:var(--text-hint);'
                          f'font-style:italic;margin-top:4px;">"{safe(note)}"</div>') if note else ""

        st.markdown(
            f'<div class="eq-card" style="padding:0.9rem 1.1rem;margin-bottom:0.5rem;'
            f'border-left:3px solid {border};">'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div style="font-size:13px;font-weight:700;color:var(--text);">'
            f'{icon} {safe(day_label)}{time_suffix}</div>'
            f'<div style="font-size:12px;color:var(--text-muted);margin-top:3px;">'
            f'{book_label}</div>'
            f'{pages_html}'
            f'{note_html}'
            f'</div>'
            f'<div style="text-align:right;flex-shrink:0;">'
            f'<div style="font-size:18px;font-weight:800;color:var(--primary);">{dur}m</div>'
            f'</div></div></div>',
            unsafe_allow_html=True,
        )

        with st.expander("Add note" if not note else f"Edit note", expanded=False):
            new_note = st.text_area(
                "Note",
                value=note,
                placeholder="What did you read? How did it feel?",
                height=70,
                key=f"note_{sid}",
                label_visibility="collapsed",
            )
            col_s, col_d = st.columns([2,1])
            with col_s:
                if st.button("Save note", key=f"save_note_{sid}", use_container_width=True):
                    try:
                        lib.update_session_note(date_str, sid, new_note)
                        st.success("Note saved!")
                        st.rerun()
                    except AttributeError:
                        st.error("Update library.py to support notes.")
            with col_d:
                if st.button("Delete session", key=f"del_sess_{sid}",
                             use_container_width=True):
                    st.session_state[f"confirm_del_{sid}"] = True
                    st.rerun()

            if st.session_state.get(f"confirm_del_{sid}"):
                st.warning("Delete this session entry?")
                c1,c2 = st.columns(2)
                with c1:
                    if st.button("Cancel", key=f"cancel_del_{sid}", use_container_width=True):
                        st.session_state.pop(f"confirm_del_{sid}",None); st.rerun()
                with c2:
                    if st.button("Yes, delete", key=f"confirm_del_yes_{sid}",
                                 use_container_width=True):
                        try:
                            lib.delete_session_entry(date_str, sid)
                            st.session_state.pop(f"confirm_del_{sid}",None); st.rerun()
                        except AttributeError:
                            st.error("Update library.py.")


# ─────────────────────────────────────────────────────────────
# STATS TAB
# ─────────────────────────────────────────────────────────────

def _render_stats(lib, name, books):
    if not books:
        st.markdown(
            f'<div class="empty-state">Nothing to chart yet, {safe(name)}. '
            f'Add a few books and come back.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── AI Insights ─────────────────────────────────────────
    insights = generate_insights(lib)
    if insights:
        st.markdown(
            '<div class="section-heading">Oracle Insights · Forged for You</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="font-size:12.5px;color:var(--text-muted);'
            'margin-bottom:1rem;line-height:1.6;">'
            'Patterns the AI noticed in your reading. Updates automatically.</div>',
            unsafe_allow_html=True,
        )
        cols = st.columns(2)
        for i, insight in enumerate(insights):
            with cols[i % 2]:
                st.markdown(render_insight_card(insight), unsafe_allow_html=True)
        st.markdown("<hr class='eq-divider'>", unsafe_allow_html=True)

    # ── Core metrics ─────────────────────────────────────────
    book_list    = list(books.values())
    n_total      = len(book_list)
    n_read       = sum(1 for b in book_list if b.status == "read")
    n_reading    = sum(1 for b in book_list if b.status == "reading")
    n_want       = sum(1 for b in book_list if b.status == "want")
    total_quotes = lib.total_quotes()
    n_read_year  = lib.books_read_this_year()
    fav_genre    = lib.favorite_genre()
    streak       = lib.get_streak()
    rated        = [b for b in book_list if b.my_rating > 0]
    avg_rating   = round(sum(b.my_rating for b in rated) / len(rated), 2) if rated else 0.0

    st.markdown('<div class="section-heading">At a Glance</div>', unsafe_allow_html=True)

    cols = st.columns(4)
    for col, (val, label) in zip(cols, [
        (n_total, "Total books"),
        (n_read,  "Finished"),
        (total_quotes, "Inscriptions Kept"),
        (streak.count or 0, "Day Vigil"),
    ]):
        with col:
            st.markdown(
                f'<div class="stat-card">'
                f'<div class="stat-value">{val}</div>'
                f'<div class="stat-label">{safe(label)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-heading">Library Composition</div>', unsafe_allow_html=True)
        if n_total > 0:
            for label, count, color in [
                ("Reading",      n_reading, "var(--primary)"),
                ("Want to read", n_want,    "var(--accent)"),
                ("Read",         n_read,    "var(--success)"),
            ]:
                pct = int(count / n_total * 100) if n_total else 0
                st.markdown(
                    f'<div class="eq-card" style="padding:0.9rem 1.1rem;margin-bottom:0.5rem;">'
                    f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
                    f'<span style="font-size:13px;color:var(--text);">{safe(label)}</span>'
                    f'<span style="font-size:13px;font-weight:700;color:{color};">'
                    f'{count} ({pct}%)</span>'
                    f'</div>'
                    f'<div class="eq-progress-wrap" style="height:5px;">'
                    f'<div class="eq-progress-fill" style="width:{pct}%;background:{color};"></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

    with col2:
        st.markdown(
            f'<div class="section-heading">{date.today().year} Goal</div>',
            unsafe_allow_html=True,
        )
        goals  = lib.get_goals()
        yearly = max(int(goals.yearly_goal or 12), 1)
        pct    = min(int(n_read_year / yearly * 100), 100) if yearly else 0
        rem    = max(yearly - n_read_year, 0)
        st.markdown(
            f'<div class="eq-card">'
            f'<div style="font-size:28px;font-weight:700;color:var(--text);">'
            f'{n_read_year}<span style="font-size:15px;color:var(--text-muted);font-weight:500;"> / {yearly}</span>'
            f'</div>'
            f'<div class="eq-progress-wrap" style="margin:10px 0 6px;">'
            f'<div class="eq-progress-fill" style="width:{pct}%;"></div>'
            f'</div>'
            f'<div style="font-size:12px;color:var(--text-muted);">'
            f'{pct}% complete · {rem} {"book" if rem == 1 else "books"} to go'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        if fav_genre and fav_genre != "N/A":
            st.markdown(
                f'<div class="eq-card" style="margin-top:0.65rem;">'
                f'<div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;'
                f'letter-spacing:1px;font-weight:600;margin-bottom:4px;">Dominant Realm</div>'
                f'<div style="font-size:17px;font-weight:700;color:var(--ai);">{safe(fav_genre)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if rated:
            st.markdown(
                f'<div class="eq-card" style="margin-top:0.65rem;">'
                f'<div style="font-size:10px;color:var(--text-muted);text-transform:uppercase;'
                f'letter-spacing:1px;font-weight:600;margin-bottom:4px;">Average rating</div>'
                f'<div style="font-size:22px;font-weight:700;color:var(--warning);">★ {avg_rating}</div>'
                f'<div style="font-size:10px;color:var(--text-hint);margin-top:2px;">'
                f'across {len(rated)} judged</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Highest Honours ────────────────────────────────────────────
    if rated:
        top = sorted(rated, key=lambda b: b.my_rating, reverse=True)[:5]
        st.markdown(
            '<div class="section-heading" style="margin-top:1.25rem;">Your Top-Rated</div>',
            unsafe_allow_html=True,
        )
        for b in top:
            stars = "★" * b.my_rating + "☆" * (5 - b.my_rating)
            st.markdown(
                f'<div class="eq-card" style="display:flex;justify-content:space-between;'
                f'align-items:center;padding:0.8rem 1rem;margin-bottom:0.4rem;">'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:13px;font-weight:600;color:var(--text);'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{safe(b.title)}</div>'
                f'<div style="font-size:11px;color:var(--text-muted);">{safe(b.authors)}</div>'
                f'</div>'
                f'<div style="font-size:13px;color:var(--warning);margin-left:0.75rem;'
                f'flex-shrink:0;">{stars}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )