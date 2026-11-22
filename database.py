"""SQLite persistence for CivicPulse AI."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "civic_pulse.db"


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    """Create the complaints table if it does not already exist."""
    with _connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS complaints (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                location TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'Medium',
                image_path TEXT,
                after_image_path TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                upvotes INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                report_count INTEGER NOT NULL DEFAULT 1,
                verification_score REAL,
                assigned_authority TEXT
            )"""
        )
        connection.execute(
            """CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                full_name TEXT,
                password_hash TEXT,
                auth_provider TEXT NOT NULL DEFAULT 'email',
                coins INTEGER NOT NULL DEFAULT 0,
                reports_count INTEGER NOT NULL DEFAULT 0
            )"""
        )
        user_migrations = (
            ("full_name", "TEXT"),
            ("password_hash", "TEXT"),
            ("auth_provider", "TEXT DEFAULT 'email'"),
            ("coins", "INTEGER DEFAULT 0"),
            ("reports_count", "INTEGER DEFAULT 0"),
        )
        existing_user_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(users)").fetchall()
        }
        for column, definition in user_migrations:
            if column not in existing_user_columns:
                try:
                    connection.execute(
                        f"ALTER TABLE users ADD COLUMN {column} {definition}"
                    )
                except sqlite3.OperationalError:
                    # A second app process may have completed this migration.
                    pass
        # Migrate existing Day 1 databases one column at a time.
        migrations = (
            ("report_count", "INTEGER NOT NULL DEFAULT 1"),
            ("severity", "TEXT DEFAULT 'Medium'"),
            ("status", "TEXT DEFAULT 'Pending'"),
            ("after_image_path", "TEXT"),
            ("verification_score", "REAL"),
            ("citizen_email", "TEXT"),
            ("assigned_authority", "TEXT"),
        )
        existing = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(complaints)").fetchall()
        }
        for column, definition in migrations:
            if column not in existing:
                try:
                    connection.execute(
                        f"ALTER TABLE complaints ADD COLUMN {column} {definition}"
                    )
                except sqlite3.OperationalError:
                    # Another app process may have migrated it after PRAGMA.
                    pass
        connection.execute(
            "UPDATE complaints SET report_count = 1 WHERE report_count IS NULL"
        )
        connection.execute(
            """UPDATE complaints
               SET status = CASE WHEN COALESCE(report_count, 1) >= 3
                                 THEN 'Escalated to Central Municipal HQ'
                                 ELSE 'Assigned to Mandal/District Office' END,
                   assigned_authority = CASE WHEN COALESCE(report_count, 1) >= 3
                       THEN 'Tier 2: Central Municipal Headquarters (High-Level Escalation)'
                       ELSE 'Tier 1: ' || location || ' Mandal / District Municipal Office' END
               WHERE status IN ('Pending', 'Open', 'In Progress')"""
        )
        connection.execute(
            """UPDATE complaints
               SET assigned_authority = CASE WHEN COALESCE(report_count, 1) >= 3
                   THEN 'Tier 2: Central Municipal Headquarters (High-Level Escalation)'
                   ELSE 'Tier 1: ' || location || ' Mandal / District Municipal Office' END
               WHERE assigned_authority IS NULL"""
        )


def find_matching_complaint(
    location: str, category: str, description: str
) -> dict[str, Any] | None:
    """Return a matching open complaint, if one exists."""
    from ai_engine import is_duplicate_issue

    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """SELECT * FROM complaints
               WHERE status IN ('Pending', 'In Progress',
                                'Assigned to Mandal/District Office',
                                'Escalated to Central Municipal HQ') AND category = ?
               ORDER BY created_at DESC, id DESC""",
            (category,),
        ).fetchall()
    for row in rows:
        complaint = dict(row)
        if is_duplicate_issue(
            location, description, complaint["location"],
            complaint["description"], same_category=True,
        ):
            return complaint
    return None


def increment_duplicate_report(
    tracking_id: str, citizen_email: str | None = None
) -> int:
    """Increment report count; repeated reports automatically become Critical."""
    init_db()
    normalized_id = tracking_id.strip().upper()
    with _connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        current = connection.execute(
            "SELECT report_count, location, status FROM complaints WHERE id = ?",
            (normalized_id,),
        ).fetchone()
        if not current or current["status"] == "Verified Resolved":
            return 0
        next_count = int(current["report_count"] or 1) + 1
        escalated = next_count >= 3
        next_status = (
            "Escalated to Central Municipal HQ"
            if escalated else "Assigned to Mandal/District Office"
        )
        authority = (
            "Tier 2: Central Municipal Headquarters (High-Level Escalation)"
            if escalated else
            f"Tier 1: {current['location']} Mandal / District Municipal Office"
        )
        connection.execute(
            """UPDATE complaints
               SET report_count = ?, status = ?, assigned_authority = ?,
                   severity = CASE
                       WHEN ? >= 2 THEN 'Critical'
                       ELSE severity
                   END
                   , citizen_email = COALESCE(?, citizen_email)
               WHERE id = ?""",
            (
                next_count,
                next_status,
                authority,
                next_count,
                citizen_email.strip().lower() if citizen_email else None,
                normalized_id,
            ),
        )
        row = connection.execute(
            "SELECT report_count FROM complaints WHERE id = ?", (normalized_id,)
        ).fetchone()
    return int(row["report_count"]) if row else 0


def _next_id(connection: sqlite3.Connection) -> str:
    """Generate a sequential CP identifier, starting at CP-1001."""
    row = connection.execute(
        "SELECT MAX(CAST(SUBSTR(id, 4) AS INTEGER)) AS max_id "
        "FROM complaints WHERE id GLOB 'CP-[0-9]*'"
    ).fetchone()
    return f"CP-{max(1000, row['max_id'] or 1000) + 1}"


def add_complaint(
    category: str,
    description: str,
    location: str,
    severity: str,
    image_path: str | None = None,
    after_image_path: str | None = None,
    citizen_email: str | None = None,
) -> str:
    """Insert a complaint and return its tracking ID."""
    init_db()
    with _connect() as connection:
        complaint_id = _next_id(connection)
        connection.execute(
            """INSERT INTO complaints
            (id, category, description, location, severity, image_path,
             after_image_path, created_at, status, citizen_email,
             assigned_authority)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Assigned to Mandal/District Office', ?, ?)""",
            (
                complaint_id,
                category,
                description,
                location,
                severity,
                image_path,
                after_image_path,
                datetime.now().astimezone().isoformat(timespec="seconds"),
                citizen_email.strip().lower() if citizen_email else None,
                f"Tier 1: {location.strip()} Mandal / District Municipal Office",
            ),
        )
    return complaint_id


def get_all_complaints() -> list[dict[str, Any]]:
    """Return complaints with critical, frequently reported issues first."""
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """SELECT * FROM complaints
               ORDER BY CASE WHEN severity = 'Critical' THEN 0 ELSE 1 END,
                        COALESCE(report_count, 1) DESC,
                        created_at DESC, id DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def resolve_complaint_with_proof(
    tracking_id: str, after_image_path: str, verification_score: float
) -> bool:
    """Save verified repair evidence and close an open complaint."""
    init_db()
    with _connect() as connection:
        normalized_id = tracking_id.strip().upper()
        complaint = connection.execute(
            """SELECT citizen_email FROM complaints
               WHERE id = ? AND status IN ('Pending', 'Open', 'In Progress',
                   'Assigned to Mandal/District Office', 'Escalated to Central Municipal HQ')""",
            (normalized_id,),
        ).fetchone()
        if not complaint:
            return False
        cursor = connection.execute(
            """UPDATE complaints
               SET after_image_path = ?, verification_score = ?,
                   status = 'Verified Resolved'
               WHERE id = ? AND status IN ('Pending', 'Open', 'In Progress',
                   'Assigned to Mandal/District Office', 'Escalated to Central Municipal HQ')""",
            (after_image_path, float(verification_score), normalized_id),
        )
        citizen_email = (complaint["citizen_email"] or "").strip().lower()
        if cursor.rowcount > 0 and citizen_email:
            connection.execute(
                "INSERT OR IGNORE INTO users (email) VALUES (?)", (citizen_email,)
            )
            connection.execute(
                "UPDATE users SET coins = coins + 50 WHERE email = ?",
                (citizen_email,),
            )
    return cursor.rowcount > 0


def get_or_create_user(email: str) -> dict[str, Any]:
    """Return a citizen wallet, creating a zero-balance wallet when needed."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Email is required to access a CivicCoins wallet.")
    init_db()
    with _connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users (email) VALUES (?)", (normalized_email,)
        )
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
    return dict(row)


_PASSWORD_ITERATIONS = 260_000


def _hash_password(password: str, salt: bytes | None = None) -> str:
    """Create a salted PBKDF2-HMAC-SHA256 password hash."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS
    )
    return f"pbkdf2_sha256${_PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def register_user_with_password(
    full_name: str, email: str, password: str
) -> tuple[bool, str]:
    """Create a password account using a salted SHA-256 key derivation."""
    normalized_email = email.strip().lower()
    normalized_name = full_name.strip()
    if not normalized_name or not normalized_email or not password:
        return False, "Full name, email, and password are required"
    password_hash = _hash_password(password)
    init_db()
    with _connect() as connection:
        try:
            connection.execute(
                """INSERT INTO users (email, full_name, password_hash, auth_provider)
                   VALUES (?, ?, ?, 'email')""",
                (normalized_email, normalized_name, password_hash),
            )
        except sqlite3.IntegrityError:
            return False, "Email already registered"
    return True, "Account created!"


def login_user_with_password(
    email: str, password: str
) -> tuple[bool, dict[str, Any] | str]:
    """Verify an email/password pair without exposing password hashes."""
    normalized_email = email.strip().lower()
    if not normalized_email or not password:
        return False, "Invalid email or password"
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
    if not row or not row["password_hash"]:
        return False, "Invalid email or password"
    try:
        algorithm, iterations, salt_hex, expected_hex = row["password_hash"].split("$")
        if algorithm != "pbkdf2_sha256":
            return False, "Invalid email or password"
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        ).hex()
    except (ValueError, TypeError):
        return False, "Invalid email or password"
    if not hmac.compare_digest(actual, expected_hex):
        return False, "Invalid email or password"
    user = dict(row)
    user.pop("password_hash", None)
    return True, user


def login_with_google_sim(
    email: str, full_name: str | None = None
) -> dict[str, Any]:
    """Create or fetch a Google-linked profile (local simulation, no OAuth)."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Email is required for Google sign-in.")
    display_name = (full_name or "").strip() or normalized_email.split("@", 1)[0].replace(".", " ").title()
    init_db()
    with _connect() as connection:
        connection.execute(
            """INSERT OR IGNORE INTO users (email, full_name, auth_provider)
               VALUES (?, ?, 'google')""",
            (normalized_email, display_name),
        )
        connection.execute(
            """UPDATE users
               SET full_name = CASE
                       WHEN full_name IS NULL OR full_name = '' THEN ? ELSE full_name
                   END,
                   auth_provider = 'google'
               WHERE email = ?""",
            (display_name, normalized_email),
        )
        row = connection.execute(
            "SELECT * FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
    user = dict(row)
    user.pop("password_hash", None)
    return user


def award_civic_coins(email: str, points: int) -> int:
    """Add points to a wallet and return its updated balance."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Email is required to award CivicCoins.")
    if points < 0:
        raise ValueError("Points cannot be negative.")
    init_db()
    with _connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users (email) VALUES (?)", (normalized_email,)
        )
        connection.execute(
            "UPDATE users SET coins = coins + ? WHERE email = ?",
            (int(points), normalized_email),
        )
        row = connection.execute(
            "SELECT coins FROM users WHERE email = ?", (normalized_email,)
        ).fetchone()
    return int(row["coins"])


def record_citizen_report(email: str, points: int = 10) -> dict[str, Any]:
    """Record a submitted report and its instant coin reward atomically."""
    normalized_email = email.strip().lower()
    if not normalized_email:
        raise ValueError("Email is required to record a citizen report.")
    init_db()
    with _connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO users (email) VALUES (?)", (normalized_email,)
        )
        connection.execute(
            """UPDATE users SET coins = coins + ?, reports_count = reports_count + 1
               WHERE email = ?""",
            (int(points), normalized_email),
        )
        row = connection.execute(
            "SELECT email, coins, reports_count FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
    return dict(row)


def get_complaint_by_id(complaint_id: str) -> dict[str, Any] | None:
    """Look up a complaint using its tracking ID."""
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM complaints WHERE id = ?", (complaint_id.strip().upper(),)
        ).fetchone()
    return dict(row) if row else None


def update_complaint_status(complaint_id: str, status: str) -> bool:
    """Update status and return whether a complaint matched the ID."""
    allowed_statuses = {
        "Pending", "Open", "In Progress", "Resolved", "Verified Resolved"
    }
    if status not in allowed_statuses:
        raise ValueError(f"Status must be one of: {', '.join(sorted(allowed_statuses))}")
    init_db()
    with _connect() as connection:
        cursor = connection.execute(
            "UPDATE complaints SET status = ? WHERE id = ?",
            (status, complaint_id.strip().upper()),
        )
    return cursor.rowcount > 0
