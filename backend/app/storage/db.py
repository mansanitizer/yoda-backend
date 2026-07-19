from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


DB_PATH = Path(__file__).resolve().parents[1] / "data" / "boxing_backend.sqlite3"
DEFAULT_USER_ID = "amarnath"
DEFAULT_USERNAME = "amarnath"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                state TEXT NOT NULL,
                current_command TEXT,
                current_event_id TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                command_displayed_at TEXT NOT NULL,
                command TEXT NOT NULL,
                action TEXT,
                action_at TEXT,
                status TEXT NOT NULL,
                confidence REAL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            );
            """
        )
        connection.execute("DELETE FROM users")
        connection.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            """,
            (DEFAULT_USER_ID, DEFAULT_USERNAME),
        )


def upsert_user(user_id: str, username: str) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM users")
        connection.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username
            """,
            (DEFAULT_USER_ID, DEFAULT_USERNAME),
        )


def get_user(user_id: str) -> Optional[sqlite3.Row]:
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT user_id, username
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()


def upsert_session(session_id: str, started_at: str, updated_at: str, state: str, current_command: Optional[str], current_event_id: Optional[str]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sessions (session_id, started_at, updated_at, state, current_command, current_event_id)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                state = excluded.state,
                current_command = excluded.current_command,
                current_event_id = excluded.current_event_id
            """,
            (session_id, started_at, updated_at, state, current_command, current_event_id),
        )


def insert_event(event_id: str, session_id: str, command_displayed_at: str, command: str, status: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO events (event_id, session_id, command_displayed_at, command, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (event_id, session_id, command_displayed_at, command, status),
        )


def finalize_event(event_id: str, action: str, action_at: str, status: str, confidence: Optional[float]) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE events
            SET action = ?, action_at = ?, status = ?, confidence = ?
            WHERE event_id = ?
            """,
            (action, action_at, status, confidence, event_id),
        )
