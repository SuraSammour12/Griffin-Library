"""
Griffin Library - AI-powered reading companion.
Run: streamlit run app.py
"""

import logging
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

from core import Library, Recommender, QuoteSearchEngine
from app.views import welcome, home, discover, foryou, library as library_view
from app.views import coach as coach_view
from app.views import sessions as sessions_view
from app.views import quotes as quotes_view, stats, explore, settings as settings_view

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("griffin")

_PAGE_TITLES = {
    "Welcome":   "Griffin Library · Enter the Vault",
    "Home":      "Griffin Library · The Grand Hall",
    "Discover":  "Griffin Library · The Scrolls",
    "For You":   "Griffin Library · Chosen for You",
    "Library":   "Griffin Library · Your Collection",
    "Quotes":    "Griffin Library · Inscriptions",
    "Stats":     "Griffin Library · The Chronicle",
    "Explore":   "Griffin Library · The Archives",
    "Settings":  "Griffin Library · The Sanctum",
    "Coach":     "Griffin Library · The Oracle",
    "Sessions":  "Griffin Library · Reading Rituals",
}

_PAGE_KEY_MAP = {
    "Welcome":      "Welcome",
    "Home":         "Home",
    "Discover":     "Discover",
    "For You":      "For You",
    "My Library":   "Library",
    "Quotes":       "Quotes",
    "Stats":        "Stats",
    "Explore":      "Explore",
    "Settings":     "Settings",
    "Coach":        "Coach",
    "Sessions":     "Sessions",
}

_early_page  = st.query_params.get("page") or "Welcome"
_title_key   = _PAGE_KEY_MAP.get(_early_page, "Welcome")
_early_title = _PAGE_TITLES.get(_title_key, "Griffin Library")

st.set_page_config(
    page_title=_early_title,
    page_icon=str(ROOT / "static" / "griffin_logo.png") if (ROOT / "static" / "griffin_logo.png").exists() else "🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css() -> str:
    css_path = ROOT / "app" / "styles" / "main.css"
    return css_path.read_text(encoding="utf-8") if css_path.exists() else ""


css = load_css()
if css:
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# Sidebar toggle: keeps the collapse button visible across Streamlit re-renders.
st.markdown("""
<script>
(function fixSidebarToggle() {
    function patch() {
        // All known Streamlit sidebar toggle selectors (across versions)
        var selectors = [
            '[data-testid="collapsedControl"]',
            '[data-testid="stSidebarCollapsedControl"]',
        ];
        selectors.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display',        'flex',    'important');
                el.style.setProperty('visibility',     'visible', 'important');
                el.style.setProperty('opacity',        '1',       'important');
                el.style.setProperty('pointer-events', 'auto',    'important');
                el.style.setProperty('position',       'fixed',   'important');
                el.style.setProperty('top',            '0.75rem', 'important');
                el.style.setProperty('left',           '0.65rem', 'important');
                el.style.setProperty('z-index',        '999999',  'important');
                el.style.setProperty('background',     '#FFFFFF',  'important');
                el.style.setProperty('border',         '1.5px solid #E2DAD0', 'important');
                el.style.setProperty('border-radius',  '10px',    'important');
                el.style.setProperty('box-shadow',     '0 2px 8px rgba(26,22,18,0.09)', 'important');
                el.style.setProperty('width',          '2.2rem',  'important');
                el.style.setProperty('height',         '2.2rem',  'important');
                el.style.setProperty('align-items',    'center',  'important');
                el.style.setProperty('justify-content','center',  'important');
                el.style.setProperty('cursor',         'pointer', 'important');
            });
        });
    }
    // Run immediately
    patch();
    // Re-run after Streamlit re-renders (it swaps DOM nodes)
    var obs = new MutationObserver(patch);
    obs.observe(document.body, { childList: true, subtree: true });
    // Belt-and-suspenders: also run every 800ms for the first 8 seconds
    var ticks = 0;
    var iv = setInterval(function() {
        patch();
        if (++ticks >= 10) clearInterval(iv);
    }, 800);
})();
</script>
""", unsafe_allow_html=True)


# postMessage receiver: listens for session actions from the timer iframe and updates the URL.
st.markdown("""
<script>
(function installGriffinReceiver() {
  if (window._griffinReceiverInstalled) return;
  window._griffinReceiverInstalled = true;

  window.addEventListener('message', function(ev) {
    var d = ev.data;
    if (!d || d.type !== 'griffin_action') return;

    var url = new URL(window.location.href);

    // Always wipe stale params first
    ['eq_action','eq_elapsed','eq_pages','eq_newpage',
     'eq_book_id','eq_t'].forEach(function(k){ url.searchParams.delete(k); });

    if (d.clearSess) url.searchParams.delete('eq_sess');

    if (d.action === 'cancel') {
      // Discard - remove session and navigate with cancel action
      url.searchParams.delete('eq_sess');
      url.searchParams.set('eq_action', 'cancel');
      url.searchParams.set('eq_t', String(d.ts || Date.now()));
    } else {
      url.searchParams.set('eq_action',  d.action);
      url.searchParams.set('eq_elapsed', String(d.mins  || 0));
      url.searchParams.set('eq_pages',   String(d.pages || 0));
      if (d.newpage != null) url.searchParams.set('eq_newpage', String(d.newpage));
      url.searchParams.set('eq_book_id', d.book_id || '');
      url.searchParams.set('eq_t',       String(d.ts || Date.now()));
    }

    window.location.replace(url.toString());
  });
})();
</script>
""", unsafe_allow_html=True)



@st.cache_resource(show_spinner="Loading AI engine…")
def get_recommender():
    try:
        return Recommender(
            index_path=ROOT / "models" / "book_index.faiss",
            catalog_path=ROOT / "models" / "books_cleaned.pkl",
        )
    except FileNotFoundError as e:
        log.error("Model files missing: %s", e)
        return None
    except Exception as e:
        log.exception("Recommender init failed: %s", e)
        return None


@st.cache_resource
def get_quote_search(_rec):
    if _rec is None:
        return None
    try:
        return QuoteSearchEngine(_rec.model)
    except Exception:
        log.exception("Quote search init failed")
        return None


@st.cache_resource
def get_library():
    data_dir = ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return Library(data_dir / "library.json")


# Sidebar navigation: renders grouped page links with active state highlighting.

_NAV_GROUPS = [
    {
        "label": None,
        "pages": [
            ("Home",       "🏰  Grand Hall"),
        ],
    },
    {
        "label": "The Vaults",
        "pages": [
            ("Discover",   "🔍  The Scrolls"),
            ("For You",    "🪄   Chosen for You"),
            ("Explore",    "🗺️  The Archives"),
        ],
    },
    {
        "label": "Your Chronicle",
        "pages": [
            ("My Library", "📜  My Collection"),
            ("Quotes",     "🪶  Inscriptions"),
            ("Stats",      "⚗️  The Chronicle"),
            ("Sessions",   "🕯️  Reading Rituals"),
        ],
    },
    {
        "label": "The Inner Circle",
        "pages": [
            ("Coach",      "🧙🏼  The Oracle"),
            ("Settings",   "⚙️  The Sanctum"),
        ],
    },
]


def _sidebar_logo_html() -> str:
    import base64
    candidates = [
        ROOT / "static" / "griffin_logo.png",
    ]
    for p in candidates:
        if p.exists():
            data = base64.b64encode(p.read_bytes()).decode()
            return (
                f'<img src="data:image/png;base64,{data}" '
                f'style="width:72px;height:72px;object-fit:contain;'
                f'border-radius:16px;display:block;margin:0 auto 8px;" />'
            )
    return '<div style="font-size:36px;text-align:center;margin-bottom:8px;">🦅</div>'


def render_sidebar(current_page: str):
    with st.sidebar:
        # ── Logo ─────────────────────────────────────────────
        logo_img = _sidebar_logo_html()
        st.markdown(
            f'<div style="padding:1.25rem 1.25rem 1rem;'
            f'border-bottom:1px solid var(--border);'
            f'margin-bottom:0.5rem;text-align:center;">'
            f'{logo_img}'
            f'<div class="eq-logo" style="margin-top:4px;">Griffin Library</div>'
            f'<div style="font-size:9px; color:var(--text-hint);'
            f'letter-spacing:1.5px; text-transform:uppercase;'
            f'margin-top:3px; font-family:var(--font-display);">'
            f'Where knowledge is the ultimate treasure'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # ── Nav groups ────────────────────────────────────────
        for group in _NAV_GROUPS:
            if group["label"]:
                st.markdown(
                    f'<div style="font-size:9px;font-weight:800;'
                    f'color:var(--text-hint);letter-spacing:2px;'
                    f'text-transform:uppercase;padding:0.9rem 1rem 0.3rem;'
                    f'font-family:var(--font-display);">{group["label"]}</div>',
                    unsafe_allow_html=True,
                )

            for page_id, page_label in group["pages"]:
                is_active = (current_page == page_id)
                if is_active:
                    st.markdown(
                        f'<div style="background:var(--ink-soft);'
                        f'padding:0.58rem 1rem;border-radius:var(--r-sm);'
                        f'font-weight:700;font-size:13.5px;'
                        f'color:var(--ink);margin:1px 0;'
                        f'font-family:var(--font-display);">{page_label}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    if st.button(page_label, key=f"nav_{page_id}",
                                 use_container_width=True):
                        st.session_state["page"] = page_id
                        st.query_params["page"]  = page_id
                        st.rerun()

        # ── Footer ────────────────────────────────────────────
        st.markdown(
            '<hr style="border:none;border-top:1px solid var(--border);margin:1rem 0 0.5rem;">',
            unsafe_allow_html=True,
        )

        if st.button("← Back to entrance", key="nav_welcome",
                         use_container_width=True):
                st.session_state["page"] = "Welcome"
                st.query_params["page"]  = "Welcome"
                st.rerun()

        st.markdown(
            '<div style="font-size:9px;color:var(--text-hint);'
            'text-align:center;padding:0.5rem 0 1rem;'
            'font-family:var(--font-display);">Griffin Library</div>',
            unsafe_allow_html=True,
        )


# Entry point: initialises library, resolves current page, and dispatches to the correct view.



def _ai_required(rec, render_fn):
    if rec is None:
        st.error(
            "AI engine could not load. "
            "Check that model files exist in the /models directory."
        )
        return
    render_fn()


def main():
    real_lib = get_library()

    url_page = st.query_params.get("page", None)

    if "page" not in st.session_state:
        st.session_state["page"] = url_page if url_page else "Welcome"

    current_page = st.session_state["page"]
    lib = real_lib

    # Guard: no name set → force Welcome
    if not lib.get_name() and current_page != "Welcome":
        st.session_state["page"] = "Welcome"
        current_page = "Welcome"

    # Sync query params (skip when JS eq_action is in flight)
    has_eq_action = bool(st.query_params.get("eq_action"))
    if not has_eq_action:
        if current_page != "Welcome":
            st.query_params["page"] = current_page
        else:
            try:
                del st.query_params["page"]
            except Exception:
                pass

    # Browser title
    title_key = _PAGE_KEY_MAP.get(current_page, "Welcome")
    _title = _PAGE_TITLES.get(title_key, "Griffin Library")
    st.markdown(
        f"<script>window.parent.document.title = '{_title}';</script>",
        unsafe_allow_html=True,
    )

    # Welcome page has no sidebar
    needs_ai = current_page in ("Discover", "For You", "Quotes", "Explore", "Welcome")
    rec = get_recommender() if needs_ai else None
    qs  = get_quote_search(rec) if rec is not None else None

    if current_page == "Welcome":
        welcome.render(lib, rec)
        return

    render_sidebar(current_page)

    # Active-session banner on non-Home pages
    if st.session_state.get("active_session") and current_page != "Home":
        _s   = st.session_state["active_session"]
        _lbl = (f"📚 {_s.get('book_title','')}"
                if not _s.get("is_free") else "🌿 Free reading")
        col_b, col_btn = st.columns([4, 1])
        with col_b:
            st.info(f"⏱️ Session active: **{_lbl}** ({_s.get('duration_minutes',30)} min)")
        with col_btn:
            if st.button("→ Home", key="_active_sess_home",
                         type="primary", use_container_width=True):
                st.session_state["page"] = "Home"
                st.rerun()

    routes = {
        "Home":       lambda: home.render(lib),
        "Discover":   lambda: _ai_required(rec, lambda: discover.render(lib, rec)),
        "For You":    lambda: _ai_required(rec, lambda: foryou.render(lib, rec)),
        "My Library": lambda: library_view.render(lib, rec),
        "Quotes":     lambda: quotes_view.render(lib, qs),
        "Stats":      lambda: stats.render(lib),
        "Explore":    lambda: explore.render(lib, rec),
        "Settings":   lambda: settings_view.render(lib),
        "Coach":      lambda: coach_view.render(lib),
        "Sessions":   lambda: sessions_view.render(lib),
    }

    handler = routes.get(current_page)
    if handler:
        handler()
    else:
        st.session_state["page"] = "Home"
        st.rerun()


main()