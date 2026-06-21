"""
styles.py
----------
Centralized visual theme for the app. Keeping CSS in one place means
every page looks consistent and we only have to tune the look once.

Design direction:
A "career command center" feel rather than a generic dashboard -
deep ink-navy as the anchor (serious, professional, trustworthy - the
color of a good blazer), with a warm amber accent standing in for the
single "go" signal (your ATS score, your call-to-action). Typography
pairs a confident grotesk for headings with a clean system body face.
"""

import streamlit as st

INK = "#10172A"        # deep navy-black - primary background / headings
INK_SOFT = "#1B2440"   # card backgrounds
SLATE = "#5B6478"      # secondary text
PAPER = "#F7F6F2"      # warm off-white - main app background
AMBER = "#E8A33D"      # signature accent - score, CTAs
AMBER_SOFT = "#FBE8C8"
GOOD = "#2E8B57"       # success green
WARN = "#D9763C"       # warning orange
BAD = "#C44545"        # error red
BORDER = "#E4E1D8"


def inject_global_styles():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Inter', -apple-system, sans-serif;
        }}

        .stApp {{
            background-color: {PAPER};
        }}

        h1, h2, h3 {{
            font-family: 'Space Grotesk', sans-serif !important;
            color: {INK} !important;
            font-weight: 700 !important;
            letter-spacing: -0.01em;
        }}

        /* Top brand bar */
        .brand-bar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0.6rem 0 1.2rem 0;
            border-bottom: 2px solid {INK};
            margin-bottom: 1.6rem;
        }}
        .brand-mark {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 1.3rem;
            color: {INK};
            letter-spacing: -0.02em;
        }}
        .brand-mark span {{ color: {AMBER}; }}
        .brand-tag {{
            color: {SLATE};
            font-size: 0.82rem;
        }}

        /* Card */
        .card {{
            background: white;
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 1.4rem 1.6rem;
            margin-bottom: 1rem;
        }}

        /* Score badge */
        .score-ring-wrap {{
            text-align: center;
            padding: 1rem 0;
        }}
        .score-big {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 3.4rem;
            font-weight: 700;
            color: {INK};
            line-height: 1;
        }}
        .score-big span {{
            font-size: 1.4rem;
            color: {SLATE};
            font-weight: 500;
        }}
        .score-label {{
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.72rem;
            color: {SLATE};
            margin-top: 0.3rem;
        }}

        /* Pills */
        .pill {{
            display: inline-block;
            padding: 0.25rem 0.7rem;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 600;
            margin: 0.15rem 0.25rem 0.15rem 0;
        }}
        .pill-found {{ background: #E2F0E6; color: {GOOD}; }}
        .pill-missing {{ background: #FBEAE6; color: {BAD}; }}
        .pill-mode {{ background: {AMBER_SOFT}; color: #8A5A12; }}

        /* Suggestion items */
        .suggestion-item {{
            background: #FCFBF8;
            border-left: 3px solid {AMBER};
            padding: 0.6rem 0.9rem;
            margin-bottom: 0.5rem;
            border-radius: 4px;
            font-size: 0.92rem;
            color: {INK};
        }}

        /* Buttons */
        .stButton button {{
            background-color: {INK} !important;
            color: white !important;
            border-radius: 6px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 0.5rem 1.2rem !important;
        }}
        .stButton button:hover {{
            background-color: {AMBER} !important;
            color: {INK} !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {INK};
        }}
        section[data-testid="stSidebar"] * {{
            color: #F0EFE9 !important;
        }}
        section[data-testid="stSidebar"] .stButton button {{
            background-color: {AMBER} !important;
            color: {INK} !important;
            width: 100%;
        }}

        footer {{visibility: hidden;}}
        #MainMenu {{visibility: hidden;}}
    </style>
    """, unsafe_allow_html=True)


def brand_header(tagline="AI-powered resume feedback before you hit apply"):
    st.markdown(f"""
    <div class="brand-bar">
        <div class="brand-mark">Resume<span>IQ</span></div>
        <div class="brand-tag">{tagline}</div>
    </div>
    """, unsafe_allow_html=True)


def score_color(score: float) -> str:
    if score >= 75:
        return GOOD
    elif score >= 50:
        return WARN
    return BAD
