"""
Tool functions the agent calls to interact with the support system's data.

These get bound to the LangGraph agent as tools. The docstrings aren't
just documentation -- the LLM reads them to decide when and how to call
each one, so they're written with that in mind.

Postgres notes for anyone reading this after the SQLite -> Postgres
migration: placeholders are %s (not ?), and inserts use RETURNING id
instead of cursor.lastrowid, which doesn't exist in Postgres at all.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent / "db"))
from connection import get_connection
from models import Customer, Order, Ticket, TicketMessage, KnowledgeBaseArticle


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

def get_customer(customer_id: int) -> Optional[Customer]:
    """Look up a customer by their internal ID. Returns None if not found."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = %s", (customer_id,)).fetchone()
    conn.close()
    return Customer(**dict(row)) if row else None


def get_customer_by_email(email: str) -> Optional[Customer]:
    """Look up a customer by email -- the usual way to identify who you're
    talking to at the start of a conversation. Returns None if not found."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE email = %s", (email,)).fetchone()
    conn.close()
    return Customer(**dict(row)) if row else None


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def get_customer_orders(customer_id: int) -> list[Order]:
    """Fetch every order placed by a customer, most recent first.
    Returns an empty list if the customer has no orders."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM orders WHERE customer_id = %s ORDER BY order_date DESC",
        (customer_id,),
    ).fetchall()
    conn.close()
    return [Order(**dict(r)) for r in rows]


def get_order(order_id: int) -> Optional[Order]:
    """Look up a single order by its ID. Returns None if it doesn't exist."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    conn.close()
    return Order(**dict(row)) if row else None


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

def search_knowledge_base(query: str, limit: int = 3) -> list[KnowledgeBaseArticle]:
    """Search FAQ/policy articles by keyword. Scores each article by how
    many query words appear in its title, content, or tags, and returns
    the top matches. Returns an empty list if nothing scores above zero.
    """
    words = [w.lower() for w in query.split() if len(w) > 2]
    if not words:
        return []

    conn = get_connection()
    rows = conn.execute("SELECT * FROM knowledge_base").fetchall()
    conn.close()

    scored = []
    for row in rows:
        haystack = f"{row['title']} {row['content']} {row['tags'] or ''}".lower()
        score = sum(haystack.count(w) for w in words)
        if score > 0:
            scored.append((score, row))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [KnowledgeBaseArticle(**dict(r)) for _, r in scored[:limit]]


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

def create_ticket(
    customer_id: int,
    subject: str,
    category: str,
    priority: str = "medium",
    order_id: Optional[int] = None,
) -> Ticket:
    """Open a new support ticket for a customer.
    category must be one of: billing, technical, shipping, account, other.
    priority must be one of: low, medium, high, urgent.
    Leave order_id as None if the issue isn't tied to a specific order.
    """
    now = _today()
    conn = get_connection()
    inserted = conn.execute(
        """INSERT INTO tickets
           (customer_id, order_id, subject, category, priority, status, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, 'open', %s, %s)
           RETURNING id""",
        (customer_id, order_id, subject, category, priority, now, now),
    ).fetchone()
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id = %s", (inserted["id"],)).fetchone()
    conn.close()
    return Ticket(**dict(row))


def add_ticket_message(ticket_id: int, sender: str, message: str) -> TicketMessage:
    """Log a message to a ticket's conversation thread.
    sender must be one of: customer, agent, system.
    Also bumps the ticket's updated_at timestamp."""
    now = _today()
    conn = get_connection()
    inserted = conn.execute(
        "INSERT INTO ticket_messages (ticket_id, sender, message, created_at) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (ticket_id, sender, message, now),
    ).fetchone()
    conn.execute("UPDATE tickets SET updated_at = %s WHERE id = %s", (now, ticket_id))
    conn.commit()
    row = conn.execute("SELECT * FROM ticket_messages WHERE id = %s", (inserted["id"],)).fetchone()
    conn.close()
    return TicketMessage(**dict(row))


def escalate_ticket(ticket_id: int, assigned_to: str, reason: str) -> Ticket:
    """Escalate a ticket to a human agent: sets status to 'escalated',
    assigns it, and logs a system note explaining why."""
    now = _today()
    conn = get_connection()
    conn.execute(
        "UPDATE tickets SET status = 'escalated', assigned_to = %s, updated_at = %s WHERE id = %s",
        (assigned_to, now, ticket_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM tickets WHERE id = %s", (ticket_id,)).fetchone()
    conn.close()
    add_ticket_message(ticket_id, "system", f"Ticket escalated to {assigned_to}. Reason: {reason}")
    return Ticket(**dict(row))


def get_customer_tickets(customer_id: int) -> list[Ticket]:
    """Fetch every ticket a customer has filed, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM tickets WHERE customer_id = %s ORDER BY created_at DESC",
        (customer_id,),
    ).fetchall()
    conn.close()
    return [Ticket(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Sensitive, money-moving actions -- gated behind human approval in graph.py.
# ---------------------------------------------------------------------------

def process_refund(order_id: int, reason: str) -> Order:
    """Mark an order as refunded. Sets status to 'returned'."""
    conn = get_connection()
    conn.execute("UPDATE orders SET status = 'returned' WHERE id = %s", (order_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    conn.close()
    return Order(**dict(row))


def cancel_order(order_id: int, reason: str) -> Order:
    """Cancel an order. Sets status to 'cancelled'."""
    conn = get_connection()
    conn.execute("UPDATE orders SET status = 'cancelled' WHERE id = %s", (order_id,))
    conn.commit()
    row = conn.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    conn.close()
    return Order(**dict(row))


# ---------------------------------------------------------------------------
# Long-term memory
# ---------------------------------------------------------------------------

def get_customer_memory(customer_id: int) -> str:
    """Return the agent's running summary of this customer from past
    conversations. Empty string if there's no memory yet."""
    conn = get_connection()
    row = conn.execute(
        "SELECT summary FROM customer_memory WHERE customer_id = %s", (customer_id,)
    ).fetchone()
    conn.close()
    return row["summary"] if row else ""


def update_customer_memory(customer_id: int, summary: str) -> None:
    """Overwrite the customer's memory with a new summary. Call this at
    the END of a conversation."""
    now = _today()
    conn = get_connection()
    conn.execute(
        """INSERT INTO customer_memory (customer_id, summary, updated_at)
           VALUES (%s, %s, %s)
           ON CONFLICT (customer_id) DO UPDATE SET
               summary = EXCLUDED.summary, updated_at = EXCLUDED.updated_at""",
        (customer_id, summary, now),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Self-test -- run directly with: python tools.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("customer 1 orders:", len(get_customer_orders(1)))
    print("customer 6 orders:", len(get_customer_orders(6)))
    print("customer 99 orders:", len(get_customer_orders(99)))

    print()
    kb = search_knowledge_base("refund timeline")
    print("KB search 'refund timeline':", [a.title for a in kb])

    print()
    print("customer 7 memory:", repr(get_customer_memory(7)[:70]))

    print()
    t = create_ticket(2, "Test ticket from tools.py self-test", "technical", "low")
    print("created ticket:", t)
    add_ticket_message(t.id, "customer", "This is a test message.")
    escalate_ticket(t.id, "Human: Test Agent", "self-test escalation check")
    print("ticket after escalation:", get_customer_tickets(2)[0])