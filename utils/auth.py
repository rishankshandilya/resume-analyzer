"""
auth.py
-------
Handles everything related to user identity:
  - Registering new users (with password hashing)
  - Logging users in (verifying password against stored hash)
  - Recording login attempts in login_history (audit trail)

SECURITY NOTE:
We NEVER store plain-text passwords. We use bcrypt, which:
  1. Adds a random "salt" to each password before hashing, so two users
     with the same password get completely different hashes.
  2. Is deliberately slow, which makes brute-force attacks impractical.
This is the same class of algorithm used by real production systems.
"""

import bcrypt
import re
from utils.database import db_cursor


class AuthError(Exception):
    """Custom exception so the UI layer can catch auth-specific failures
    and show a friendly message instead of a raw stack trace."""
    pass


def _hash_password(plain_password: str) -> str:
    """Converts a plain-text password into a bcrypt hash (safe to store)."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")  # store as text in the DB


def _verify_password(plain_password: str, stored_hash: str) -> bool:
    """Checks a login attempt's password against the stored hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))


def _is_valid_email(email: str) -> bool:
    """Basic email format check using a regular expression."""
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(pattern, email) is not None


def register_user(full_name: str, email: str, password: str) -> int:
    """
    Creates a new user account.
    Returns the new user_id on success.
    Raises AuthError with a human-readable message on failure.
    """
    full_name = full_name.strip()
    email = email.strip().lower()

    if not full_name:
        raise AuthError("Please enter your full name.")
    if not _is_valid_email(email):
        raise AuthError("Please enter a valid email address.")
    if len(password) < 6:
        raise AuthError("Password must be at least 6 characters long.")

    with db_cursor() as cur:
        cur.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        if cur.fetchone():
            raise AuthError("An account with this email already exists. Please log in instead.")

    password_hash = _hash_password(password)

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name, email, password_hash),
        )
        new_user_id = cur.lastrowid

    return new_user_id


def login_user(email: str, password: str) -> dict:
    """
    Verifies credentials and returns the user's info as a dict if successful.
    Every attempt (success or failure) is logged to login_history.
    Raises AuthError on invalid credentials.
    """
    email = email.strip().lower()

    with db_cursor() as cur:
        cur.execute(
            "SELECT user_id, full_name, email, password_hash FROM users WHERE email = ?",
            (email,),
        )
        row = cur.fetchone()

    if row is None:
        _log_login_attempt(user_id=None, email=email, success=False)
        raise AuthError("No account found with that email.")

    if not _verify_password(password, row["password_hash"]):
        _log_login_attempt(user_id=row["user_id"], email=email, success=False)
        raise AuthError("Incorrect password. Please try again.")

    _log_login_attempt(user_id=row["user_id"], email=email, success=True)

    return {
        "user_id": row["user_id"],
        "full_name": row["full_name"],
        "email": row["email"],
    }


def _log_login_attempt(user_id, email: str, success: bool):
    """Writes one row to login_history. Used for both successful and failed attempts."""
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO login_history (user_id, email_used, success) VALUES (?, ?, ?)",
            (user_id, email, 1 if success else 0),
        )


def get_login_history(user_id: int, limit: int = 10):
    """Returns the most recent login attempts for a given user (for a security/profile page)."""
    with db_cursor() as cur:
        cur.execute(
            """SELECT email_used, success, login_time
               FROM login_history
               WHERE user_id = ?
               ORDER BY login_time DESC
               LIMIT ?""",
            (user_id, limit),
        )
        return cur.fetchall()
