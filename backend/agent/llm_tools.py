"""
LLM-facing tool wrappers.

tools.py returns typed dataclasses for use elsewhere in our own code.
These wrap those functions with @tool and format the output as plain
text — the LLM reads strings, not Python objects, so this is the
translation layer between "data the program can use" and "context the
model can reason over."
"""

from typing import Optional
from langchain_core.tools import tool

import tools as db


@tool
def lookup_orders(customer_id: int) -> str:
    """Get all orders placed by a customer, most recent first. Use this
    when the customer asks about an order, shipment, delivery, or
    purchase history."""
    orders = db.get_customer_orders(customer_id)
    if not orders:
        return "This customer has no orders on file."
    lines = [
        f"Order #{o.id}: {o.product_name} (qty {o.quantity}), \u20b9{o.price}, "
        f"status: {o.status}, ordered {o.order_date}"
        + (f", tracking: {o.tracking_number}" if o.tracking_number else "")
        for o in orders
    ]
    return "\n".join(lines)


@tool
def search_kb(query: str) -> str:
    """Search the knowledge base for policy and FAQ answers covering
    shipping, returns, refunds, billing, and account help. Use this
    before escalating a question you can probably answer from documented
    policy."""
    articles = db.search_knowledge_base(query)
    if not articles:
        return "No matching knowledge base articles found."
    return "\n\n".join(f"### {a.title}\n{a.content}" for a in articles)


@tool
def create_ticket(
    customer_id: int,
    subject: str,
    category: str,
    priority: str = "medium",
    order_id: Optional[int] = None,
) -> str:
    """Open a new support ticket. category must be one of: billing,
    technical, shipping, account, other. priority must be one of: low,
    medium, high, urgent. Use this when an issue needs tracking, not
    just a quick answer."""
    t = db.create_ticket(customer_id, subject, category, priority, order_id)
    return f"Created ticket #{t.id}: '{t.subject}' (status: {t.status})"


@tool
def escalate(ticket_id: int, reason: str) -> str:
    """Escalate an existing ticket to a human agent. Use this for any
    refund, cancellation, or anything you can't confidently resolve
    yourself. Never process a refund or cancellation directly — escalate
    it instead."""
    t = db.escalate_ticket(ticket_id, "Human: Support Team", reason)
    return f"Ticket #{t.id} escalated to a human agent. They'll follow up shortly."


@tool
def get_customer_history(customer_id: int) -> str:
    """Get a customer's profile, past tickets, and prior conversation
    memory. Use this at the start of a conversation to understand who
    you're talking to."""
    customer = db.get_customer(customer_id)
    if not customer:
        return "No such customer."
    memory = db.get_customer_memory(customer_id)
    tickets = db.get_customer_tickets(customer_id)
    parts = [f"{customer.name} ({customer.tier} tier, customer since {customer.signup_date})"]
    if memory:
        parts.append(f"Past context: {memory}")
    if tickets:
        parts.append(
            f"{len(tickets)} past ticket(s). Most recent: "
            f"'{tickets[0].subject}' ({tickets[0].status})"
        )
    return "\n".join(parts)


@tool
def process_refund(order_id: int, reason: str) -> str:
    """Process a refund for an order. This pauses for human approval
    before it actually executes -- propose it when you're confident the
    order qualifies under the return policy, but call it ALONE in your
    turn, not bundled with other tool calls."""
    order = db.process_refund(order_id, reason)
    return f"Refund processed for order #{order.id}. New status: {order.status}."


@tool
def cancel_order(order_id: int, reason: str) -> str:
    """Cancel an order. This pauses for human approval before it actually
    executes. Call it ALONE in your turn, not bundled with other tool
    calls."""
    order = db.cancel_order(order_id, reason)
    return f"Order #{order.id} cancelled."


ALL_TOOLS = [
    lookup_orders, search_kb, create_ticket, escalate, get_customer_history,
    process_refund, cancel_order,
]