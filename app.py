"""
app.py
-------
Entry point of the Streamlit application.

Responsibilities:
  - Initialize the database on first run
  - Manage session state (who's logged in)
  - Route between Login / Register / Dashboard / Upload / Results / History

Run locally with:   streamlit run app.py
"""

import streamlit as st
from utils.database import init_db
from utils.styles import inject_global_styles
import auth_pages
import app_pages

st.set_page_config(
    page_title="ResumeIQ — AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Run once per server start - creates tables if they don't exist yet.
init_db()

inject_global_styles()

# ----------------------------------------------------------------------
# SESSION STATE DEFAULTS
# Streamlit re-runs the whole script on every interaction, so anything
# that needs to persist between reruns (like "is the user logged in?")
# must live in st.session_state.
# ----------------------------------------------------------------------
if "user" not in st.session_state:
    st.session_state.user = None          # holds {user_id, full_name, email} once logged in
if "page" not in st.session_state:
    st.session_state.page = "login"       # which page to show
if "active_analysis" not in st.session_state:
    st.session_state.active_analysis = None  # holds the most recent analysis result to show on Results page


def go_to(page_name: str):
    st.session_state.page = page_name


# ----------------------------------------------------------------------
# ROUTING
# If nobody is logged in, only Login/Register are reachable.
# Once logged in, the sidebar nav controls which page is shown.
# ----------------------------------------------------------------------
if st.session_state.user is None:
    if st.session_state.page == "register":
        auth_pages.render_register(go_to)
    else:
        auth_pages.render_login(go_to)

else:
    # Logged-in sidebar navigation
    with st.sidebar:
        st.markdown(f"### 👋 {st.session_state.user['full_name'].split()[0]}")
        st.caption(st.session_state.user["email"])
        st.divider()

        if st.button("🏠 Dashboard", use_container_width=True):
            go_to("dashboard")
        if st.button("📤 Upload Resume", use_container_width=True):
            go_to("upload")
        if st.button("📊 Results", use_container_width=True):
            go_to("results")
        if st.button("🕘 History", use_container_width=True):
            go_to("history")

        st.divider()
        if st.button("🚪 Log Out", use_container_width=True):
            st.session_state.user = None
            st.session_state.active_analysis = None
            go_to("login")
            st.rerun()

    page = st.session_state.page
    if page == "dashboard":
        app_pages.render_dashboard(go_to)
    elif page == "upload":
        app_pages.render_upload(go_to)
    elif page == "results":
        app_pages.render_results(go_to)
    elif page == "history":
        app_pages.render_history(go_to)
    else:
        app_pages.render_dashboard(go_to)
