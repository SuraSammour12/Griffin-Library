# ============================================================
# Griffin Library - Welcome and Onboarding
# ============================================================
# Entry screen for new and returning users.
# Shows a feature overview for new users and a greeting for returning ones.
# ============================================================

import base64
from datetime import datetime
from pathlib import Path

import streamlit as st
from .components import safe


# ─────────────────────────────────────────────────────────────
# Assets
# ─────────────────────────────────────────────────────────────

def _get_bg_b64() -> str:
    candidates = [
        Path(__file__).parent.parent / "static" / "welcome_bg.png",
        Path(__file__).parent.parent / "static" / "welcome_bg.jpg",
        Path(__file__).parent / "static" / "welcome_bg.png",
        Path(__file__).parent / "static" / "welcome_bg.jpg",
        Path(__file__).parent.parent.parent / "static" / "welcome_bg.png",
    ]
    for p in candidates:
        if p.exists():
            ext = "jpeg" if p.suffix == ".jpg" else "png"
            data = base64.b64encode(p.read_bytes()).decode()
            return f"data:image/{ext};base64,{data}"
    return ""


def _get_logo_b64() -> str:
    candidates = [
        Path(__file__).parent.parent / "static" / "griffin_logo.png",
        Path(__file__).parent.parent.parent / "static" / "griffin_logo.png",
    ]
    for p in candidates:
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
            return f"data:image/png;base64,{data}"
    return ""


def _inject_welcome_styles(bg_css: str):
    st.markdown(f"""
<style>
.block-container {{
    padding: 0 !important;
    max-width: 100% !important;
}}
.stApp {{
    background: {bg_css} !important;
    background-size: cover !important;
    background-position: center !important;
    background-repeat: no-repeat !important;
    background-attachment: fixed !important;
}}
/* Name input */
.stTextInput input {{
    text-align: center !important;
    font-family: 'Playfair Display', Georgia, serif !important;
    font-size: 13px !important;
    letter-spacing: 3px !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    border: 1.5px solid rgba(201,168,76,0.6) !important;
    border-radius: 12px !important;
    color: #1A1612 !important;
    background: rgba(255,255,255,0.92) !important;
    padding: 0.85rem 1rem !important;
    backdrop-filter: blur(8px) !important;
}}
.stTextInput input::placeholder {{
    color: rgba(30,58,47,0.4) !important;
    letter-spacing: 2px !important;
}}
/* Submit button */
[data-testid="stFormSubmitButton"] > button {{
    background: linear-gradient(135deg, #1E3A2F 0%, #2d5a42 100%) !important;
    color: #F5E6C8 !important;
    border: 1.5px solid rgba(201,168,76,0.4) !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
    padding: 0.85rem !important;
    letter-spacing: 2px !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25) !important;
}}
[data-testid="stFormSubmitButton"] > button:hover {{
    background: linear-gradient(135deg, #2d5a42 0%, #3d7a5a 100%) !important;
    border-color: rgba(201,168,76,0.7) !important;
}}
/* Primary button (returning user) */
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, #1E3A2F 0%, #2d5a42 100%) !important;
    color: #F5E6C8 !important;
    border: 1.5px solid rgba(201,168,76,0.4) !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    font-size: 13px !important;
    padding: 0.75rem !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.25) !important;
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Content constants
# ─────────────────────────────────────────────────────────────

_BUBBLES = [
    ("📜", "Keep a record of every tome you've conquered - your collection, your legend."),
    ("🔮", "Uncover your next great read with AI that speaks the language of themes and feeling."),
    ("🪶", "Preserve the lines that move you. Search your inscriptions by meaning, not memory."),
    ("🕯️", "Time your reading rituals and build a streak worthy of the Griffin's crest."),
]

_RETURNING_LINES = [
    "The vaults await your return.",
    "Your collection grows with every page.",
    "A great story is always worth returning to.",
    "The Griffin keeps watch over your library.",
    "Knowledge gathered is never lost.",
]

_TECH_TAGS = ["Python", "Streamlit", "FAISS", "Sentence Transformers", "Groq"]


def _greet(name: str) -> str:
    h = datetime.now().hour
    if 5 <= h < 12:    return f"The vaults open for you, {name}."
    elif 12 <= h < 17: return f"The scrolls await, {name}."
    elif 17 <= h < 21: return f"Evening falls on the library, {name}."
    else:              return f"Still reading by candlelight, {name}?"


def _subtitle() -> str:
    from datetime import date
    return _RETURNING_LINES[date.today().toordinal() % len(_RETURNING_LINES)]


# ─────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────

def render(lib, rec=None):
    name    = lib.get_name()
    bg_data = _get_bg_b64()
    logo_src = _get_logo_b64()

    bg_css = (
        f'url("{bg_data}")' if bg_data
        else "linear-gradient(160deg,#1a2e20 0%,#2d4a35 50%,#1a2318 100%)"
    )
    _inject_welcome_styles(bg_css)

    logo_html = (
        f'<img src="{logo_src}" style="'
        f'width:100px;height:100px;object-fit:contain;'
        f'border-radius:20px;display:block;margin:0 auto 16px;" />'
        if logo_src else
        '<div style="font-size:48px;text-align:center;margin-bottom:12px;">🦅</div>'
    )

    # ── RETURNING USER ────────────────────────────────────────
    if name:
        col_l, col_c, col_r = st.columns([1, 1.4, 1])
        with col_c:
            st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)
            st.markdown(
                f'{logo_html}'
                f'<div style="'
                f'text-align:center;'
                f'background:rgba(15,25,18,0.72);'
                f'backdrop-filter:blur(16px);'
                f'-webkit-backdrop-filter:blur(16px);'
                f'border:1px solid rgba(201,168,76,0.35);'
                f'border-radius:20px;'
                f'padding:2rem 2.5rem 2rem;'
                f'box-shadow:0 8px 40px rgba(0,0,0,0.4);">'
                f'<div style="font-family:\'Cinzel\',\'Playfair Display\',Georgia,serif;'
                f'font-size:26px;font-weight:700;color:#C9A84C;'
                f'letter-spacing:1px;margin-bottom:6px;">Griffin Library</div>'
                f'<div style="font-size:12px;color:rgba(201,168,76,0.6);'
                f'font-style:italic;letter-spacing:1px;margin-bottom:1.5rem;">'
                f'Where knowledge is the ultimate treasure</div>'
                f'<div style="width:40px;height:1px;background:rgba(201,168,76,0.4);'
                f'margin:0 auto 1.5rem;"></div>'
                f'<div style="font-size:18px;font-weight:600;color:#e8d5a3;'
                f'margin-bottom:8px;">{safe(_greet(name))}</div>'
                f'<div style="font-size:13px;color:rgba(232,213,163,0.65);'
                f'font-style:italic;">{safe(_subtitle())}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
            if st.button("Enter the Library →", use_container_width=True,
                         key="returning_enter", type="primary"):
                st.session_state["page"] = "Home"
                st.query_params["page"]  = "Home"
                st.rerun()
        return

    # ── NEW USER ──────────────────────────────────────────────
    col_l, col_c, col_r = st.columns([1, 1.6, 1])
    with col_c:
        st.markdown("<div style='height:4vh'></div>", unsafe_allow_html=True)

        # Logo + title - no white box, just glass panel
        bubbles_html = ""
        for icon, text in _BUBBLES:
            bubbles_html += (
                f'<div style="display:flex;align-items:center;gap:14px;'
                f'margin-bottom:12px;">'
                f'<div style="font-size:20px;flex-shrink:0;">{icon}</div>'
                f'<div style="font-size:13px;color:rgba(232,213,163,0.85);'
                f'line-height:1.5;">{safe(text)}</div>'
                f'</div>'
            )

        st.markdown(
            f'{logo_html}'
            f'<div style="'
            f'background:rgba(15,25,18,0.72);'
            f'backdrop-filter:blur(16px);'
            f'-webkit-backdrop-filter:blur(16px);'
            f'border:1px solid rgba(201,168,76,0.35);'
            f'border-radius:20px;'
            f'padding:2rem 2.25rem;'
            f'box-shadow:0 8px 40px rgba(0,0,0,0.4);">'
            # Title block
            f'<div style="text-align:center;margin-bottom:1.5rem;">'
            f'<div style="font-family:\'Cinzel\',\'Playfair Display\',Georgia,serif;'
            f'font-size:26px;font-weight:700;color:#C9A84C;letter-spacing:1px;'
            f'margin-bottom:5px;">Griffin Library</div>'
            f'<div style="font-size:12px;color:rgba(201,168,76,0.6);'
            f'font-style:italic;letter-spacing:1px;">'
            f'Where knowledge is the ultimate treasure</div>'
            f'</div>'
            # Thin gold divider
            f'<div style="width:40px;height:1px;background:rgba(201,168,76,0.4);'
            f'margin:0 auto 1.5rem;"></div>'
            # Feature bubbles
            f'{bubbles_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Name label - visible, elegant
        st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;font-size:10px;font-weight:800;'
            'color:#FFFFFF;letter-spacing:3px;'
            'text-transform:uppercase;margin-bottom:8px;'
            'text-shadow:0 1px 8px rgba(0,0,0,0.9),0 0 20px rgba(0,0,0,0.7);">'
            'Who seeks entry to the Library?</div>',
            unsafe_allow_html=True,
        )

        with st.form("welcome_form"):
            user_name = st.text_input(
                "name", placeholder="Enter your name",
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button(
                "Open the Vault →", use_container_width=True
            )

        if submitted:
            if user_name.strip():
                lib.set_name(user_name.strip())
                st.session_state["page"] = "Home"
                st.query_params["page"]  = "Home"
                st.rerun()
            else:
                st.error("Please enter your name to continue.")

        # Tech strip
        tag_html = "".join(
            f'<span style="background:rgba(255,255,255,0.08);border-radius:100px;'
            f'padding:3px 10px;font-size:10px;font-weight:600;'
            f'color:rgba(232,213,163,0.45);">{t}</span>'
            for t in _TECH_TAGS
        )
        st.markdown(
            '<div style="text-align:center;margin-top:1.5rem;">'
            '<div style="font-size:9px;color:rgba(232,213,163,0.3);'
            'letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px;">'
            'Built with</div>'
            f'<div style="display:flex;justify-content:center;gap:6px;flex-wrap:wrap;">'
            f'{tag_html}</div></div>',
            unsafe_allow_html=True,
        )