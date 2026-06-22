"""
Typed row models for the support agent's database.

These are plain dataclasses, not an ORM. We're talking to Postgres
directly with psycopg and wrapping rows in these for type-checked
access elsewhere in the codebase — same philosophy as building the RAG
pipeline with raw chromadb instead of a wrapper library: fewer layers
between you and what's actually happening.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Customer:
    id: int
    name: str
    email: str
    phone: Optional[str]
    tier: str  # free | premium | enterprise
    signup_date: str
    satisfaction_score: Optional[float]


@dataclass
class Order:
    id: int
    customer_id: int
    product_name: str
    quantity: int
    price: float
    status: str  # pending | shipped | delivered | returned | cancelled
    order_date: str
    tracking_number: Optional[str]


@dataclass
class Ticket:
    id: int
    customer_id: int
    order_id: Optional[int]
    subject: str
    category: str  # billing | technical | shipping | account | other
    priority: str  # low | medium | high | urgent
    status: str  # open | in_progress | escalated | resolved | closed
    created_at: str
    updated_at: str
    assigned_to: Optional[str]


@dataclass
class TicketMessage:
    id: int
    ticket_id: int
    sender: str  # customer | agent | system
    message: str
    created_at: str


@dataclass
class KnowledgeBaseArticle:
    id: int
    title: str
    content: str
    category: str
    tags: Optional[str]


@dataclass
class CustomerMemory:
    customer_id: int
    summary: str
    updated_at: str


@dataclass
class User:
    id: int
    customer_id: Optional[int]  # None for staff accounts
    email: str
    password_hash: str
    role: str  # customer | staff
    created_at: str