from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "app.db"
LEADS_PATH = DATA_DIR / "leads.csv"


SHORT_TERM_MEMORY: dict[str, dict[str, Any]] = {}


def initialize_storage() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            budget_aed INTEGER,
            preferences TEXT NOT NULL DEFAULT '{}',
            liked_listing_ids TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            listing_id INTEGER NOT NULL,
            viewing_datetime TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    connection.commit()
    connection.close()

    if not LEADS_PATH.exists():
        with open(
            LEADS_PATH,
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "created_at",
                    "user_id",
                    "name",
                    "budget_aed",
                    "needs",
                    "listing_id",
                ],
            )
            writer.writeheader()


def get_session(session_id: str) -> dict[str, Any]:
    if session_id not in SHORT_TERM_MEMORY:
        SHORT_TERM_MEMORY[session_id] = {
            "messages": [],
            "last_results": [],
            "selected_listing_id": None,
        }

    return SHORT_TERM_MEMORY[session_id]


def save_session_message(
    session_id: str,
    role: str,
    content: str,
) -> None:
    session = get_session(session_id)

    session["messages"].append(
        {
            "role": role,
            "content": content,
        }
    )

    session["messages"] = session["messages"][-12:]


def set_last_results(
    session_id: str,
    results: list[dict[str, Any]],
) -> None:
    session = get_session(session_id)

    session["last_results"] = results

    if results:
        session["selected_listing_id"] = results[0]["listing_id"]
    else:
        session["selected_listing_id"] = None


def get_last_results(session_id: str) -> dict[str, Any]:
    session = get_session(session_id)

    return {
        "selected_listing_id": session.get(
            "selected_listing_id"
        ),
        "last_results": session.get(
            "last_results",
            [],
        ),
    }


def safe_json_loads(
    value: Optional[str],
    default: Any,
) -> Any:
    if not value:
        return default

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def get_user_profile(
    user_id: str,
) -> Optional[dict[str, Any]]:
    initialize_storage()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            name,
            budget_aed,
            preferences,
            liked_listing_ids,
            updated_at
        FROM user_profiles
        WHERE user_id = ?
        """,
        (user_id,),
    )

    row = cursor.fetchone()
    connection.close()

    if row is None:
        return None

    return {
        "user_id": row[0],
        "name": row[1],
        "budget_aed": row[2],
        "preferences": safe_json_loads(row[3], {}),
        "liked_listing_ids": safe_json_loads(row[4], []),
        "updated_at": row[5],
    }


def save_user_profile(
    user_id: str,
    name: Optional[str] = None,
    budget_aed: Optional[int] = None,
    preferences: Optional[dict[str, Any]] = None,
    liked_listing_ids: Optional[list[int]] = None,
) -> None:
    initialize_storage()

    existing = get_user_profile(user_id) or {}

    final_name = (
        name
        if name is not None and name.strip()
        else existing.get("name")
    )

    final_budget = (
        budget_aed
        if budget_aed is not None
        else existing.get("budget_aed")
    )

    final_preferences = (
        preferences
        if preferences is not None
        else existing.get("preferences", {})
    )

    final_liked_listing_ids = (
        liked_listing_ids
        if liked_listing_ids is not None
        else existing.get("liked_listing_ids", [])
    )

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO user_profiles (
            user_id,
            name,
            budget_aed,
            preferences,
            liked_listing_ids,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            name = excluded.name,
            budget_aed = excluded.budget_aed,
            preferences = excluded.preferences,
            liked_listing_ids = excluded.liked_listing_ids,
            updated_at = excluded.updated_at
        """,
        (
            user_id,
            final_name,
            final_budget,
            json.dumps(final_preferences),
            json.dumps(final_liked_listing_ids),
            datetime.now().isoformat(),
        ),
    )

    connection.commit()
    connection.close()


def save_lead(
    user_id: str,
    name: str,
    budget_aed: Optional[int],
    needs: str,
    listing_id: Optional[int],
) -> None:
    initialize_storage()

    with open(
        LEADS_PATH,
        "a",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "created_at",
                "user_id",
                "name",
                "budget_aed",
                "needs",
                "listing_id",
            ],
        )

        writer.writerow(
            {
                "created_at": datetime.now().isoformat(),
                "user_id": user_id,
                "name": name,
                "budget_aed": budget_aed,
                "needs": needs,
                "listing_id": listing_id,
            }
        )


def save_booking(
    user_id: str,
    listing_id: int,
    viewing_datetime: str,
) -> int:
    initialize_storage()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO bookings (
            user_id,
            listing_id,
            viewing_datetime,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            listing_id,
            viewing_datetime,
            datetime.now().isoformat(),
        ),
    )

    booking_id = cursor.lastrowid

    connection.commit()
    connection.close()

    return int(booking_id)


initialize_storage()