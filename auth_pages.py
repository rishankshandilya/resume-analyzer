"""
auth_pages.py
--------------
Renders the Login and Registration screens.
Both pages use utils/auth.py for all actual logic - this file is
purely presentation + wiring user input to that logic.
"""

import streamlit as st
from utils.auth import register_user, login_user, AuthError
from utils.styles import brand_header


def render_login(go_to):
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        brand_header()
        st.markdown("### Welcome back")
        st.caption("Log in to analyze your resume and track your progress.")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Log In", use_container_width=True)

        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                try:
                    user = login_user(email, password)
                    st.session_state.user = user
                    st.session_state.page = "dashboard"
                    st.success(f"Welcome back, {user['full_name'].split()[0]}!")
                    st.rerun()
                except AuthError as e:
                    st.error(str(e))

        st.divider()
        st.caption("Don't have an account yet?")
        if st.button("Create an account", use_container_width=True):
            go_to("register")
            st.rerun()


def render_register(go_to):
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        brand_header()
        st.markdown("### Create your account")
        st.caption("Free forever. Track every resume version you upload.")

        with st.form("register_form"):
            full_name = st.text_input("Full name", placeholder="Rahul Sharma")
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="At least 6 characters")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                try:
                    register_user(full_name, email, password)
                    st.success("Account created! Please log in.")
                    go_to("login")
                    st.rerun()
                except AuthError as e:
                    st.error(str(e))

        st.divider()
        st.caption("Already have an account?")
        if st.button("Back to log in", use_container_width=True):
            go_to("login")
            st.rerun()
