"""
Auth-specific database queries. Deliberately separate from agent/tools.py
-- those are tools the LLM can call; these never should be.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connection import get_connection
from models import User, Customer


def get_user_by_email(email: str) -> Optional[User]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    conn.close()
    return User(**dict(row)) if row else None


def get_user_by_id(user_id: int) -> Optional[User]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()
    conn.close()
    return User(**dict(row)) if row else None


def create_customer_and_user(name: str, email: str, password_hash: str) -> User:
    """Signup creates both rows at once: a customer profile (business
    data) and a user credential (how they log in), linked together."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()

    customer_row = conn.execute(
        """INSERT INTO customers (name, email, phone, tier, signup_date, satisfaction_score)
           VALUES (%s, %s, NULL, 'free', %s, NULL) RETURNING id""",
        (name, email, now),
    ).fetchone()
    customer_id = customer_row["id"]

    user_row = conn.execute(
        "INSERT INTO users (customer_id, email, password_hash, created_at) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (customer_id, email, password_hash, now),
    ).fetchone()

    conn.commit()
    row = conn.execute("SELECT * FROM users WHERE id = %s", (user_row["id"],)).fetchone()
    conn.close()
    return User(**dict(row))


def get_customer(customer_id: int) -> Optional[Customer]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = %s", (customer_id,)).fetchone()
    conn.close()
    return Customer(**dict(row)) if row else None