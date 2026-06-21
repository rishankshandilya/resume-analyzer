"""
ats_engine.py
--------------
The core scoring engine. Evaluates a resume across 8 categories and
produces a final score out of 100, plus actionable suggestions.

SCORING FORMULA (out of 100):
    Contact Information   -> 10 points
    Education              -> 10 points
    Skills                  -> 20 points
    Projects                  -> 15 points
    Experience                  -> 15 points
    Formatting                    -> 10 points
    Keywords (role match)          -> 15 points
    Resume Length                    -> 5 points
    --------------------------------------------
    TOTAL                              100 points

Each category is scored independently by its own method, which makes
the engine easy to test, explain, and extend (e.g., add a 9th category
later without touching the others).
"""

import re
from utils.skill_extractor import extract_skills, find_missing_skills


class ATSEngine:
    """
    Usage:
        engine = ATSEngine(resume_text, target_role="Data Analyst")
        result = engine.analyze()
        # result is a dict with score, breakdown, found/missing skills, suggestions
    """

    # Weight of each category - must sum to 100
    WEIGHTS = {
        "contact": 10,
        "education": 10,
        "skills": 20,
        "projects": 15,
        "experience": 15,
        "formatting": 10,
        "keywords": 15,
        "length": 5,
    }

    EDUCATION_KEYWORDS = [
        "bachelor", "master", "b.tech", "m.tech", "b.e", "m.e", "b.sc", "m.sc",
        "bca", "mca", "mba", "degree", "university", "college", "cgpa", "gpa", "diploma"
    ]

    PROJECT_KEYWORDS = ["project", "built", "developed", "designed", "implemented", "created"]

    EXPERIENCE_KEYWORDS = [
        "experience", "internship", "intern", "worked at", "company",
        "responsibilities", "role", "employed"
    ]

    ACHIEVEMENT_PATTERN = re.compile(r"\b\d+%|\b\d+\s?(users|hours|days|projects|times|x\b)")

    def __init__(self, resume_text: str, target_role: str = "General / Not Sure"):
        self.text = resume_text
        self.text_lower = resume_text.lower()
        self.target_role = target_role
        self.suggestions = []

    # ------------------------------------------------------------------
    # MAIN ENTRY POINT
    # ------------------------------------------------------------------
    def analyze(self) -> dict:
        """Runs every scoring sub-method and assembles the final report."""
        found_skills = extract_skills(self.text)
        missing_skills = find_missing_skills(found_skills, self.target_role)

        scores = {
            "contact": self._score_contact(),
            "education": self._score_education(),
            "skills": self._score_skills(found_skills),
            "projects": self._score_projects(),
            "experience": self._score_experience(),
            "formatting": self._score_formatting(),
            "keywords": self._score_keywords(found_skills, missing_skills),
            "length": self._score_length(),
        }

        final_score = round(sum(scores.values()), 1)

        return {
            "ats_score": final_score,
            "breakdown": scores,
            "max_breakdown": self.WEIGHTS,
            "skills_found": found_skills,
            "skills_missing": missing_skills,
            "suggestions": self.suggestions,
        }

    # ------------------------------------------------------------------
    # CATEGORY 1: CONTACT INFORMATION (10 pts)
    # Checks for email, phone number, and a LinkedIn/portfolio link.
    # ------------------------------------------------------------------
    def _score_contact(self) -> float:
        score = 0
        has_email = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", self.text) is not None
        has_phone = re.search(r"(\+?\d{1,3}[\s-]?)?\d{10}", self.text) is not None
        has_link = re.search(r"linkedin\.com|github\.com|http[s]?://", self.text_lower) is not None

        if has_email:
            score += 4
        else:
            self.suggestions.append("Add a professional email address near the top of your resume.")

        if has_phone:
            score += 3
        else:
            self.suggestions.append("Add a 10-digit phone number so recruiters can reach you.")

        if has_link:
            score += 3
        else:
            self.suggestions.append("Add a LinkedIn or GitHub link to showcase your work.")

        return score

    # ------------------------------------------------------------------
    # CATEGORY 2: EDUCATION (10 pts)
    # ------------------------------------------------------------------
    def _score_education(self) -> float:
        matches = sum(1 for kw in self.EDUCATION_KEYWORDS if kw in self.text_lower)
        if matches >= 2:
            return 10
        elif matches == 1:
            self.suggestions.append("Expand your Education section with degree name, institution, and CGPA/percentage.")
            return 6
        else:
            self.suggestions.append("Add a clear Education section (degree, college, year, CGPA).")
            return 0

    # ------------------------------------------------------------------
    # CATEGORY 3: SKILLS (20 pts)
    # Score scales with number of distinct skills detected, capped at 20.
    # ------------------------------------------------------------------
    def _score_skills(self, found_skills: list) -> float:
        count = len(found_skills)
        score = min(count * 2, 20)  # 2 points per skill, max 20
        if count < 5:
            self.suggestions.append(
                "Add a dedicated 'Skills' section listing your technical tools and languages clearly."
            )
        return score

    # ------------------------------------------------------------------
    # CATEGORY 4: PROJECTS (15 pts)
    # Looks for project keywords AND measurable achievements (numbers/%).
    # ------------------------------------------------------------------
    def _score_projects(self) -> float:
        keyword_hits = sum(1 for kw in self.PROJECT_KEYWORDS if kw in self.text_lower)
        has_metrics = bool(self.ACHIEVEMENT_PATTERN.search(self.text_lower))

        score = 0
        if keyword_hits >= 2:
            score += 10
        elif keyword_hits == 1:
            score += 5
        else:
            self.suggestions.append("Add a Projects section describing what you built and the technologies used.")

        if has_metrics:
            score += 5
        else:
            self.suggestions.append(
                "Add measurable achievements to your projects, e.g. "
                "'Reduced processing time by 40%' instead of 'Worked on optimization.'"
            )

        return score

    # ------------------------------------------------------------------
    # CATEGORY 5: EXPERIENCE (15 pts)
    # Freshers may score lower here naturally - that's expected and fine;
    # internships/projects can substitute, which the suggestion reflects.
    # ------------------------------------------------------------------
    def _score_experience(self) -> float:
        keyword_hits = sum(1 for kw in self.EXPERIENCE_KEYWORDS if kw in self.text_lower)
        if keyword_hits >= 2:
            return 15
        elif keyword_hits == 1:
            return 9
        else:
            self.suggestions.append(
                "If you don't have work experience yet, highlight internships, freelance work, "
                "or significant academic projects instead."
            )
            return 4  # small baseline so freshers aren't unfairly crushed

    # ------------------------------------------------------------------
    # CATEGORY 6: FORMATTING (10 pts)
    # Heuristics: presence of section headers, reasonable line count,
    # no excessively long unbroken paragraphs (ATS systems struggle with these).
    # ------------------------------------------------------------------
    def _score_formatting(self) -> float:
        score = 0
        common_headers = ["education", "experience", "skills", "projects", "summary", "objective"]
        headers_found = sum(1 for h in common_headers if h in self.text_lower)

        if headers_found >= 3:
            score += 6
        else:
            self.suggestions.append(
                "Use clear section headings like 'Education', 'Skills', and 'Projects' "
                "so ATS software can categorize your resume correctly."
            )

        lines = self.text.splitlines()
        avg_line_length = sum(len(l) for l in lines) / max(len(lines), 1)
        if avg_line_length < 150:
            score += 4
        else:
            self.suggestions.append(
                "Break up long paragraphs into bullet points - ATS systems and recruiters "
                "both scan bullet points more easily than dense paragraphs."
            )

        return score

    # ------------------------------------------------------------------
    # CATEGORY 7: KEYWORDS / ROLE MATCH (15 pts)
    # Compares found skills against the target role's expected skill list.
    # ------------------------------------------------------------------
    def _score_keywords(self, found_skills: list, missing_skills: list) -> float:
        total_expected = len(found_skills) + len(missing_skills)
        if total_expected == 0:
            return 0

        match_ratio = len(found_skills) / total_expected if total_expected else 0
        score = round(match_ratio * 15, 1)

        if missing_skills:
            top_missing = ", ".join(missing_skills[:5])
            self.suggestions.append(
                f"For a {self.target_role} role, consider adding these commonly expected "
                f"keywords if you have the experience: {top_missing}."
            )

        return score

    # ------------------------------------------------------------------
    # CATEGORY 8: RESUME LENGTH (5 pts)
    # Ideal fresher resume: roughly 300-700 words (about 1 page).
    # ------------------------------------------------------------------
    def _score_length(self) -> float:
        word_count = len(self.text.split())
        if 300 <= word_count <= 700:
            return 5
        elif 200 <= word_count < 300 or 700 < word_count <= 900:
            self.suggestions.append("Aim for a one-page resume (roughly 300-700 words) for best ATS and recruiter readability.")
            return 3
        else:
            if word_count < 200:
                self.suggestions.append("Your resume looks quite short - add more detail to your projects and skills.")
            else:
                self.suggestions.append("Your resume looks long - trim it down to one page by removing less relevant details.")
            return 1
