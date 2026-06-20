"""
app_pages.py
-------------
Renders the four core pages a logged-in user sees:
  - Dashboard: overview stats + quick actions
  - Upload: resume upload + role selection + triggers analysis
  - Results: full ATS breakdown for the most recent analysis
  - History: table + chart of all past analyses, with comparison
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.styles import brand_header, score_color, AMBER, INK, GOOD, BAD
from utils.resume_parser import ResumeParser, ParsingError
from utils.ats_engine import ATSEngine
from utils.skill_extractor import get_available_roles
from utils.ai_helper import get_ai_suggestions, is_ai_available
from utils.database import db_cursor


# ===========================================================================
# DASHBOARD
# ===========================================================================
def render_dashboard(go_to):
    brand_header()
    user = st.session_state.user
    st.markdown(f"## Welcome, {user['full_name'].split()[0]} 👋")

    stats = _get_user_stats(user["user_id"])

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _stat_card("Resumes Analyzed", stats["total_analyses"])
    with c2:
        _stat_card("Latest Score", f"{stats['latest_score']}/100" if stats["latest_score"] is not None else "—")
    with c3:
        _stat_card("Best Score", f"{stats['best_score']}/100" if stats["best_score"] is not None else "—")
    with c4:
        ai_status = "ON ✅" if is_ai_available() else "OFF (Local Mode)"
        _stat_card("AI Mode", ai_status)

    st.write("")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("""<div class="card">
            <h3 style="margin-top:0;">📤 Analyze a new resume</h3>
            <p style="color:#5B6478;">Upload a PDF or DOCX file and get your ATS score in seconds.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("Upload Resume →", use_container_width=True):
            go_to("upload")
            st.rerun()

    with col2:
        st.markdown("""<div class="card">
            <h3 style="margin-top:0;">🕘 Track your progress</h3>
            <p style="color:#5B6478;">Compare past resume versions and see your score improve.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("View History →", use_container_width=True):
            go_to("history")
            st.rerun()

    if stats["total_analyses"] > 0:
        st.write("")
        st.markdown("#### Score trend")
        history_df = _get_score_history_df(user["user_id"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=history_df["analyzed_at"], y=history_df["ats_score"],
            mode="lines+markers", line=dict(color=AMBER, width=3),
            marker=dict(size=9, color=INK),
        ))
        fig.update_layout(
            height=280, margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(range=[0, 100], title="ATS Score"),
            xaxis=dict(title=""),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)


def _stat_card(label, value):
    st.markdown(f"""
    <div class="card" style="text-align:center;">
        <div style="font-size:1.8rem; font-weight:700; font-family:'Space Grotesk',sans-serif; color:{INK};">{value}</div>
        <div style="font-size:0.78rem; color:#5B6478; text-transform:uppercase; letter-spacing:0.05em;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def _get_user_stats(user_id):
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) as cnt FROM resume_analysis WHERE user_id = ?", (user_id,))
        total = cur.fetchone()["cnt"]

        cur.execute("""SELECT ats_score FROM resume_analysis WHERE user_id = ?
                       ORDER BY analyzed_at DESC LIMIT 1""", (user_id,))
        row = cur.fetchone()
        latest = row["ats_score"] if row else None

        cur.execute("SELECT MAX(ats_score) as best FROM resume_analysis WHERE user_id = ?", (user_id,))
        best_row = cur.fetchone()
        best = best_row["best"] if best_row and best_row["best"] is not None else None

    return {"total_analyses": total, "latest_score": latest, "best_score": best}


def _get_score_history_df(user_id):
    with db_cursor() as cur:
        cur.execute("""SELECT ats_score, analyzed_at FROM resume_analysis
                       WHERE user_id = ? ORDER BY analyzed_at ASC""", (user_id,))
        rows = cur.fetchall()
    return pd.DataFrame([dict(r) for r in rows])


# ===========================================================================
# UPLOAD PAGE
# ===========================================================================
def render_upload(go_to):
    brand_header()
    st.markdown("## Upload your resume")
    st.caption("PDF or DOCX, max 5MB. Your file is parsed locally and never leaves the analysis pipeline.")

    target_role = st.selectbox("Which role are you targeting?", get_available_roles())
    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx"])

    if uploaded_file is not None:
        if st.button("🔍 Analyze Resume", use_container_width=True):
            with st.spinner("Reading your resume..."):
                try:
                    parser = ResumeParser(uploaded_file)
                    resume_text = parser.extract_text()
                except ParsingError as e:
                    st.error(str(e))
                    return

            with st.spinner("Scoring against ATS criteria..."):
                engine = ATSEngine(resume_text, target_role=target_role)
                result = engine.analyze()

            with st.spinner("Generating suggestions..."):
                suggestions, mode_used = get_ai_suggestions(resume_text, result, target_role)
                result["suggestions"] = suggestions
                result["analysis_mode"] = mode_used

            resume_id = _save_resume(st.session_state.user["user_id"], uploaded_file.name, parser.file_type, resume_text)
            _save_analysis(st.session_state.user["user_id"], resume_id, result)

            st.session_state.active_analysis = result
            st.session_state.active_analysis["file_name"] = uploaded_file.name
            st.session_state.active_analysis["target_role"] = target_role

            st.success("Analysis complete!")
            go_to("results")
            st.rerun()


def _save_resume(user_id, file_name, file_type, raw_text):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO resumes (user_id, file_name, file_type, raw_text) VALUES (?, ?, ?, ?)",
            (user_id, file_name, file_type, raw_text),
        )
        return cur.lastrowid


def _save_analysis(user_id, resume_id, result):
    b = result["breakdown"]
    with db_cursor(commit=True) as cur:
        cur.execute("""
            INSERT INTO resume_analysis
                (resume_id, user_id, ats_score, contact_score, education_score, skills_score,
                 projects_score, experience_score, formatting_score, keywords_score, length_score,
                 skills_found, skills_missing, suggestions, analysis_mode)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            resume_id, user_id, result["ats_score"],
            b["contact"], b["education"], b["skills"], b["projects"],
            b["experience"], b["formatting"], b["keywords"], b["length"],
            ", ".join(result["skills_found"]), ", ".join(result["skills_missing"]),
            "\n".join(result["suggestions"]), result["analysis_mode"],
        ))


# ===========================================================================
# RESULTS PAGE
# ===========================================================================
def render_results(go_to):
    brand_header()
    result = st.session_state.active_analysis

    if result is None:
        st.info("No analysis to show yet. Upload a resume to get started.")
        if st.button("Go to Upload"):
            go_to("upload")
            st.rerun()
        return

    score = result["ats_score"]
    color = score_color(score)

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown(f"""
        <div class="card score-ring-wrap">
            <div class="score-big" style="color:{color};">{score}<span>/100</span></div>
            <div class="score-label">ATS Score</div>
        </div>
        """, unsafe_allow_html=True)
        mode = result.get("analysis_mode", "Rule-Based")
        st.markdown(f'<span class="pill pill-mode">⚙ {mode} analysis</span>', unsafe_allow_html=True)
        st.caption(f"File: {result.get('file_name', '—')}")
        st.caption(f"Target role: {result.get('target_role', '—')}")

    with col2:
        st.markdown("#### Category Breakdown")
        breakdown = result["breakdown"]
        max_b = result["max_breakdown"]
        fig = go.Figure(go.Bar(
            x=[v for v in breakdown.values()],
            y=[k.replace("_", " ").title() for k in breakdown.keys()],
            orientation="h",
            marker_color=AMBER,
            text=[f"{v}/{max_b[k]}" for k, v in breakdown.items()],
            textposition="auto",
        ))
        fig.update_layout(
            height=320, margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(range=[0, 20], title=""),
            plot_bgcolor="white", paper_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.write("")
    col3, col4 = st.columns(2)
    with col3:
        st.markdown("#### ✅ Skills Found")
        if result["skills_found"]:
            pills = "".join(f'<span class="pill pill-found">{s}</span>' for s in result["skills_found"])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("No recognized skills found.")

    with col4:
        st.markdown("#### ⚠️ Missing Keywords")
        if result["skills_missing"]:
            pills = "".join(f'<span class="pill pill-missing">{s}</span>' for s in result["skills_missing"])
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.caption("Great coverage — nothing major missing!")

    st.write("")
    st.markdown("#### 💡 Suggestions to improve your score")
    for s in result["suggestions"]:
        st.markdown(f'<div class="suggestion-item">{s}</div>', unsafe_allow_html=True)

    st.write("")
    if st.button("📤 Analyze Another Resume", use_container_width=True):
        go_to("upload")
        st.rerun()


# ===========================================================================
# HISTORY PAGE
# ===========================================================================
def render_history(go_to):
    brand_header()
    st.markdown("## Resume History")
    st.caption("Every version you've analyzed, most recent first.")

    user_id = st.session_state.user["user_id"]
    with db_cursor() as cur:
        cur.execute("""
            SELECT ra.analysis_id, r.file_name, ra.ats_score, ra.analysis_mode, ra.analyzed_at
            FROM resume_analysis ra
            JOIN resumes r ON r.resume_id = ra.resume_id
            WHERE ra.user_id = ?
            ORDER BY ra.analyzed_at DESC
        """, (user_id,))
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        st.info("You haven't analyzed any resumes yet.")
        if st.button("Upload your first resume"):
            go_to("upload")
            st.rerun()
        return

    df = pd.DataFrame(rows)
    df_display = df.rename(columns={
        "file_name": "File", "ats_score": "Score",
        "analysis_mode": "Mode", "analyzed_at": "Date"
    })[["File", "Score", "Mode", "Date"]]

    st.dataframe(df_display, use_container_width=True, hide_index=True)

    if len(df) >= 2:
        st.write("")
        st.markdown("#### Compare two versions")
        c1, c2 = st.columns(2)
        labels = [f"{r['file_name']} ({r['analyzed_at']}) — {r['ats_score']}/100" for r in rows]
        with c1:
            v1 = st.selectbox("Version A", labels, index=min(1, len(labels)-1))
        with c2:
            v2 = st.selectbox("Version B", labels, index=0)

        score1 = rows[labels.index(v1)]["ats_score"]
        score2 = rows[labels.index(v2)]["ats_score"]
        diff = round(score2 - score1, 1)

        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            _stat_card("Version A", f"{score1}/100")
        with cc2:
            _stat_card("Version B", f"{score2}/100")
        with cc3:
            arrow = "📈" if diff > 0 else ("📉" if diff < 0 else "➡️")
            _stat_card(f"Change {arrow}", f"{'+' if diff >= 0 else ''}{diff}")
