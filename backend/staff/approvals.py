"""
Queries for the staff approval queue. This table is the actual answer
to "what's waiting for review right now" -- LangGraph's interrupt state
lives inside the checkpointer, keyed by thread_id, which isn't something
you can practically query as "give me every paused conversation." This
table is the deliberate, queryable record of that instead.
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connection import get_connection


def create_pending_approval(customer_id: int, tool_name: str, tool_args: dict) -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    row = conn.execute(
        "INSERT INTO pending_approvals (customer_id, tool_name, tool_args, created_at) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (customer_id, tool_name, json.dumps(tool_args), now),
    ).fetchone()
    conn.commit()
    conn.close()
    return row["id"]


def list_pending_approvals() -> list[dict]:
    """Every approval still waiting on a decision, oldest first -- a
    real queue, not just a flat list, since the oldest unresolved
    request is the one staff should probably look at first."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT pa.id, pa.customer_id, pa.tool_name, pa.tool_args, pa.created_at,
                  c.name AS customer_name, c.tier AS customer_tier
           FROM pending_approvals pa
           JOIN customers c ON c.id = pa.customer_id
           WHERE pa.status = 'pending'
           ORDER BY pa.created_at ASC"""
    ).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        d["tool_args"] = json.loads(d["tool_args"])
        results.append(d)
    return results


def get_pending_approval(approval_id: int) -> Optional[dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM pending_approvals WHERE id = %s", (approval_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["tool_args"] = json.loads(d["tool_args"])
    return d


def resolve_pending_approval(approval_id: int, approved: bool, resolved_by: str) -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    status = "approved" if approved else "declined"
    conn = get_connection()
    conn.execute(
        "UPDATE pending_approvals SET status = %s, resolved_at = %s, resolved_by = %s WHERE id = %s",
        (status, now, resolved_by, approval_id),
    )
    conn.commit()
    conn.close()