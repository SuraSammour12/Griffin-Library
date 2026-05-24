# ============================================================
# Griffin Library - Reading Rituals (Sessions)
# ============================================================
# Handles session creation, live timer, and session history.
# Home page has no session controls.
#
# Key functions:
#   _render_start_panel()  - session launcher (free or book)
#   _render_active_panel() - live countdown timer and controls
#   _render_history()      - full session log with filters
# ============================================================

import uuid, json, base64
from datetime import datetime, date, timedelta
import streamlit as st
import streamlit.components.v1 as components
from app.views.components import safe


def _fmt_day(d: date, fmt: str) -> str:
    """strftime wrapper that works on Windows (no %-d support)."""
    import re
    result = d.strftime(fmt)
    result = re.sub(r'(?<= )0(\d)', r'\1', result)
    result = re.sub(r'^0(\d)', r'\1', result)
    return result


# ─────────────────────────────────────────────────────────────
# WALL-CLOCK HELPERS
# ─────────────────────────────────────────────────────────────

def _compute_elapsed(sess: dict) -> float:
    if sess.get("paused"):
        return float(sess.get("elapsed_saved", 0))
    try:
        resume_iso = sess.get("resume_time") or sess.get("start_time")
        resume_dt  = datetime.fromisoformat(resume_iso)
        live_sec   = (datetime.now() - resume_dt).total_seconds()
        return float(sess.get("elapsed_saved", 0)) + live_sec
    except Exception:
        return float(sess.get("elapsed_saved", 0))


def _save_session_to_url(sess: dict):
    try:
        st.query_params["eq_sess"] = base64.urlsafe_b64encode(
            json.dumps(sess).encode()).decode()
    except Exception:
        pass


def _clear_session_url():
    for k in ["eq_sess", "eq_action", "eq_elapsed", "eq_pages",
              "eq_newpage", "eq_book_id", "eq_t"]:
        try:
            st.query_params.pop(k, None)
        except Exception:
            pass


def _load_session_from_url() -> dict | None:
    try:
        enc = st.query_params.get("eq_sess")
        if not enc:
            return None
        return json.loads(base64.urlsafe_b64decode(enc.encode()).decode())
    except Exception:
        return None


def _sync_sessions_log(lib):
    try:
        st.session_state["sessions_log"] = lib.get_sessions_log() or {}
    except Exception:
        st.session_state["sessions_log"] = {}


def _pbar(pct: float, color: str = "var(--ink,#1E3A2F)") -> str:
    pct = max(0, min(100, int(pct)))
    return (
        f'<div style="background:var(--border,#E8DFCC);border-radius:99px;'
        f'height:6px;width:100%;margin-top:6px;">'
        f'<div style="background:{color};height:6px;border-radius:99px;'
        f'width:{pct}%;transition:width 0.5s ease;"></div></div>'
    )


# ─────────────────────────────────────────────────────────────
# SESSION ACTIONS
# ─────────────────────────────────────────────────────────────

def _action_cancel():
    st.session_state["active_session"]  = None
    st.session_state["_sess_finishing"] = False
    for k in ["_sess_confirm_stop", "_sess_new_page"]:
        st.session_state.pop(k, None)
    _clear_session_url()
    st.rerun()


def _action_pause(sess: dict, elapsed_sec: float):
    sess["elapsed_saved"] = elapsed_sec
    sess["paused"]        = True
    sess.pop("resume_time", None)
    st.session_state["active_session"] = sess
    _save_session_to_url(sess)
    st.rerun()


def _action_resume(sess: dict):
    sess["paused"]      = False
    sess["resume_time"] = datetime.now().isoformat()
    st.session_state["active_session"] = sess
    _save_session_to_url(sess)
    st.rerun()


def _action_finish(sess: dict, elapsed_sec: float):
    sess["elapsed_saved"]               = elapsed_sec
    st.session_state["active_session"]  = sess
    st.session_state["_sess_finishing"] = True
    st.rerun()


def _call_update_sessions_log(lib, today, elapsed_min, pages_read,
                              session_type, book_id, book_title,
                              start_page, end_page, time_str=""):
    """Persist to lib. Fire-and-forget - display never depends on this."""
    try:
        lib.update_sessions_log(
            today, elapsed_min, pages_read,
            session_type=session_type,
            book_id=book_id, book_title=book_title,
            start_page=start_page, end_page=end_page,
            time_str=time_str,
        )
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# CANONICAL SESSION STORE
# ─────────────────────────────────────────────────────────────
# Architecture:
#   _SS_KEY   = list of session entry dicts, newest first
#   _SS_READY = bool flag, True once bootstrap has run
#
# Rules:
#  • _ss_add_entry()  - ONLY writer for new sessions, sets _SS_READY=True
#  • _ss_bootstrap()  - ONE-TIME historical load, guarded by _SS_READY flag
#  • _ss_all()        - reader, always returns copy from session_state
#
# This guarantees: once an entry is added, it can NEVER be overwritten
# by a bootstrap call, regardless of what lib returns.
# ─────────────────────────────────────────────────────────────

_SS_KEY   = "_griffin_sessions"
_SS_READY = "_griffin_sessions_ready"


def _ss_add_entry(entry: dict):
    """
    Add a new session entry. Always works, always visible on next render.
    Sets _SS_READY=True so bootstrap can never overwrite these entries.
    """
    existing = list(st.session_state.get(_SS_KEY, []))
    existing.insert(0, dict(entry))          # newest first
    st.session_state[_SS_KEY]   = existing
    st.session_state[_SS_READY] = True       # lock bootstrap out


def _ss_bootstrap(lib):
    """
    Load historical entries from lib on first page visit.
    Completely skipped if _SS_READY is True (i.e. after any save).
    """
    if st.session_state.get(_SS_READY):
        return

    entries = []
    try:
        # Use get_sessions_log() - always available on both Library and DemoLibrary
        log = lib.get_sessions_log() or {}
        for date_str, day in sorted(log.items(), reverse=True):
            if not isinstance(day, dict):
                continue
            for e in day.get("entries", []):
                ent = dict(e)
                ent["date"] = date_str
                entries.append(ent)
        entries.sort(
            key=lambda e: (e.get("date", ""), e.get("time", "")),
            reverse=True,
        )
    except Exception:
        entries = []

    entries.sort(key=lambda e: (e.get("date", ""), e.get("time", "")), reverse=True)
    st.session_state[_SS_KEY]   = entries
    st.session_state[_SS_READY] = True   # mark done so we never re-run


def _ss_all() -> list:
    """Return all session entries, newest first. Safe to call anywhere."""
    return list(st.session_state.get(_SS_KEY, []))


def _update_book_pages(lib, book_id_str: str, new_page: int):
    """Update book progress. Returns (book_title, pages_read).
    Works for both catalog books and custom-added books.
    """
    book_title, pages_read = "", 0
    if not book_id_str:
        return book_title, pages_read
    try:
        # lib.get() works for both numeric and custom string IDs
        b = lib.get(book_id_str)
        if b is None and book_id_str.isdigit():
            b = lib.get(int(book_id_str))
        if b is not None:
            start_p    = int(b.current_page or 0)
            pages_read = max(0, new_page - start_p)
            book_title = b.title
            # Use book_id_str directly - b.book_id may be 0 for custom books
            # (schemas.py defines book_id as int, custom IDs like "custom_123" become 0)
            current_total = int(b.total_pages or 0)
            new_total     = max(current_total, new_page)
            lib.update_pages(book_id_str, new_total, new_page)
    except Exception:
        pass
    return book_title, pages_read


def _action_save_free(lib, sess: dict, elapsed_sec: float):
    import uuid as _uuid
    elapsed_min = max(1, int(elapsed_sec / 60))
    today       = date.today().isoformat()
    now_str     = datetime.now().strftime("%H:%M")

    entry = {
        "id":           str(_uuid.uuid4())[:8],
        "date":         today,
        "time":         now_str,
        "type":         "free",
        "book_id":      "",
        "book_title":   "",
        "duration_min": elapsed_min,
        "pages_read":   0,
        "start_page":   0,
        "end_page":     0,
        "note":         "",
    }

    _ss_add_entry(entry)                           # canonical store first
    _call_update_sessions_log(                     # lib persistence second
        lib, today, elapsed_min, 0,
        session_type="free",
        book_id="", book_title="",
        start_page=0, end_page=0,
        time_str=now_str,
    )
    try:
        lib.touch_streak()
    except Exception:
        pass
    _sync_sessions_log(lib)

    st.session_state["active_session"]  = None
    st.session_state["_sess_finishing"] = False
    st.session_state.pop("_sess_confirm_stop", None)
    _clear_session_url()
    st.session_state["_done_msg"] = {
        "text":   f"🌿 {elapsed_min} min logged!",
        "detail": "Streak updated ✓",
    }
    st.rerun()


def _action_save_book(lib, sess: dict, elapsed_sec: float,
                      new_page: int, update_page: bool):
    import uuid as _uuid
    elapsed_min = max(1, int(elapsed_sec / 60))
    today       = date.today().isoformat()
    now_str     = datetime.now().strftime("%H:%M")
    book_id_str = str(sess.get("book_id", ""))
    start_p     = int(sess.get("starting_page", 0))
    book_title  = sess.get("book_title", "")
    pages_read, end_page = 0, start_p

    if update_page and book_id_str:
        title_from_lib, _ = _update_book_pages(lib, book_id_str, new_page)
        if title_from_lib:
            book_title = title_from_lib
        pages_read = max(0, new_page - start_p)
        end_page   = new_page

    entry = {
        "id":           str(_uuid.uuid4())[:8],
        "date":         today,
        "time":         now_str,
        "type":         "book",
        "book_id":      book_id_str,
        "book_title":   book_title,
        "duration_min": elapsed_min,
        "pages_read":   pages_read,
        "start_page":   start_p,
        "end_page":     end_page,
        "note":         "",
    }

    _ss_add_entry(entry)                           # canonical store first
    _call_update_sessions_log(                     # lib persistence second
        lib, today, elapsed_min, pages_read,
        session_type="book",
        book_id=book_id_str, book_title=book_title,
        start_page=start_p, end_page=end_page,
        time_str=now_str,
    )
    try:
        lib.touch_streak()
    except Exception:
        pass
    _sync_sessions_log(lib)

    st.session_state["active_session"]  = None
    st.session_state["_sess_finishing"] = False
    st.session_state.pop("_sess_confirm_stop", None)
    _clear_session_url()
    detail = "Progress updated in My Library ✓" if update_page and pages_read > 0 else "Time logged ✓"
    st.session_state["_done_msg"] = {
        "text":   f"🎉 {elapsed_min} min · {pages_read} pages saved!" if pages_read else f"🎉 {elapsed_min} min saved!",
        "detail": detail,
    }
    st.rerun()


def _launch(is_free: bool, book_id: str, book_title: str, duration: int,
            starting_page: int = 0):
    now  = datetime.now()
    name = st.session_state.get("_owner_name", "")
    sess = {
        "session_id":       str(uuid.uuid4()),
        "book_id":          book_id,
        "book_title":       book_title,
        "is_free":          is_free,
        "start_time":       now.isoformat(),
        "resume_time":      now.isoformat(),
        "duration_minutes": duration,
        "paused":           False,
        "elapsed_saved":    0.0,
        "starting_page":    starting_page,
        "_owner":           name,
    }
    st.session_state["active_session"]  = sess
    st.session_state["_sess_finishing"] = False
    try:
        enc = base64.urlsafe_b64encode(json.dumps(sess).encode()).decode()
        st.query_params["eq_sess"] = enc
    except Exception:
        pass
    st.rerun()


# ─────────────────────────────────────────────────────────────
# TIMER DISPLAY (cosmetic HTML component)
# ─────────────────────────────────────────────────────────────

def _render_timer_display(remaining_sec: float, elapsed_sec: float,
                          dur_sec: int, is_paused: bool,
                          title: str, dur_lbl: str):
    rem   = max(0, remaining_sec)
    pct   = min(100, int(elapsed_sec / dur_sec * 100)) if dur_sec > 0 else 0
    urg   = 0 < rem <= 60
    done  = rem == 0
    state = "done" if done else ("paused" if is_paused else "running")

    components.html(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0;
   font-family:'Inter','Segoe UI',system-ui,sans-serif;}}
html,body{{background:transparent;overflow:hidden;}}
.wrap{{padding:6px 0 10px;}}
.hdr{{display:flex;justify-content:space-between;align-items:center;
      margin-bottom:16px;}}
.htitle{{font-size:13px;font-weight:700;color:#1A1612;
         max-width:280px;overflow:hidden;
         white-space:nowrap;text-overflow:ellipsis;}}
.hbadge{{background:#E8F0EC;color:#1E3A2F;border-radius:20px;
         padding:3px 12px;font-size:12px;font-weight:700;flex-shrink:0;}}
.tmr{{text-align:center;font-size:72px;font-weight:900;
      font-variant-numeric:tabular-nums;letter-spacing:-3px;
      line-height:1;margin:0 0 6px;transition:color 0.4s;}}
.running{{color:#1E3A2F;}}.paused{{color:#888;}}
.urgent{{color:#B83232;animation:blink 1s ease-in-out infinite;}}
.done-state{{color:#2A7A4B;font-size:48px;}}
.sts{{text-align:center;font-size:11px;color:#A8998C;
      letter-spacing:1.5px;text-transform:uppercase;
      font-weight:600;margin-bottom:12px;min-height:16px;}}
.track{{height:6px;background:#EDE8DF;border-radius:99px;overflow:hidden;}}
.fill{{height:100%;border-radius:99px;transition:width 0.5s linear;
       background:linear-gradient(90deg,#1E3A2F,#3B6E52);}}
.fill.urgent{{background:linear-gradient(90deg,#B83232,#EF4444);}}
.fill.done-fill{{background:linear-gradient(90deg,#2A7A4B,#34D399);}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
</style></head><body><div class="wrap">
<div class="hdr">
  <div class="htitle">{safe(title)}</div>
  <div class="hbadge">{safe(dur_lbl)}</div>
</div>
<div class="tmr {
    'done-state' if done else 'urgent' if urg else 'paused' if is_paused else 'running'
}" id="tmr">{"DONE" if done else f"{int(rem//60):02d}:{int(rem%60):02d}"}</div>
<div class="sts" id="sts">{"Done!" if done else "Paused" if is_paused else "remaining"}</div>
<div class="track">
  <div class="fill {'urgent' if urg else 'done-fill' if done else ''}"
       id="fill" style="width:{pct}%"></div>
</div>
</div>
<script>
var TOTAL={int(dur_sec)},REM0={rem:.3f},startMs=performance.now(),raf;
function pad(n){{return String(Math.floor(n)).padStart(2,'0');}}
function fmt(s){{return pad(s/60)+':'+pad(s%60);}}
function tick(){{
  var rem=Math.max(0,REM0-(performance.now()-startMs)/1000);
  var pct=Math.min(100,(TOTAL-rem)/TOTAL*100);
  var urg=rem>0&&rem<=60,done=rem===0;
  var t=document.getElementById('tmr'),f=document.getElementById('fill'),s=document.getElementById('sts');
  if(t)t.textContent=done?'DONE':fmt(rem);
  if(t)t.className='tmr '+(done?'done-state':urg?'urgent':'running');
  if(f)f.style.width=pct+'%';
  if(f)f.className='fill '+(done?'done-fill':urg?'urgent':'');
  if(s)s.textContent=done?'Done!':'remaining';
  if(!done)raf=requestAnimationFrame(tick);
}}
{'// Paused — no animation' if is_paused or done else 'raf=requestAnimationFrame(tick);'}
</script></body></html>""", height=148, scrolling=False)


# ─────────────────────────────────────────────────────────────
# ACTIVE SESSION PANEL
# ─────────────────────────────────────────────────────────────

def _render_active_panel(sess: dict, lib):
    try:
        from streamlit_autorefresh import st_autorefresh  # type: ignore[import]
        st_autorefresh(interval=30_000, limit=None, key="sess_autorefresh")
    except ImportError:
        pass

    dur_sec     = int(sess["duration_minutes"]) * 60
    elapsed_sec = _compute_elapsed(sess)
    remaining   = max(0.0, dur_sec - elapsed_sec)
    is_paused   = sess.get("paused", False)
    is_free     = sess.get("is_free", True)
    title       = ("🌿 Free Reading Session"
                   if is_free else f"📚 {sess.get('book_title','')}")
    dur_lbl     = f"{sess['duration_minutes']} min"
    elapsed_min = max(1, int(elapsed_sec / 60))
    start_p     = int(sess.get("starting_page", 0))

    # Resolve total pages for book sessions
    book_id_str = str(sess.get("book_id", ""))
    total_pages = max(start_p + 1, 1)
    if book_id_str:
        try:
            b = lib.get(book_id_str)
            if b is None and book_id_str.isdigit():
                b = lib.get(int(book_id_str))
            if b:
                total_pages = max(int(b.total_pages or 0), start_p + 1)
        except Exception:
            pass

    finishing = st.session_state.get("_sess_finishing", False)
    is_done   = remaining <= 0

    # ── Completion / save screen ──────────────────────────────
    if finishing or is_done:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#E8F0EC,#D8E8DE);'
            f'border:1.5px solid rgba(30,58,47,0.25);border-radius:16px;'
            f'padding:1.5rem 1.75rem;margin-bottom:1.25rem;">'
            f'<div style="font-size:32px;text-align:center;margin-bottom:8px;">🎉</div>'
            f'<div style="font-size:20px;font-weight:800;color:#1E3A2F;'
            f'text-align:center;margin-bottom:4px;">'
            f'{"A worthy ritual!" if is_free else "The ritual is complete!"}</div>'
            f'<div style="font-size:14px;color:#3B6E52;text-align:center;">'
            f'You studied for <strong>{elapsed_min} min</strong>.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        if is_free:
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅  Save session", key="fs_save_free",
                             use_container_width=True, type="primary"):
                    _action_save_free(lib, sess, elapsed_sec)
            with c2:
                if st.button("Discard", key="fs_discard",
                             use_container_width=True):
                    _action_cancel()
        else:
            st.markdown(
                f'<div style="font-size:14px;font-weight:700;'
                f'color:var(--text,#1A1612);margin:1rem 0 4px;">'
                f'Where did the tome fall open last?</div>'
                f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);'
                f'margin-bottom:8px;">Your vigil began at page <strong>{start_p}</strong></div>',
                unsafe_allow_html=True,
            )
            # Remove upper limit for custom books where total_pages may be 0 or 1
            _safe_max = total_pages if total_pages > max(start_p + 1, 10) else 99999
            _safe_val = max(start_p, min(
                int(st.session_state.get("_sess_new_page", start_p)), _safe_max
            ))
            new_pg = st.number_input(
                "Page reached",
                min_value=0, max_value=_safe_max,
                value=_safe_val,
                step=1, key="fs_page_input",
                label_visibility="collapsed",
            )
            st.session_state["_sess_new_page"] = int(new_pg)
            st.caption("📜 Your progress in My Collection updates when you seal the ritual.")

            c1, c2, c3 = st.columns([2, 2, 1])
            with c1:
                if st.button("🦅  Seal the Ritual", key="fs_save_pg",
                             use_container_width=True, type="primary"):
                    _action_save_book(lib, sess, elapsed_sec,
                                      int(new_pg), update_page=True)
            with c2:
                if st.button("Record Time Only", key="fs_log_only",
                             use_container_width=True):
                    _action_save_book(lib, sess, elapsed_sec,
                                      start_p, update_page=False)
            with c3:
                if st.button("Discard", key="fs_discard_book",
                             use_container_width=True):
                    _action_cancel()
        return

    # ── Live timer ────────────────────────────────────────────
    _render_timer_display(
        remaining_sec=remaining,
        elapsed_sec=elapsed_sec,
        dur_sec=dur_sec,
        is_paused=is_paused,
        title=title,
        dur_lbl=dur_lbl,
    )

    c_stop, c_pause, c_done = st.columns([1, 1, 1.5])
    with c_stop:
        if st.button("⏹  Stop", key="sess_stop",
                     use_container_width=True,
                     help="Discard this session — it will not be saved"):
            st.session_state["_sess_confirm_stop"] = True
            st.rerun()
    with c_pause:
        if is_paused:
            if st.button("▶  Resume", key="sess_resume", use_container_width=True):
                _action_resume(sess)
        else:
            if st.button("⏸  Pause", key="sess_pause", use_container_width=True):
                _action_pause(sess, elapsed_sec)
    with c_done:
        if st.button("✅  Finish", key="sess_finish",
                     use_container_width=True, type="primary"):
            _action_finish(sess, elapsed_sec)

    if st.session_state.get("_sess_confirm_stop"):
        st.warning(
            f"**Stop session?** You've read for **{elapsed_min} min**. "
            "This will **not** be saved."
        )
        ka, kb = st.columns(2)
        with ka:
            if st.button("Keep reading", key="sess_keep",
                         use_container_width=True, type="primary"):
                st.session_state["_sess_confirm_stop"] = False
                st.rerun()
        with kb:
            if st.button("Stop & discard", key="sess_discard",
                         use_container_width=True):
                _action_cancel()


# ─────────────────────────────────────────────────────────────
# START PANEL  (no active session)
# ─────────────────────────────────────────────────────────────

def _render_start_panel(lib):
    st.markdown(
        '<div style="background:var(--surface,#fff);'
        'border:1px solid var(--border,#E2DAD0);border-radius:18px;'
        'padding:1.75rem 2rem;margin-bottom:1rem;">'
        '<div style="font-size:16px;font-weight:700;color:var(--text,#1A1612);'
        'margin-bottom:4px;">Begin a Reading Ritual</div>'
        '<div style="font-size:13px;color:var(--text-muted,#6A5F54);'
        'margin-bottom:1.5rem;">Choose your ritual and light the candle. Your journey awaits.</div>',
        unsafe_allow_html=True,
    )

    col_free, col_book = st.columns(2, gap="medium")

    # ── Open Vigil ──────────────────────────────────────────
    with col_free:
        st.markdown(
            '<div style="background:var(--surface,#FAFAF8);'
            'border:1.5px solid var(--border,#E2DAD0);border-radius:14px;'
            'padding:1.25rem;margin-bottom:0.75rem;">'
            '<div style="font-size:24px;margin-bottom:8px;">🌿</div>'
            '<div style="font-size:14px;font-weight:700;color:var(--text,#1A1612);'
            'margin-bottom:4px;">Open Vigil</div>'
            '<div style="font-size:12px;color:var(--text-muted,#6A5F54);">'
            'Free exploration — no tome required.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        dur_free = st.select_slider(
            "Duration",
            options=[15, 20, 25, 30, 45, 60, 90],
            value=25,
            format_func=lambda x: f"{x} min",
            key="qs_free_dur",
            label_visibility="collapsed",
        )
        if st.button("▶  Start Open Vigil", key="qs_free",
                     use_container_width=True, type="primary"):
            _launch(is_free=True, book_id="", book_title="",
                    duration=dur_free)

    # ── Bound Ritual ──────────────────────────────────────────
    with col_book:
        st.markdown(
            '<div style="background:var(--surface,#FAFAF8);'
            'border:1.5px solid var(--border,#E2DAD0);border-radius:14px;'
            'padding:1.25rem;margin-bottom:0.75rem;">'
            '<div style="font-size:24px;margin-bottom:8px;">📚</div>'
            '<div style="font-size:14px;font-weight:700;color:var(--text,#1A1612);'
            'margin-bottom:4px;">Bound Ritual</div>'
            '<div style="font-size:12px;color:var(--text-muted,#6A5F54);">'
            'Bound to a tome in your vaults.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        reading_books = lib.get_by_status("reading")

        if reading_books:
            book_map     = {b.title: b for b in reading_books}
            chosen_title = st.selectbox(
                "Book", list(book_map.keys()),
                key="qs_book_select",
                label_visibility="collapsed",
            )
            dur_book = st.select_slider(
                "Duration",
                options=[15, 20, 25, 30, 45, 60, 90],
                value=25,
                format_func=lambda x: f"{x} min",
                key="qs_book_dur",
                label_visibility="collapsed",
            )
            chosen_book = book_map[chosen_title]
            if st.button("▶  Start Bound Ritual", key="qs_book",
                         use_container_width=True, type="primary"):
                # Find the real storage key for this book.
                # Cannot use "v is chosen_book" - after reload objects differ.
                # Match by title+author (unique enough for a user's library).
                _real_bid = None
                for _k, _v in lib.get_all().items():
                    if (_v.title == chosen_book.title and
                            _v.authors == chosen_book.authors):
                        _real_bid = _k
                        break
                if _real_bid is None:
                    # Last resort: use book_id if it's a catalog book
                    _real_bid = str(chosen_book.book_id)
                _fresh = lib.get(_real_bid)
                _start = int((_fresh.current_page if _fresh else chosen_book.current_page) or 0)
                _launch(is_free=False,
                        book_id=_real_bid,
                        book_title=chosen_book.title,
                        duration=dur_book,
                        starting_page=_start)
        else:
            st.markdown(
                '<div style="font-size:12px;color:var(--text-muted,#6A5F54);'
                'padding:0.5rem 0;">No tomes are open in your vaults.<br>'
                'Open a tome in My Collection first.</div></div>',
                unsafe_allow_html=True,
            )
            # Spacer to match the select_slider height on the left column
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            # Inject CSS to make THIS specific disabled button look like a primary button
            st.markdown("""
            <style>
            button[kind="secondary"][disabled]#qs_book_dis,
            [data-testid="stButton"]:has(button[disabled]) button {
                background: #1E3A2F !important;
                color: #FFFFFF !important;
                border-color: #1E3A2F !important;
                box-shadow: 0 2px 8px rgba(30,58,47,0.15) !important;
                opacity: 0.45 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            st.button(
                "▶  Start Bound Ritual",
                key="qs_book_dis",
                use_container_width=True,
                disabled=True,
                type="primary",
            )

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# HISTORY DASHBOARD
# ─────────────────────────────────────────────────────────────

def _entries_from_log(lib) -> list:
    """Return all entries. Bootstrap runs once; after that reads clean store."""
    _ss_bootstrap(lib)
    return _ss_all()


def _render_history(lib):
    all_entries = _entries_from_log(lib)

    st.markdown(
        '<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
        'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:1rem;">'
        'Chronicle of Rituals</div>',
        unsafe_allow_html=True,
    )

    # ── Summary strip ─────────────────────────────────────────
    if all_entries:
        total_min   = sum(e.get("duration_min", 0) for e in all_entries)
        total_pages = sum(e.get("pages_read", 0)   for e in all_entries)
        h, m        = divmod(total_min, 60)
        time_str    = f"{h}h {m}m" if h else f"{m}m"
        avg         = round(total_min / len(all_entries)) if all_entries else 0
        book_cnt    = sum(1 for e in all_entries if e.get("type") == "book")
        free_cnt    = len(all_entries) - book_cnt

        cols = st.columns(5)
        stats_data = [
            (str(len(all_entries)), "Sessions"),
            (time_str, "Total time"),
            (str(avg) + "m", "Avg Vigil"),
            (str(total_pages) if total_pages else "—", "Pages Traversed"),
            (f"{book_cnt} 📚 · {free_cnt} 🌿", "Ritual Types"),
        ]
        for col, (val, label) in zip(cols, stats_data):
            with col:
                st.markdown(
                    f'<div style="background:var(--surface,#fff);'
                    f'border:1px solid var(--border,#E2DAD0);'
                    f'border-radius:12px;padding:0.75rem 0.9rem;text-align:center;">'
                    f'<div style="font-size:16px;font-weight:800;'
                    f'color:var(--text,#1A1612);line-height:1.1;">{safe(val)}</div>'
                    f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
                    f'text-transform:uppercase;letter-spacing:0.8px;margin-top:3px;'
                    f'font-weight:600;">{safe(label)}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # ── Empty state ───────────────────────────────────────────
    if not all_entries:
        st.markdown(
            '<div style="background:var(--surface,#fff);'
            'border:1px solid var(--border,#E2DAD0);border-radius:14px;'
            'padding:2.5rem;text-align:center;">'
            '<div style="font-size:32px;margin-bottom:0.75rem;">📖</div>'
            '<div style="font-size:14px;font-weight:600;color:var(--text,#1A1612);'
            'margin-bottom:6px;">No rituals recorded yet</div>'
            '<div style="font-size:13px;color:var(--text-muted,#6A5F54);">'
            'Begin a ritual above — your deeds are recorded for eternity.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Pre-define filter defaults (BEFORE expander, avoids NameError) ────
    search_q    = ""
    book_filter = "All books"
    type_filter = "All types"
    sort_opt    = "Newest first"

    # ── Filters ───────────────────────────────────────────────
    with st.expander("🔍  Filter & Sort", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 1.5, 1.5])
        with fc1:
            search_q = st.text_input(
                "Search", placeholder="book title or date…",
                key="sh_search", label_visibility="collapsed")
        with fc2:
            all_book_titles = sorted(set(
                e.get("book_title", "") for e in (all_entries or [])
                if e.get("book_title")
            ))
            book_filter = st.selectbox(
                "Book", ["All books"] + all_book_titles,
                key="sh_book", label_visibility="collapsed")
        with fc3:
            type_filter = st.selectbox(
                "Type", ["All types", "📚 Book", "🌿 Free"],
                key="sh_type", label_visibility="collapsed")
        with fc4:
            sort_opt = st.selectbox(
                "Sort", ["Newest first", "Oldest first",
                         "Longest first", "Shortest first"],
                key="sh_sort", label_visibility="collapsed")

    # ── Apply filters ─────────────────────────────────────────
    filtered = list(all_entries)
    if search_q.strip():
        sq = search_q.strip().lower()
        filtered = [
            e for e in filtered
            if sq in e.get("date", "").lower()
            or sq in e.get("book_title", "").lower()
        ]
    if book_filter and book_filter != "All books":
        filtered = [e for e in filtered if e.get("book_title") == book_filter]
    if type_filter == "📚 Book":
        filtered = [e for e in filtered if e.get("type") == "book"]
    elif type_filter == "🌿 Free":
        filtered = [e for e in filtered if e.get("type") == "free"]

    reverse = sort_opt in ("Newest first", "Longest first")
    if "Longest" in sort_opt or "Shortest" in sort_opt:
        filtered.sort(key=lambda e: e.get("duration_min", 0), reverse=reverse)
    else:
        filtered.sort(
            key=lambda e: (e.get("date", ""), e.get("time", "")),
            reverse=reverse,
        )

    if len(filtered) != len(all_entries):
        st.markdown(
            f'<div style="font-size:12px;color:var(--text-muted,#6A5F54);'
            f'margin-bottom:0.75rem;">'
            f'Showing <strong>{len(filtered)}</strong> of {len(all_entries)} sessions</div>',
            unsafe_allow_html=True,
        )

    # ── Rows grouped by date ──────────────────────────────────
    today_d     = date.today()
    yesterday_d = today_d - timedelta(days=1)
    last_date   = None

    for entry in filtered:
        date_str = entry.get("date", "")
        try:
            d = date.fromisoformat(date_str)
            if d == today_d:       day_lbl = "Today"
            elif d == yesterday_d: day_lbl = "Yesterday"
            else:                  day_lbl = _fmt_day(d, "%A, %B %d, %Y")
        except Exception:
            day_lbl = date_str
            d = None

        if date_str != last_date:
            is_today_div = (d == today_d) if d else False
            st.markdown(
                f'<div style="font-size:11px;font-weight:700;'
                f'color:{"var(--ink,#1E3A2F)" if is_today_div else "var(--text-hint,#A8998C)"};'
                f'text-transform:uppercase;letter-spacing:1.5px;'
                f'padding:0.75rem 0 0.4rem;border-top:1px solid var(--border,#E2DAD0);'
                f'margin-top:{"0" if last_date is None else "0.5rem"};">'
                f'{safe(day_lbl)}</div>',
                unsafe_allow_html=True,
            )
            last_date = date_str

        _render_session_row(lib, entry, date_str)


def _render_session_row(lib, entry: dict, date_str: str):
    is_book    = entry.get("type") == "book"
    icon       = "📚" if is_book else "🌿"
    dur        = entry.get("duration_min", 0)
    pages      = entry.get("pages_read", 0)
    bk_title   = entry.get("book_title", "")
    t_start    = entry.get("time", "")
    sid        = entry.get("id", "")
    note       = entry.get("note", "")
    start_page = entry.get("start_page", 0)
    end_page   = entry.get("end_page", 0)

    # Compute end time from start + duration
    try:
        if t_start:
            dt_s       = datetime.strptime(f"{date_str} {t_start}", "%Y-%m-%d %H:%M")
            dt_e       = dt_s + timedelta(minutes=dur)
            time_range = f"{dt_s.strftime('%H:%M')} – {dt_e.strftime('%H:%M')}"
        else:
            time_range = ""
    except Exception:
        time_range = t_start

    # Pages detail
    if is_book and end_page > start_page and pages > 0:
        pages_detail = f"p.{start_page} → {end_page} ({pages} pages)"
    elif pages > 0:
        pages_detail = f"{pages} pages read"
    else:
        pages_detail = ""

    book_label  = safe(bk_title) if is_book and bk_title else "Free reading"
    type_label  = "Bound Ritual" if is_book else "Open Vigil"
    unique_key  = f"srow_{sid or (date_str + str(dur) + str(t_start))}"

    # ── Card ──────────────────────────────────────────────────
    chips_html = ""
    if time_range:
        chips_html += (
            f'<span style="font-size:10.5px;background:rgba(30,58,47,0.08);'
            f'color:var(--ink,#1E3A2F);border-radius:100px;padding:2px 9px;'
            f'margin-right:5px;font-weight:600;">{safe(time_range)}</span>'
        )
    if pages_detail:
        chips_html += (
            f'<span style="font-size:10.5px;background:var(--accent-soft,#EBF5F0);'
            f'color:var(--ink,#1E3A2F);border-radius:100px;padding:2px 9px;'
            f'margin-right:5px;font-weight:600;">{safe(pages_detail)}</span>'
        )
    type_chip = (
        f'<span style="font-size:10.5px;background:rgba(0,0,0,0.04);'
        f'color:var(--text-muted,#6A5F54);border-radius:100px;padding:2px 9px;'
        f'font-weight:600;">{icon} {safe(type_label)}</span>'
    )
    note_html = (
        f'<div style="font-size:12px;color:var(--text-hint,#A8998C);'
        f'font-style:italic;margin-top:8px;padding-top:8px;'
        f'border-top:1px solid var(--border,#E2DAD0);">"{safe(note)}"</div>'
    ) if note else ""

    st.markdown(
        f'<div style="background:var(--surface,#fff);'
        f'border:1px solid var(--border,#E2DAD0);border-radius:14px;'
        f'padding:1rem 1.25rem;margin-bottom:0.5rem;">'
        f'<div style="display:flex;justify-content:space-between;'
        f'align-items:flex-start;gap:0.75rem;">'
        f'<div style="flex:1;min-width:0;">'
        f'<div style="font-size:14px;font-weight:700;color:var(--text,#1A1612);'
        f'margin-bottom:5px;">{safe(book_label)}</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:4px;">'
        f'{chips_html}{type_chip}</div>'
        f'{note_html}'
        f'</div>'
        f'<div style="text-align:right;flex-shrink:0;">'
        f'<div style="font-size:22px;font-weight:900;'
        f'color:var(--ink,#1E3A2F);line-height:1;">{dur}</div>'
        f'<div style="font-size:10px;color:var(--text-hint,#A8998C);'
        f'font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">min</div>'
        f'</div></div></div>',
        unsafe_allow_html=True,
    )

    with st.expander("Edit / Delete", expanded=False):
        new_note = st.text_area(
            "Chronicle Note",
            value=note,
            placeholder="Describe your study. What was revealed to you?",
            height=72,
            key=f"note_{unique_key}",
            label_visibility="collapsed",
        )
        cs, cd = st.columns([3, 1])
        with cs:
            if st.button("Save note", key=f"snote_{unique_key}",
                         use_container_width=True):
                try:
                    lib.update_session_note(date_str, sid, new_note)
                    st.rerun()
                except Exception:
                    st.error("Could not save note.")
        with cd:
            if st.button("Delete", key=f"del_{unique_key}",
                         use_container_width=True):
                st.session_state[f"cdel_{unique_key}"] = True
                st.rerun()

        if st.session_state.get(f"cdel_{unique_key}"):
            st.warning("Erase this ritual from the chronicle forever?")
            ca, cb = st.columns(2)
            with ca:
                if st.button("Cancel", key=f"dno_{unique_key}",
                             use_container_width=True):
                    st.session_state.pop(f"cdel_{unique_key}", None)
                    st.rerun()
            with cb:
                if st.button("Yes, delete", key=f"dyes_{unique_key}",
                             use_container_width=True):
                    try:
                        lib.delete_session_entry(date_str, sid)
                    except Exception:
                        pass
                    st.session_state.pop(f"cdel_{unique_key}", None)
                    st.rerun()


# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────

def render(lib):
    current_name = lib.get_name() or ""

    # ── Clear stale session store if the user changed ─────────
    # When a new user logs in, _griffin_sessions still holds the
    # previous user's entries. Detect the change and wipe everything
    # so the new user starts with a clean slate loaded from their own lib.
    last_sess_owner = st.session_state.get("_sess_owner")
    if last_sess_owner and last_sess_owner != current_name:
        st.session_state.pop(_SS_KEY,   None)
        st.session_state.pop(_SS_READY, None)
        st.session_state.pop("active_session",  None)
        st.session_state.pop("_sess_finishing", None)
        st.session_state.pop("_sess_new_page",  None)
        st.session_state.pop("_sess_confirm_stop", None)
        _clear_session_url()
    st.session_state["_sess_owner"] = current_name

    # Restore active session from URL after browser refresh
    if not st.session_state.get("active_session"):
        saved = _load_session_from_url()
        if saved:
            if saved.get("_owner") and saved["_owner"] != current_name:
                _clear_session_url()
            else:
                st.session_state["active_session"]  = saved
                st.session_state["_sess_finishing"] = False

    # Bootstrap historical entries once (no-op after first save)
    _ss_bootstrap(lib)

    # Sync the sessions_log cache (used by home page streak dots)
    _sync_sessions_log(lib)

    # Store owner name for new sessions
    st.session_state["_owner_name"] = current_name

    st.markdown(
        '<div class="page-title">Reading Rituals</div>'
        '<div class="page-subtitle">'
        'Begin a Reading Ritual or browse your full history.</div>',
        unsafe_allow_html=True,
    )

    # Done message
    done_msg = st.session_state.pop("_done_msg", None)
    if done_msg:
        st.success(f"**{done_msg['text']}**  \n{done_msg['detail']}")

    active = st.session_state.get("active_session")

    if active:
        # Active session: show a minimal "currently running" header + timer
        st.markdown(
            '<div style="font-size:11px;font-weight:700;color:var(--text-hint,#A8998C);'
            'text-transform:uppercase;letter-spacing:1.5px;margin-bottom:0.75rem;">'
            'Active Ritual</div>',
            unsafe_allow_html=True,
        )
        _render_active_panel(active, lib)
        st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)
    else:
        # No active session: show start panel
        _render_start_panel(lib)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    _render_history(lib)