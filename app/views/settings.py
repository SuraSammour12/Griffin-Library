# ============================================================
# Griffin Library - The Sanctum (Settings)
# ============================================================
# User profile, annual reading goal, data export,
# automatic backups, and collection reset.
# ============================================================

import streamlit as st
from datetime import date
from .components import safe


def render(lib):
    st.markdown("""
    <div class="page-title">The Sanctum</div>
    <div class="page-subtitle">Your identity, your oath, and your records.</div>
    """, unsafe_allow_html=True)

    # ── Profile ─────────────────────────────────────────────
    st.markdown(
        '<div class="section-heading">Profile</div>',
        unsafe_allow_html=True,
    )
    current_name = lib.get_name()
    with st.form("settings_name"):
        new_name = st.text_input(
            "Scholar Name",
            value=current_name,
            placeholder="Your name in the Library",
        )
        save_name = st.form_submit_button("Inscribe Name")
    if save_name and new_name.strip() and new_name.strip() != current_name:
        lib.set_name(new_name.strip())
        st.success("Name updated.")
        st.rerun()

    # ── Goals ───────────────────────────────────────────────
    st.markdown(
        '<div class="section-heading" style="margin-top:1.5rem;">Annual Reading Oath</div>',
        unsafe_allow_html=True,
    )
    current_goal = lib.get_goals().yearly_goal
    with st.form("settings_goal"):
        new_goal = st.number_input(
            f"Tomes to conquer in {date.today().year}",
            min_value=1, max_value=365,
            value=int(current_goal),
            step=1,
        )
        save_goal = st.form_submit_button("Seal the Oath")
    if save_goal and int(new_goal) != int(current_goal):
        lib.set_goal(int(new_goal))
        st.success("Goal updated.")
        st.rerun()

    # ── Data Export ─────────────────────────────────────────
    st.markdown(
        '<div class="section-heading" style="margin-top:1.5rem;">Your Records</div>',
        unsafe_allow_html=True,
    )

    st.markdown("""
    <div class="eq-card">
        <div style="font-size:13px; color:var(--text); font-weight:600; margin-bottom:6px;">
            Export the Archives
        </div>
        <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px; line-height:1.5;">
            Download your full chronicle — tomes, inscriptions, notes, verdicts, oaths — as a JSON file.
            The archives can be restored on any sanctum.
        </div>
    </div>
    """, unsafe_allow_html=True)

    json_data = lib.export_json()
    st.download_button(
        "Download chronicle.json",
        data=json_data,
        file_name=f"griffin_library_{date.today()}.json",
        mime="application/json",
        use_container_width=True,
    )

    # Backups list
    backups = lib.storage.list_backups()
    if backups:
        with st.expander(f"Automatic Vault Backups ({len(backups)})"):
            st.markdown("""
            <div style="font-size:12px; color:var(--text-muted); margin-bottom:8px; line-height:1.5;">
                The Library preserves the last 7 daily backups of your chronicle. They live in
                <code>data/backups/</code> next to your library file.
            </div>
            """, unsafe_allow_html=True)
            for b in backups:
                st.markdown(
                    f'<div style="font-size:12px; color:var(--text); padding:4px 0; '
                    f'font-family:monospace;">{safe(b)}</div>',
                    unsafe_allow_html=True,
                )

    # ── Danger zone ─────────────────────────────────────────
    st.markdown(
        '<div class="section-heading" style="margin-top:1.5rem; color:var(--danger);">The Forbidden Seal</div>',
        unsafe_allow_html=True,
    )

    if st.session_state.get("confirm_reset_lib"):
        st.error(
            "**This will erase everything** — all tomes, inscriptions, verdicts, notes, and your oath. "
            "Your name in the Library will also be cleared. A chronicle backup is preserved before this action, "
            "but it's still worth exporting first."
        )
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            if st.button("Cancel", key="reset_cancel", use_container_width=True):
                st.session_state["confirm_reset_lib"] = False
                st.rerun()
        with col_d2:
            if st.button("Yes, dissolve everything", key="reset_confirm", use_container_width=True):
                lib.reset()
                st.session_state["confirm_reset_lib"] = False
                st.session_state["page"] = "Welcome"
                st.rerun()
    else:
        if st.button("Dissolve the Collection"):
            st.session_state["confirm_reset_lib"] = True
            st.rerun()

    # ── About ───────────────────────────────────────────────
    st.markdown("<hr class='eq-divider' style='margin-top:2rem;'>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:12px; color:var(--text-hint); text-align:center; line-height:1.6;">
        <strong>Griffin Library v2</strong> - AI-powered reading companion built on all-mpnet-base-v2 + FAISS<br>
        Built with Streamlit
    </div>
    """, unsafe_allow_html=True)