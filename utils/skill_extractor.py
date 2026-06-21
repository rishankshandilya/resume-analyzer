"""
skill_extractor.py
--------------------
Detects which skills appear in a resume's text, and compares them
against role-specific "expected skill" lists to find gaps.

Approach: keyword/phrase matching with word-boundary regex.
This is intentionally simple and explainable (good for interviews) -
no black-box ML model needed for a v1 of this feature.
"""

import re

# ---------------------------------------------------------------------
# SKILL DATABASE
# Organized by category. Add new skills here to expand detection -
# the rest of the app needs no changes (Open/Closed Principle).
# ---------------------------------------------------------------------
SKILL_DATABASE = {
    "Programming Languages": [
        "Python", "Java", "C++", "C", "JavaScript", "TypeScript", "SQL", "R", "Go", "Scala"
    ],
    "Data & Analytics": [
        "Pandas", "NumPy", "Matplotlib", "Seaborn", "Power BI", "Tableau",
        "Excel", "SciPy", "Scikit-learn", "Statistics", "Data Visualization",
        "Data Cleaning", "ETL"
    ],
    "Web Development": [
        "HTML", "CSS", "React", "Django", "Flask", "Streamlit", "Node.js",
        "REST API", "FastAPI", "Bootstrap"
    ],
    "Databases": [
        "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "Redis"
    ],
    "Machine Learning / AI": [
        "Machine Learning", "Deep Learning", "NLP", "TensorFlow", "PyTorch",
        "Keras", "Computer Vision", "OpenCV", "Neural Networks"
    ],
    "Cloud & DevOps": [
        "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Git", "GitHub",
        "CI/CD", "Linux", "Jenkins"
    ],
    "Soft / Tools": [
        "Communication", "Teamwork", "Leadership", "Problem Solving",
        "Jira", "Agile", "Scrum"
    ],
}

# Flatten into a single list for fast lookups
ALL_SKILLS = [skill for skills in SKILL_DATABASE.values() for skill in skills]

# ---------------------------------------------------------------------
# ROLE PROFILES
# Defines which skills are "expected" for a target role. This powers
# the "Missing Skills" feature - comparing what's found vs. what's expected.
# ---------------------------------------------------------------------
ROLE_PROFILES = {
    "Python Developer": [
        "Python", "SQL", "Django", "Flask", "REST API", "Git", "MySQL",
        "PostgreSQL", "Docker", "Linux"
    ],
    "Data Analyst": [
        "Python", "SQL", "Excel", "Pandas", "NumPy", "Power BI", "Tableau",
        "Data Visualization", "Statistics", "Data Cleaning"
    ],
    "General / Not Sure": ALL_SKILLS[:15],  # a broad sample if user has no target role
}


def extract_skills(resume_text: str) -> list:
    """
    Scans resume text and returns a sorted list of skills found,
    matched against the master SKILL_DATABASE.
    Uses word-boundary regex so 'R' doesn't match inside 'Strategic', etc.
    """
    found = []
    text_lower = resume_text.lower()

    for skill in ALL_SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, text_lower):
            found.append(skill)

    return sorted(set(found))


def find_missing_skills(found_skills: list, target_role: str) -> list:
    """
    Compares found skills against the expected list for a target role.
    Returns skills that are expected but NOT present in the resume.
    """
    expected = ROLE_PROFILES.get(target_role, ROLE_PROFILES["General / Not Sure"])
    found_set = set(found_skills)
    missing = [skill for skill in expected if skill not in found_set]
    return missing


def get_available_roles() -> list:
    """Returns the list of role names the user can pick from in the UI dropdown."""
    return list(ROLE_PROFILES.keys())
