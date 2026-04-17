"""
database.py - SQLite database operations for cat breed detection history.
"""

import sqlite3
import os
from datetime import datetime


DB_NAME = "cat_breed_history.db"


def get_db_path():
    """Return path to the SQLite database file."""
    try:
        from android.storage import app_storage_path  # type: ignore
        storage = app_storage_path()
    except ImportError:
        storage = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(storage, DB_NAME)


def init_db():
    """Create the history table if it does not exist."""
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                breed     TEXT    NOT NULL,
                confidence REAL   NOT NULL,
                image_path TEXT,
                timestamp TEXT    NOT NULL
            )
            """
        )
        conn.commit()


def save_detection(breed: str, confidence: float, image_path: str = ""):
    """Persist a breed detection result to the database."""
    init_db()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            "INSERT INTO history (breed, confidence, image_path, timestamp) VALUES (?, ?, ?, ?)",
            (breed, confidence, image_path, timestamp),
        )
        conn.commit()


def get_all_history():
    """Return all detection records ordered by newest first."""
    init_db()
    with sqlite3.connect(get_db_path()) as conn:
        cursor = conn.execute(
            "SELECT id, breed, confidence, image_path, timestamp FROM history ORDER BY id DESC"
        )
        return cursor.fetchall()


def delete_all_history():
    """Remove all records from the history table."""
    init_db()
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute("DELETE FROM history")
        conn.commit()
