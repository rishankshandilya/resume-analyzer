"""
ai_helper.py
-------------
Implements "Hybrid AI Mode":
    - If a Gemini API key IS configured -> ask Gemini to generate richer,
      more natural-language resume feedback.
    - If a Gemini API key is NOT configured (or the call fails for any
      reason - network issue, quota, bad key, timeout) -> silently fall
      back to the local rule-based suggestions already produced by
      ats_engine.py.

GOLDEN RULE: This module must NEVER raise an exception that crashes the
app. Every external call is wrapped in try/except. The app should look
identical to the user whether AI is available or not - just smarter
when it is.
"""

import os
import streamlit as st


def _get_api_key() -> str | None:
    """
    Looks for a Gemini API key in two places, in order:
      1. Streamlit secrets (st.secrets) - used when deployed on Streamlit Cloud
      2. Environment variable GEMINI_API_KEY - used for local development
    Returns None if no key is found anywhere (this is expected and fine).
    """
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass  # st.secrets doesn't exist locally unless a secrets.toml is present - that's OK

    return os.environ.get("GEMINI_API_KEY")


def is_ai_available() -> bool:
    """Quick check the UI can use to show 'AI Mode: ON/OFF' to the user."""
    return _get_api_key() is not None


def get_ai_suggestions(resume_text: str, ats_result: dict, target_role: str) -> tuple[list, str]:
    """
    Attempts to generate AI-powered suggestions using Gemini.

    Returns a tuple: (suggestions_list, mode_used)
        mode_used is either "AI" or "Rule-Based" - the UI displays this
        so the user always knows which mode produced their feedback.

    On ANY failure, falls back to the rule-based suggestions that were
    already computed by ats_engine.py and passed in via ats_result.
    """
    api_key = _get_api_key()

    # No key configured -> don't even attempt a network call.
    if not api_key:
        return ats_result["suggestions"], "Rule-Based"

    try:
        suggestions = _call_gemini(api_key, resume_text, ats_result, target_role)
        if suggestions:
            return suggestions, "AI"
        else:
            return ats_result["suggestions"], "Rule-Based"
    except Exception:
        # Any failure at all (bad key, no internet, rate limit, timeout,
        # malformed response) - we quietly fall back. The user never sees
        # an error; they just get rule-based suggestions instead.
        return ats_result["suggestions"], "Rule-Based"


def _call_gemini(api_key: str, resume_text: str, ats_result: dict, target_role: str) -> list:
    """
    Makes the actual call to Gemini's free-tier API.
    Imports google.generativeai lazily, inside the function, so that the
    rest of the app works fine even if that package isn't installed -
    it's only needed when AI mode is actually used.
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")  # fast + free-tier friendly

    found = ", ".join(ats_result["skills_found"]) or "none detected"
    missing = ", ".join(ats_result["skills_missing"]) or "none"

    prompt = f"""You are an expert resume reviewer helping a fresher targeting a {target_role} role.

Resume text:
---
{resume_text[:3000]}
---

ATS Score: {ats_result['ats_score']}/100
Skills found: {found}
Skills missing for this role: {missing}

Give exactly 5 short, specific, actionable suggestions to improve this resume.
Each suggestion should be one sentence. Do not use markdown formatting.
Return ONLY the 5 suggestions, one per line, no numbering, no preamble."""

    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.4, "max_output_tokens": 400},
    )

    text = response.text.strip()
    lines = [line.strip("-• \t") for line in text.split("\n") if line.strip()]

    return lines[:5] if lines else []
