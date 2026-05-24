# ============================================================
# Griffin Library - My Collection (View)
# ============================================================
# Renders the user library with tabs for reading status.
# Handles book management, notes, quotes, and content moderation.
# ============================================================

import streamlit as st
import re
from datetime import date
from .components import safe
from .custom_book import render_add_custom_book, custom_badge, embedding_status_html

# ── Content moderation constants ─────────────────────────────
_MAX_VIOLATIONS = 3

_SEXUAL_PATTERNS = [
    r'\b(porn|pornography|nude|naked|sex tape|onlyfans|masturbat|orgasm|erotic)\b',
    r'\b(fuck(?:ing)?|pussy|dick|cock|cum shot|blowjob|handjob|gangbang)\b',
]

_SELFHARM_PATTERNS = [
    r'\b(kill\s+my\s*self|killing\s+my\s*self|end\s+my\s+life|want\s+to\s+die|suicid|take\s+my\s+life)\b',
    r'\b(i\s+want\s+to\s+die|i\s+wish\s+i\s+was\s+dead|no\s+reason\s+to\s+live|can\'t\s+go\s+on)\b',
    r'\b(overdose\s+on\s+purpose|hurt\s+my\s*self|self[\s\-]harm|cut\s+my\s*self)\b',
]


def _is_sexual(text: str) -> bool:
    t = text.lower()
    for p in _SEXUAL_PATTERNS:
        if re.search(p, t, re.IGNORECASE):
            return True
    return False


def _is_selfharm(text: str) -> bool:
    t = text.lower()
    for p in _SELFHARM_PATTERNS:
        if re.search(p, t, re.IGNORECASE):
            return True
    return False


def _handle_content(lib, text: str) -> bool:
    if _is_selfharm(text):
        st.warning(
            "It sounds like you might be going through something really hard right now. "
            "You don't have to face it alone.\n\n"
            "If you're in crisis, please reach out - **International Lifeline: 988** "
            "(or your local crisis line). There are people who want to help.\n\n"
            "_If you were looking for books about grief, loss, or difficult emotions - "
            "feel free to rephrase your search and we'll help you find something meaningful._"
        )
        return True

    if _is_sexual(text):
        count = st.session_state.get("_violation_count", 0) + 1
        st.session_state["_violation_count"] = count
        remaining = _MAX_VIOLATIONS - count

        if count >= _MAX_VIOLATIONS:
            st.error(
                "⛔ **Access Revoked.** \n\n"
                "Your account has been permanently removed from the Library vaults due to "
                "repeated submission of inappropriate content. This cannot be undone."
            )
            lib.reset()
            st.session_state.clear()
            st.session_state["page"] = "Welcome"
            st.rerun()
        else:
            st.warning(
                f"⚠️ **Violation of the Library's Code - Strike {count} of {_MAX_VIOLATIONS}**\n\n"
                f"This content violates the sacred rules of Griffin Library. "
                f"Scholars are expected to conduct themselves with honour.\n\n"
                f"**{remaining} {'strike' if remaining == 1 else 'strikes'} remaining** "
                f"before permanent removal."
            )
        return True

    return False


def render(lib, rec=None):
    name = lib.get_name() or "Scholar"
    books = lib.get_all()

    if "celebrate_book" in st.session_state:
        celebrated = st.session_state.pop("celebrate_book")
        st.snow()
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1a2e1f,#243d2a);'
            f'border:1.5px solid #C9A84C; border-radius:16px; padding:1.75rem 2rem;'
            f'text-align:center; margin-bottom:1.5rem; box-shadow:0 8px 32px rgba(201,168,76,0.18);">'
            f'<div style="font-size:28px; margin-bottom:10px;">🦅</div>'
            f'<div style="font-size:20px; font-weight:700; color:#C9A84C; margin-bottom:8px;">'
            f'A tome has been sealed, {safe(name)}!</div>'
            f'<div style="font-size:14px; color:#a8c4b0; line-height:1.6;">'
            f'<strong style="color:#e8d5a3;">"{safe(celebrated)}"</strong> '
            f'now rests among the legends of your chronicle.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="page-title">My Collection</div>'
        '<div class="page-subtitle">Your vaults. Every tome is a chapter in your legend.</div>',
        unsafe_allow_html=True,
    )

    if not books:
        st.markdown(
            f'<div class="empty-state">The vaults are empty, {safe(name)}. '
            f'Venture to <strong>The Scrolls</strong> to discover your first tome.</div>',
            unsafe_allow_html=True,
        )
        return

    reading = lib.get_by_status("reading")
    want    = lib.get_by_status("want")
    read    = lib.get_by_status("read")
    custom  = [b for b in books.values() if getattr(b, "is_custom", False)]

    tab1, tab2, tab3, tab4 = st.tabs([
        f"In Progress ({len(reading)})",
        f"To Acquire ({len(want)})",
        f"Sealed ({len(read)})",
        f"✍️ My Tomes ({len(custom)})",
    ])

    with tab1:
        if not reading:
            st.markdown('<div class="empty-state">No tomes open - the vaults await you.</div>', unsafe_allow_html=True)
        else:
            for b in reading:
                _render_book(lib, b, kind="reading", tab_ctx="t1")

    with tab2:
        if not want:
            st.markdown('<div class="empty-state">No tomes await in the wings.</div>', unsafe_allow_html=True)
        else:
            for b in want:
                _render_book(lib, b, kind="want", tab_ctx="t2")

    with tab3:
        if not read:
            st.markdown('<div class="empty-state">No tomes have been sealed yet.</div>', unsafe_allow_html=True)
        else:
            for b in sorted(read, key=lambda x: x.finish_date or "", reverse=True):
                _render_book(lib, b, kind="read", tab_ctx="t3")

    with tab4:
        st.markdown(
            '<div style="font-size:13px; color:var(--text-muted); margin-bottom:1rem; line-height:1.6;">'
            'Tomes you inscribed yourself. They appear in your collection and rituals.</div>',
            unsafe_allow_html=True,
        )
        if custom:
            for b in custom:
                _render_book(lib, b, kind=b.status, tab_ctx="t4")
        render_add_custom_book(lib, rec)


def _render_book(lib, book, kind: str, tab_ctx: str = ""):
    bid = book.book_id
    real_key = str(bid)
    if getattr(book, "is_custom", False):
        for k, v in lib.get_all().items():
            if v.title == book.title and v.authors == book.authors:
                real_key = k
                break
    key_base = f"book_{real_key}_{kind}_{tab_ctx}" if tab_ctx else f"book_{real_key}_{kind}"

    rating_str   = f"★ {book.avg_rating:.1f}" if book.avg_rating else ""
    pages_str    = f"{book.num_pages} pages"   if book.num_pages  else ""
    meta         = " · ".join(s for s in [rating_str, pages_str] if s)
    rating_stars = ("★" * book.my_rating + "☆" * (5 - book.my_rating)) if book.my_rating else ""
    finish_line  = f"✦ Sealed {safe(book.finish_date)}" if (kind == "read" and book.finish_date) else ""

    is_custom  = getattr(book, "is_custom", False)
    badge      = custom_badge() if is_custom else ""
    emb_status = embedding_status_html(book) if is_custom else ""

    parts = ['<div class="eq-card">']
    parts.append(
        f'<div style="font-size:16px;font-weight:700;color:var(--text);line-height:1.35;">'
        f'{safe(book.title)}{badge}</div>'
    )
    parts.append(f'<div style="font-size:12px;color:var(--text-muted);margin-top:3px;">{safe(book.authors)}</div>')
    if meta:
        parts.append(f'<div style="font-size:11px;color:var(--text-hint);margin-top:6px;">{safe(meta)}</div>')
    if finish_line:
        parts.append(f'<div style="font-size:11px;color:var(--success);font-weight:600;margin-top:4px;">{finish_line}</div>')
    if rating_stars:
        parts.append(f'<div style="font-size:14px;color:var(--warning);margin-top:6px;">{rating_stars}</div>')
    if emb_status:
        parts.append(emb_status)
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)

    with st.expander("Manage this tome"):
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            if kind != "want":
                if st.button("To Acquire", key=f"{key_base}_to_want", use_container_width=True):
                    lib.update_status(real_key, "want")
                    st.rerun()
        with col_s2:
            if kind != "reading":
                if st.button("Open It", key=f"{key_base}_to_read", use_container_width=True):
                    lib.update_status(real_key, "reading")
                    st.rerun()
        with col_s3:
            if kind != "read":
                if st.button("Seal It", key=f"{key_base}_to_done", use_container_width=True):
                    lib.update_status(real_key, "read")
                    st.session_state["celebrate_book"] = book.title
                    st.rerun()

        if kind == "reading":
            st.markdown('<div class="section-heading">Chronicle of Pages</div>', unsafe_allow_html=True)
            col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
            with col_p1:
                total = st.number_input("Total pages", min_value=0,
                                        value=int(book.total_pages or 0), key=f"{key_base}_total")
            with col_p2:
                current = st.number_input("Current page", min_value=0,
                                          value=int(book.current_page or 0), key=f"{key_base}_curr")
            with col_p3:
                st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
                if st.button("Update", key=f"{key_base}_update_pages", use_container_width=True):
                    lib.update_pages(real_key, total, current)
                    st.rerun()

        if kind in ("reading", "read"):
            st.markdown('<div class="section-heading">Your Verdict</div>', unsafe_allow_html=True)
            col_r1, col_r2 = st.columns([3, 1])
            with col_r1:
                new_rating = st.slider("Rating", 0, 5, int(book.my_rating or 0),
                                       key=f"{key_base}_rating", label_visibility="collapsed")
            with col_r2:
                if st.button("Seal", key=f"{key_base}_save_rating", use_container_width=True):
                    lib.update_rating(real_key, new_rating)
                    st.rerun()

        st.markdown('<div class="section-heading">Scholar\'s Notes</div>', unsafe_allow_html=True)
        notes = st.text_area("Notes", value=book.notes or "", key=f"{key_base}_notes",
                             label_visibility="collapsed",
                             placeholder="Your reflections upon this tome…", height=80)
        if st.button("Seal Notes", key=f"{key_base}_save_notes"):
            if not _handle_content(lib, notes):
                lib.update_notes(real_key, notes)
                st.rerun()

        st.markdown('<div class="section-heading">Inscriptions</div>', unsafe_allow_html=True)
        with st.form(f"{key_base}_quote_form"):
            new_q = st.text_area("Inscribe a Passage", placeholder="The line that stirred your soul…",
                                 height=80, key=f"{key_base}_new_quote")
            col_q1, col_q2 = st.columns(2)
            with col_q1:
                page = st.text_input("Page", placeholder="42", key=f"{key_base}_quote_page")
            with col_q2:
                tags_input = st.text_input("Seals (comma-separated)",
                                           placeholder="wisdom, courage",
                                           key=f"{key_base}_quote_tags")
            add_q = st.form_submit_button("Inscribe", use_container_width=True)

        if add_q and new_q.strip():
            if not _handle_content(lib, new_q.strip()):
                tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                ok = lib.add_quote(real_key, new_q.strip(), page=page.strip(), tags=tags)
                if ok:
                    st.rerun()

        if book.quotes:
            st.markdown(
                f'<div style="font-size:12px;color:var(--text-muted);margin:8px 0;">'
                f'{len(book.quotes)} preserved inscription{"s" if len(book.quotes) != 1 else ""}</div>',
                unsafe_allow_html=True,
            )
            for idx, q in enumerate(book.quotes):
                tags_html = "".join(
                    f'<span class="tag-chip">#{safe(t)}</span>' for t in q.tags
                ) if q.tags else ""
                page_label = f" · p.{safe(q.page)}" if q.page else ""
                st.markdown(
                    f'<div class="quote-card" style="margin-bottom:0.5rem;font-size:14px;">'
                    f'"{safe(q.text)}"'
                    f'<div style="font-size:11px;color:var(--text-hint);margin-top:8px;font-style:normal;">'
                    f'{safe(q.date)}{page_label}</div>'
                    f'<div style="margin-top:6px;">{tags_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                col_qa, col_qb = st.columns([4, 1])
                with col_qa:
                    new_tags = st.text_input(
                        "Seals", value=", ".join(q.tags),
                        key=f"{key_base}_q{idx}_tags",
                        label_visibility="collapsed",
                        placeholder="Edit seals (comma-separated)",
                    )
                    if new_tags != ", ".join(q.tags):
                        if st.button("Save seals", key=f"{key_base}_q{idx}_save_tags"):
                            lib.update_quote_tags(real_key, idx, [t.strip() for t in new_tags.split(",") if t.strip()])
                            st.rerun()
                with col_qb:
                    if st.button("Remove", key=f"{key_base}_q{idx}_del", help="Remove inscription"):
                        lib.delete_quote(real_key, idx)
                        st.rerun()

        st.markdown("<hr class='eq-divider'>", unsafe_allow_html=True)
        confirm_key = f"{key_base}_confirm_delete"
        if st.session_state.get(confirm_key):
            st.warning(f"Remove *{book.title}* and all its inscriptions from the vaults? This cannot be undone.")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("Cancel", key=f"{key_base}_cancel_del", use_container_width=True):
                    st.session_state[confirm_key] = False
                    st.rerun()
            with col_d2:
                if st.button("Yes, remove it", key=f"{key_base}_confirm_del", use_container_width=True):
                    lib.delete(real_key)
                    st.session_state[confirm_key] = False
                    st.rerun()
        else:
            if st.button("Remove from Collection", key=f"{key_base}_request_del"):
                st.session_state[confirm_key] = True
                st.rerun()