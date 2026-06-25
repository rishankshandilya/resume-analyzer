"""
database.py
-----------
Handles all database setup and connections for the AI Resume Analyzer.

We use SQLite instead of MySQL for this project because:
- Zero setup required (no separate database server to install/run)
- The entire database lives in a single file (resume_analyzer.db)
- It works identically on your laptop AND on Streamlit Cloud (free hosting)
- It still uses real SQL (CREATE TABLE, FOREIGN KEY, INDEX, etc.) so every
  concept you'd explain about MySQL applies here too - just swap the word
  "MySQL" for "SQLite" in an interview and the architecture story holds.

Tables:
  1. users            - login credentials (hashed passwords only, never plain text)
  2. resumes           - every resume file a user has uploaded
  3. resume_analysis    - the ATS score + breakdown for each uploaded resume
  4. login_history       - audit log of every login attempt (security feature)
"""

import sqlite3
import os
from contextlib import contextmanager

# The .db file will be created in a top-level /data folder, regardless
# of where this module is imported from (project root, not utils/).
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "resume_analyzer.db")


def get_connection():
    """
    Opens a new SQLite connection.
    `check_same_thread=False` is needed because Streamlit can call this
    from different internal threads during a single user session.
    `row_factory = sqlite3.Row` lets us access columns by name (like a dict)
    instead of only by index - much easier to read in the rest of the app.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite ignores FKs unless told to enforce them
    return conn


@contextmanager
def db_cursor(commit=False):
    """
    A context manager so the rest of the codebase can do:

        with db_cursor(commit=True) as cur:
            cur.execute("INSERT INTO ...")

    instead of manually opening/closing connections everywhere.
    This guarantees the connection is always closed, even if an error occurs.
    """
    conn = get_connection()
    cur = conn.cursor()
    try:
        yield cur
        if commit:
            conn.commit()
    finally:
        conn.close()


def init_db():
    """
    Creates all tables if they don't already exist.
    Safe to call every time the app starts (CREATE TABLE IF NOT EXISTS).
    """
    with db_cursor(commit=True) as cur:

        # ---------------------------------------------------------
        # USERS TABLE
        # Stores login credentials. Password is NEVER stored as plain
        # text - only the bcrypt hash is saved (see auth.py).
        # ---------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name     TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ---------------------------------------------------------
        # RESUMES TABLE
        # Every file a user uploads gets a row here, regardless of
        # whether it's their 1st or 10th upload. This is what powers
        # the "Resume History" feature.
        # ---------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                resume_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                file_name     TEXT NOT NULL,
                file_type     TEXT NOT NULL,          -- 'pdf' or 'docx'
                raw_text      TEXT,                    -- extracted text content
                uploaded_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # ---------------------------------------------------------
        # RESUME_ANALYSIS TABLE
        # One row per analysis run on a resume. Stores the final score
        # AND the category breakdown so charts/history can be rebuilt
        # without re-running the analysis.
        # ---------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS resume_analysis (
                analysis_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id          INTEGER NOT NULL,
                user_id            INTEGER NOT NULL,
                ats_score          REAL NOT NULL,
                contact_score      REAL,
                education_score    REAL,
                skills_score       REAL,
                projects_score     REAL,
                experience_score   REAL,
                formatting_score   REAL,
                keywords_score     REAL,
                length_score       REAL,
                skills_found       TEXT,        -- comma-separated
                skills_missing     TEXT,        -- comma-separated
                suggestions        TEXT,        -- newline-separated
                analysis_mode      TEXT,        -- 'AI' or 'Rule-Based'
                analyzed_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resume_id) REFERENCES resumes(resume_id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # ---------------------------------------------------------
        # LOGIN_HISTORY TABLE
        # Security/audit feature: records every login attempt
        # (successful or failed) with a timestamp.
        # ---------------------------------------------------------
        cur.execute("""
            CREATE TABLE IF NOT EXISTS login_history (
                login_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                email_used   TEXT NOT NULL,
                success      INTEGER NOT NULL,     -- 1 = success, 0 = failed
                login_time   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        """)

        # ---------------------------------------------------------
        # INDEXES
        # Speed up the lookups we do most often: finding a user by
        # email at login, and finding all resumes/analyses for a user.
        # ---------------------------------------------------------
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_resumes_user ON resumes(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_user ON resume_analysis(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_analysis_resume ON resume_analysis(resume_id)")


if __name__ == "__main__":
    # Running `python database.py` directly will just set up the DB file.
    init_db()
    print(f"Database initialized at: {DB_PATH}")
