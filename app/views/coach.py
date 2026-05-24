# ============================================================
# Griffin Library - The Oracle
# ============================================================
# AI reading coach: builds personalized reading schedules,
# generates task boards, and adapts plans based on progress.
# Pure conversational coaching with an editable task board.
# ============================================================

import json
from datetime import datetime, date, timedelta
import streamlit as st
from app.views.components import safe

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL    = "llama-3.3-70b-versatile"

_SYSTEM = """You are Archon, the ancient Oracle of Griffin Library - wise, warm, and deeply knowledgeable about the art of reading.
Your purpose: guide Scholars of the Library to build powerful reading rituals and conquer their chosen tomes.

Rules:
- Always respond in English only.
- Ask ONE question at a time. Keep responses to 2-4 sentences.
- Speak with quiet authority. Be encouraging, specific, and grounded - never vague.
- Use the user's name when you know it.
- After 3-5 exchanges you have enough wisdom to forge a Scroll of Intent.

When you have gathered sufficient knowledge, inscribe a Scroll of Intent in EXACTLY this format:

<PLAN>
{
  "summary": "One personalized sentence - written as an ancient oath or declaration of intent",
  "daily_pages": 20,
  "weekly_sessions": 4,
  "session_duration_min": 25,
  "monthly_books": 1,
  "tasks": [
    {"id": "t1", "text": "Read 20 pages every evening before bed", "done": false},
    {"id": "t2", "text": "Finish current book within 2 weeks", "done": false},
    {"id": "t3", "text": "Set phone to Do Not Disturb during reading", "done": false},
    {"id": "t4", "text": "Keep a bookmark + notepad at your reading spot", "done": false}
  ],
  "tips": [
    "Start with just 5 minutes if motivation is low - it always grows.",
    "Reading the same time each day removes the decision fatigue.",
    "Track your streak - consistency is its own reward."
  ]
}
</PLAN>

After </PLAN> add one short sentence of ancient encouragement - as the Oracle sealing the scroll.
Tailor every number to what the user actually told you."""


# ─────────────────────────────────────────────────────────────
# GROQ API
# ─────────────────────────────────────────────────────────────

def _get_key() -> str:
    try:
        return st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        pass
    try:
        import os
        return os.environ.get("GROQ_API_KEY", "")
    except Exception:
        return ""


def _call_groq(messages: list) -> str:
    import requests
    key = _get_key()
    if not key:
        return (
            "⚠️ **Groq API key not configured.**\n\n"
            "Add it to `.streamlit/secrets.toml`:\n"
            "```\nGROQ_API_KEY = \"gsk_...\"\n```\n"
            "Get a free key at [console.groq.com](https://console.groq.com)."
        )
    try:
        resp = requests.post(
            _GROQ_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":      _MODEL,
                "messages":   [{"role": "system", "content": _SYSTEM}] + messages,
                "max_tokens": 700,
                "temperature": 0.7,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        return f"⚠️ Error {resp.status_code}: {resp.json().get('error', {}).get('message', 'Unknown')}"
    except requests.Timeout:
        return "⚠️ Request timed out. Please try again."
    except Exception as e:
        return f"⚠️ Connection error: {e}"


# ─────────────────────────────────────────────────────────────
# PLAN PARSING
# ─────────────────────────────────────────────────────────────

def _extract_plan(text: str) -> dict | None:
    try:
        s = text.find("<PLAN>")
        e = text.find("</PLAN>")
        if s != -1 and e != -1:
            return json.loads(text[s + 6:e].strip())
    except Exception:
        pass
    return None


def _clean_text(text: str) -> str:
    s = text.find("<PLAN>")
    e = text.find("</PLAN>")
    if s != -1 and e != -1:
        before = text[:s].strip()
        after  = text[e + 7:].strip()
        return (before + "\n\n" + after).strip() if (before or after) else after
    return text


# ─────────────────────────────────────────────────────────────
# PLAN BOARD
# ─────────────────────────────────────────────────────────────

def _render_plan_board(lib, plan: dict):
    """Interactive plan board with editable tasks."""
    tasks = plan.get("tasks", [])

    # Stats row
    dp   = plan.get("daily_pages", 0)
    ws   = plan.get("weekly_sessions", 0)
    sd   = plan.get("session_duration_min", 0)
    mb   = plan.get("monthly_books", 0)

    st.markdown(
        f'<div class="coach-plan-header">'
        f'<div class="coach-plan-title">📋 Your Reading Plan</div>'
        f'<div class="coach-plan-summary">{safe(plan.get("summary", ""))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Key numbers
    c1, c2, c3, c4 = st.columns(4)
    for col, val, lbl in [
        (c1, f"{dp} pages", "Daily goal"),
        (c2, f"{ws}×/week", "Sessions"),
        (c3, f"{sd} min", "Per session"),
        (c4, f"{mb} book/mo", "Monthly"),
    ]:
        with col:
            st.markdown(
                f'<div class="coach-kpi">'
                f'<div class="coach-kpi-val">{val}</div>'
                f'<div class="coach-kpi-lbl">{lbl}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

    # Tasks
    st.markdown('<div class="coach-tasks-heading">To-do list</div>', unsafe_allow_html=True)
    tasks = st.session_state.get("_orion_tasks", tasks)

    for i, task in enumerate(tasks):
        col_check, col_text, col_del = st.columns([0.5, 6, 0.8])
        with col_check:
            checked = st.checkbox(
                " ",
                value=task.get("done", False),
                key=f"task_check_{i}",
                label_visibility="collapsed",
            )
            if checked != task.get("done", False):
                tasks[i]["done"] = checked
                st.session_state["_orion_tasks"] = tasks
                _persist_tasks(tasks)
                _save_plan_to_lib(lib, st.session_state.get("_orion_plan", {}))
                st.rerun()
        with col_text:
            done_cls = "coach-task-done" if task.get("done") else ""
            st.markdown(
                f'<div class="coach-task-text {done_cls}">{safe(task["text"])}</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            if st.button("✕", key=f"task_del_{i}", help="Remove task"):
                tasks.pop(i)
                st.session_state["_orion_tasks"] = tasks
                _persist_tasks(tasks)
                _save_plan_to_lib(lib, st.session_state.get("_orion_plan", {}))
                st.rerun()

    # Add custom task
    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
    with st.form("add_task_form", clear_on_submit=True):
        col_t, col_btn = st.columns([5, 1])
        with col_t:
            new_task = st.text_input(
                "Add task",
                placeholder="e.g. Read 10 pages before breakfast",
                label_visibility="collapsed",
            )
        with col_btn:
            add = st.form_submit_button("Add", use_container_width=True)
        if add and new_task.strip():
            tasks.append({"id": f"u{len(tasks)}", "text": new_task.strip(), "done": False})
            st.session_state["_orion_tasks"] = tasks
            _persist_tasks(tasks)
            _save_plan_to_lib(lib, st.session_state.get("_orion_plan", {}))
            st.rerun()

    # Quest Progress
    done_count = sum(1 for t in tasks if t.get("done"))
    total      = len(tasks)
    if total > 0:
        pct = int(done_count / total * 100)
        st.markdown(
            f'<div style="margin-top:1rem;">'
            f'<div style="display:flex;justify-content:space-between;'
            f'font-size:12px;color:var(--text-muted);margin-bottom:4px;">'
            f'<span>Quest Progress</span><span>{done_count}/{total} tasks</span></div>'
            f'<div style="background:var(--surface-alt);border-radius:99px;height:6px;">'
            f'<div style="background:var(--primary);height:6px;border-radius:99px;'
            f'width:{pct}%;transition:width 0.4s ease;"></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # Tips
    tips = plan.get("tips", [])
    if tips:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="coach-tasks-heading">Ancient Principles</div>', unsafe_allow_html=True)
        for tip in tips:
            st.markdown(
                f'<div class="coach-tip">💡 {safe(tip)}</div>',
                unsafe_allow_html=True,
            )

    # Actions
    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    col_r, col_c = st.columns([1, 1])
    with col_r:
        if st.button("📜 Restore Scroll", use_container_width=True):
            orig = _extract_plan(
                "\n".join(
                    m["content"] for m in st.session_state.get("_orion_msgs", [])
                    if "<PLAN>" in m.get("content", "")
                ) or ""
            )
            if orig:
                tasks_reset = orig.get("tasks", [])
                st.session_state["_orion_tasks"] = tasks_reset
                _persist_tasks(tasks_reset)
                _save_plan_to_lib(lib, st.session_state.get("_orion_plan", {}))
                st.rerun()
    with col_c:
        if st.button("⚔️ Dissolve the Scroll", use_container_width=True):
            for k in ["_orion_plan", "_orion_tasks"]:
                st.session_state.pop(k, None)
            try:
                lib.set_coach_plan(None)
            except AttributeError:
                pass
            st.rerun()


def _save_plan_to_lib(lib, plan: dict):
    """Persist the approved plan into the library's data store."""
    try:
        lib.set_coach_plan(plan)
    except AttributeError:
        pass


def _load_plan_from_lib(lib) -> dict | None:
    """Restore plan from library on cold start."""
    try:
        return lib.get_coach_plan()
    except AttributeError:
        return None


def _persist_tasks(tasks):
    """Update tasks in session_state plan. lib persistence happens at seal time."""
    plan = st.session_state.get("_orion_plan")
    if plan:
        plan["tasks"] = tasks
        st.session_state["_orion_plan"] = plan


# ─────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────

def _render_chat(lib, name: str):
    if "_orion_msgs" not in st.session_state:
        st.session_state["_orion_msgs"] = []
        books_read = len(lib.get_by_status("read"))
        reading    = len(lib.get_by_status("reading"))
        greeting   = (
            f"Hey {name}! I am **Archon**, Oracle of Griffin Library. 📚\n\n"
            f"I can see you've {'read **' + str(books_read) + ' book' + ('' if books_read == 1 else 's') + '**' if books_read else 'just started'}"
            f"{' and have **' + str(reading) + '** in progress' if reading else ''}.\n\n"
            "I shall ask a few questions, then forge your personal Scroll of Intent "
            "with a sacred list of tasks worthy of a true Scholar.\n\n"
            "**What's your main reading goal right now?**\n"
            "*e.g. finish 1 book a month, read every morning, stop starting books I never finish…*"
        )
        st.session_state["_orion_msgs"].append(
            {"role": "assistant", "content": greeting}
        )

    msgs = st.session_state["_orion_msgs"]

    for msg in msgs:
        avatar = "🧙🏼" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(_clean_text(msg["content"]))

    # ── Pending plan confirmation ─────────────────────────────
    pending = st.session_state.get("_orion_plan_pending")
    if pending:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#E8F0EC,#D8E8DE);'
            'border:1.5px solid rgba(30,58,47,0.25);border-radius:14px;'
            'padding:1.25rem 1.5rem;margin:1rem 0;">'
            '<div style="font-size:11px;font-weight:800;color:#1E3A2F;'
            'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">'
            '📜 Your Scroll of Intent Awaits</div>'
            f'<div style="font-size:15px;font-style:italic;color:#1A1612;'
            f'margin-bottom:14px;">{pending.get("summary","")}</div>'
            '<div style="font-size:13px;color:#3B6E52;margin-bottom:4px;">'
            f'<strong>{pending.get("daily_pages",0)} pages/day</strong> · '
            f'<strong>{pending.get("weekly_sessions",0)}×/week</strong> · '
            f'<strong>{pending.get("session_duration_min",0)} min/session</strong></div>'
            '</div>',
            unsafe_allow_html=True,
        )
        ca, cb = st.columns(2)
        with ca:
            if st.button("🦅 Seal the Scroll", key="plan_approve",
                         use_container_width=True, type="primary"):
                st.session_state["_orion_plan"]  = pending
                st.session_state["_orion_tasks"] = pending.get("tasks", [])
                st.session_state.pop("_orion_plan_pending", None)
                _save_plan_to_lib(lib, pending)
                st.success("The scroll is sealed. Open **My Scroll of Intent** to begin your quest.")
                st.rerun()
        with cb:
            if st.button("🔮 Seek further counsel", key="plan_reject",
                         use_container_width=True):
                st.session_state.pop("_orion_plan_pending", None)
                # Add a nudge message so Orion knows to revise
                msgs = st.session_state.get("_orion_msgs", [])
                msgs.append({"role": "user", "content":
                    "I'd like to adjust the plan. Can you ask me a follow-up question?"})
                st.session_state["_orion_msgs"] = msgs
                st.rerun()
    # ──────────────────────────────────────────────────────────

    user_input = st.chat_input("Ask the Oracle…", key="orion_input")

    if user_input:
        msgs.append({"role": "user", "content": user_input})
        api_msgs = [m for m in msgs
                    if not (m["role"] == "assistant"
                            and "I'm **Orion**" in m["content"])]
        with st.spinner("Archon is consulting the ancient texts…"):
            reply = _call_groq(api_msgs)
        msgs.append({"role": "assistant", "content": reply})

        plan = _extract_plan(reply)
        if plan:
            # Store as PENDING - user must confirm before it goes live
            st.session_state["_orion_plan_pending"] = plan
            # Don't store to _orion_plan yet - confirmation required

        st.session_state["_orion_msgs"] = msgs
        st.rerun()

    # Quick-start chips (only shown at conversation start)
    if len(msgs) == 1:
        st.markdown(
            '<div style="font-size:11px;color:var(--text-muted);margin:10px 0 6px;">'
            'Quick start:</div>',
            unsafe_allow_html=True,
        )
        suggestions = [
            "I want to conquer 1 tome per month",
            "I only have 15 minutes a day to study",
            "Help me build a nightly reading ritual",
            "I begin scrolls but never finish them",
        ]
        cols = st.columns(2)
        for i, s in enumerate(suggestions):
            with cols[i % 2]:
                if st.button(s, key=f"qs_{i}", use_container_width=True):
                    msgs.append({"role": "user", "content": s})
                    with st.spinner("Archon is consulting the ancient texts…"):
                        reply = _call_groq([{"role": "user", "content": s}])
                    msgs.append({"role": "assistant", "content": reply})
                    plan = _extract_plan(reply)
                    if plan:
                        st.session_state["_orion_plan_pending"] = plan
                    st.session_state["_orion_msgs"] = msgs
                    st.rerun()

    # Reset conversation
    if len(msgs) > 1:
        st.markdown("<div style='height:0.75rem'></div>", unsafe_allow_html=True)
        if st.session_state.get("_orion_confirm_reset"):
            st.error(
                "**Are you certain, Scholar??** This will erase the current audience with the Oracle "
                "and your Scroll of Intent. The archives do not forgive deletion."
            )
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Cancel", key="orion_no", use_container_width=True,
                             type="primary"):
                    st.session_state["_orion_confirm_reset"] = False
                    st.rerun()
            with c2:
                if st.button("Erase the Scroll", key="orion_yes",
                             use_container_width=True):
                    for k in ["_orion_msgs", "_orion_confirm_reset",
                              "_orion_plan", "_orion_tasks", "_orion_plan_pending"]:
                        st.session_state.pop(k, None)
                    st.rerun()
        else:
            if st.button("🔄 Consult the Oracle Anew", key="orion_reset"):
                st.session_state["_orion_confirm_reset"] = True
                st.rerun()


# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────

def render(lib):
    name = lib.get_name() or "there"

    # ── Clear stale chat if the user changed (different name) ────
    # Prevents previous user's conversation appearing for a new user.
    last_owner = st.session_state.get("_orion_owner")
    if last_owner and last_owner != name:
        for k in ["_orion_msgs", "_orion_plan", "_orion_tasks",
                  "_orion_plan_pending", "_orion_confirm_reset"]:
            st.session_state.pop(k, None)
    st.session_state["_orion_owner"] = name

    # ── Restore persisted plan on cold start / page refresh ──
    if "_orion_plan" not in st.session_state:
        saved = _load_plan_from_lib(lib)
        if saved:
            st.session_state["_orion_plan"]  = saved
            st.session_state["_orion_tasks"] = saved.get("tasks", [])

    st.markdown("""
    <div class="page-title">The Oracle</div>
    <div class="page-subtitle">
        Archon, the Oracle of Griffin Library, forges reading rituals - ancient scrolls of intent, sacred task lists,
        and wisdom that deepens as your chronicle grows.
    </div>
    """, unsafe_allow_html=True)

    plan = st.session_state.get("_orion_plan")

    tab_chat, tab_plan = st.tabs(["🔮 Consult the Oracle", "📜 My Scroll of Intent"])

    with tab_chat:
        _render_chat(lib, name)

    with tab_plan:
        # Show pending plan notice in My Plan tab too
        if st.session_state.get("_orion_plan_pending"):
            st.info(
                "📋 **A Scroll of Intent awaits your seal.** "
                "Return to **Consult the Oracle** to approve or seek revision."
            )
        if plan:
            _render_plan_board(lib, plan)
        else:
            st.markdown(
                '<div class="empty-state">'
                'No scroll has been forged yet. Consult the Oracle to begin. '
                'Answer 3-4 questions and Archon will forge your Scroll of Intent - with a '
                'sacred task list worthy of a Griffin Scholar.'
                '</div>',
                unsafe_allow_html=True,
            )