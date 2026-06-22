-- Postgres schema. DROP+CREATE on every seed run -- this is still
-- pre-launch dev data, so a clean rebuild is simpler than writing
-- migrations for a schema that's still actively changing.

DROP TABLE IF EXISTS pending_approvals CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS customer_memory CASCADE;
DROP TABLE IF EXISTS knowledge_base CASCADE;
DROP TABLE IF EXISTS ticket_messages CASCADE;
DROP TABLE IF EXISTS tickets CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT,
    tier            TEXT NOT NULL CHECK (tier IN ('free', 'premium', 'enterprise')),
    signup_date     TEXT NOT NULL,
    satisfaction_score REAL
);

CREATE TABLE orders (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    product_name    TEXT NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1,
    price           REAL NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('pending', 'shipped', 'delivered', 'returned', 'cancelled')),
    order_date      TEXT NOT NULL,
    tracking_number TEXT
);

CREATE TABLE tickets (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    order_id        INTEGER REFERENCES orders(id),
    subject         TEXT NOT NULL,
    category        TEXT NOT NULL CHECK (category IN ('billing', 'technical', 'shipping', 'account', 'other')),
    priority        TEXT NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    status          TEXT NOT NULL CHECK (status IN ('open', 'in_progress', 'escalated', 'resolved', 'closed')),
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    assigned_to     TEXT
);

CREATE TABLE ticket_messages (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id       INTEGER NOT NULL REFERENCES tickets(id),
    sender          TEXT NOT NULL CHECK (sender IN ('customer', 'agent', 'system')),
    message         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE knowledge_base (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title           TEXT NOT NULL,
    content         TEXT NOT NULL,
    category        TEXT NOT NULL,
    tags            TEXT
);

CREATE TABLE customer_memory (
    customer_id     INTEGER PRIMARY KEY REFERENCES customers(id),
    summary         TEXT NOT NULL DEFAULT '',
    updated_at      TEXT NOT NULL
);

-- customer_id is now NULLABLE: staff accounts log in but aren't
-- customers, so they have no customer profile to point at. role
-- decides which app they land in and which endpoints they can call.
CREATE TABLE users (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     INTEGER REFERENCES customers(id),
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer', 'staff')),
    created_at      TEXT NOT NULL
);

-- The actual staff queue. Inserted when a customer's agent proposes a
-- sensitive action and the graph pauses; resolved when staff acts on
-- it, which is also what unblocks the paused conversation.
CREATE TABLE pending_approvals (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id     INTEGER NOT NULL REFERENCES customers(id),
    tool_name       TEXT NOT NULL,
    tool_args       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'declined')),
    created_at      TEXT NOT NULL,
    resolved_at     TEXT,
    resolved_by     TEXT
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_messages_ticket ON ticket_messages(ticket_id);
CREATE INDEX idx_users_customer ON users(customer_id);
CREATE INDEX idx_pending_approvals_status ON pending_approvals(status);