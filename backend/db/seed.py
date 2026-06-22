"""
Builds and fills the Postgres database with realistic demo data for a
fictional electronics retailer ("Nimbus Gear").

Run directly:  python seed.py
Re-running is safe -- schema.sql does DROP+CREATE on every run, so IDs
always start fresh at 1 (customer_id=7 is always Ananya Iyer).
"""

from pathlib import Path
from connection import get_connection

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def build_schema(conn):
    conn.execute(SCHEMA_PATH.read_text())
    conn.commit()


def seed(conn):
    cur = conn.cursor()

    # ---- customers -------------------------------------------------
    customers = [
        ("Riya Sharma",     "riya.sharma@gmail.com",    "+91-98100-11223", "premium",    "2024-03-12", 4.6),
        ("Arjun Mehta",     "arjun.mehta@outlook.com",  "+91-99220-44556", "free",       "2025-01-08", 3.2),
        ("Sara Khan",       "sara.khan@yahoo.com",      "+91-97700-77889", "enterprise", "2023-11-02", 4.9),
        ("Devansh Patel",   "devansh.p@gmail.com",      "+91-98765-12340", "free",       "2025-09-19", 2.8),
        ("Neha Verma",      "neha.verma@gmail.com",     "+91-90909-22334", "premium",    "2024-07-25", 4.4),
        ("Karan Singh",     "karan.singh@gmail.com",    "+91-91234-56789", "free",       "2026-02-14", None),
        ("Ananya Iyer",     "ananya.iyer@outlook.com",  "+91-99887-65432", "enterprise", "2022-06-30", 4.7),
        ("Vikram Rao",      "vikram.rao@gmail.com",     "+91-98989-11111", "premium",    "2024-12-01", 3.9),
        ("Priya Nair",      "priya.nair@gmail.com",     "+91-97000-33221", "free",       "2026-04-03", None),
        ("Aditya Kapoor",   "aditya.kapoor@yahoo.com",  "+91-96655-44332", "premium",    "2023-08-17", 4.1),
    ]
    cur.executemany(
        "INSERT INTO customers (name, email, phone, tier, signup_date, satisfaction_score) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        customers,
    )

    # ---- orders ------------------------------------------------------
    products = [
        ("Nimbus Pro Wireless Headphones", 6499.0),
        ("Nimbus Smartwatch S2", 8999.0),
        ("Nimbus Bluetooth Speaker Mini", 2499.0),
        ("Nimbus USB-C Hub (7-in-1)", 1899.0),
        ("Nimbus Mechanical Keyboard", 4999.0),
        ("Nimbus HD Webcam", 2999.0),
        ("Nimbus 20000mAh Power Bank", 1999.0),
        ("Nimbus Laptop Stand", 1299.0),
        ("Nimbus Monitor Arm", 3499.0),
        ("Nimbus Phone Case (Clear)", 499.0),
    ]
    orders = [
        (1, products[0][0], 1, products[0][1], "delivered", "2026-05-02", "NMB-7841-IN"),
        (1, products[3][0], 2, products[3][1], "delivered", "2026-06-01", "NMB-7902-IN"),
        (2, products[2][0], 1, products[2][1], "shipped",   "2026-06-15", "NMB-8011-IN"),
        (3, products[1][0], 1, products[1][1], "delivered", "2026-04-20", "NMB-7610-IN"),
        (3, products[4][0], 1, products[4][1], "delivered", "2026-05-28", "NMB-7888-IN"),
        (4, products[5][0], 1, products[5][1], "pending",   "2026-06-18", None),
        (5, products[0][0], 1, products[0][1], "returned",  "2026-03-11", "NMB-7320-IN"),
        (5, products[6][0], 3, products[6][1], "delivered", "2026-06-05", "NMB-7950-IN"),
        (6, products[9][0], 2, products[9][1], "shipped",   "2026-06-17", "NMB-8030-IN"),
        (7, products[1][0], 2, products[1][1], "delivered", "2026-02-09", "NMB-7155-IN"),
        (7, products[8][0], 1, products[8][1], "delivered", "2026-05-30", "NMB-7901-IN"),
        (8, products[7][0], 1, products[7][1], "cancelled", "2026-06-10", None),
        (8, products[2][0], 1, products[2][1], "delivered", "2026-04-14", "NMB-7599-IN"),
        (9, products[3][0], 1, products[3][1], "pending",   "2026-06-19", None),
        (9, products[0][0], 1, products[0][1], "shipped",   "2026-06-16", "NMB-8025-IN"),
        (10, products[4][0], 1, products[4][1], "delivered", "2026-01-22", "NMB-6990-IN"),
        (10, products[6][0], 2, products[6][1], "returned",  "2026-05-18", "NMB-7860-IN"),
        (2, products[9][0], 3, products[9][1], "delivered", "2026-05-25", "NMB-7870-IN"),
    ]
    cur.executemany(
        "INSERT INTO orders (customer_id, product_name, quantity, price, status, order_date, tracking_number) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        orders,
    )

    # ---- tickets -------------------------------------------------------
    tickets = [
        (5, 7,  "Headphones arrived with a cracked earcup", "shipping", "high",   "escalated",  "2026-06-12", "2026-06-13", "Human: Priya R."),
        (2, 3,  "When will my speaker ship?",               "shipping", "low",    "resolved",   "2026-06-15", "2026-06-16", None),
        (4, None, "Cannot reset my account password",       "account",  "medium", "open",       "2026-06-18", "2026-06-18", None),
        (8, 12, "Why was my order cancelled without notice?", "billing", "high", "in_progress", "2026-06-11", "2026-06-12", None),
        (3, 5,  "Keyboard keys double-typing intermittently", "technical", "medium", "resolved", "2026-06-02", "2026-06-04", None),
        (10, 17, "Power bank stopped charging after 2 weeks", "technical", "high", "escalated", "2026-05-22", "2026-05-24", "Human: Rohan T."),
        (6, 9,  "Wrong color phone case received",           "shipping", "low",    "open",       "2026-06-17", "2026-06-17", None),
        (9, None, "Asking about enterprise bulk discount",    "billing", "medium", "open",       "2026-06-19", "2026-06-19", None),
        (1, 2,  "USB-C hub one port not detected",            "technical", "medium", "closed",   "2026-06-03", "2026-06-05", None),
        (7, 11, "Refund still not credited after 10 days",    "billing", "urgent", "escalated", "2026-06-14", "2026-06-19", "Human: Priya R."),
    ]
    cur.executemany(
        "INSERT INTO tickets (customer_id, order_id, subject, category, priority, status, created_at, updated_at, assigned_to) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        tickets,
    )

    # ---- ticket_messages -----------------------------------------------
    messages = [
        (1, "customer", "Hi, I just opened the box and the left earcup is cracked. Order #7.", "2026-06-12"),
        (1, "agent",    "I'm sorry to hear that, Neha. I can see order #7 was delivered on May 28. "
                         "Since this is a manufacturing defect, I'm escalating this to our exchange team.", "2026-06-12"),
        (1, "system",   "Ticket escalated to human agent: Priya R.", "2026-06-13"),
        (10, "customer", "My refund for the returned power bank hasn't shown up yet, it's been 10 days.", "2026-06-14"),
        (10, "agent",   "Checking now -- I can see the return was received on June 8th. Standard refund "
                         "timelines are 5-7 business days, so this is past due. Escalating to billing.", "2026-06-14"),
        (10, "system",  "Ticket escalated to human agent: Priya R.", "2026-06-14"),
        (3,  "customer", "I can't reset my password, the reset email never arrives.", "2026-06-18"),
        (3,  "agent",   "Let's check a couple of things -- can you confirm the email on your account?", "2026-06-18"),
    ]
    cur.executemany(
        "INSERT INTO ticket_messages (ticket_id, sender, message, created_at) VALUES (%s, %s, %s, %s)",
        messages,
    )

    # ---- knowledge_base -------------------------------------------------
    kb_articles = [
        ("Return policy", "Items can be returned within 30 days of delivery if unused and in original "
         "packaging. Defective items can be returned within 90 days. Refunds are issued to the original "
         "payment method.", "policy", "returns,refunds"),
        ("Refund timeline", "Once a returned item is received at our warehouse, refunds are processed "
         "within 5-7 business days. Bank processing may add 2-3 additional days before it reflects in "
         "your account.", "policy", "refunds,billing"),
        ("Shipping options and costs", "Standard shipping (4-6 business days) is free on orders above "
         "\u20b9999. Express shipping (1-2 business days) costs \u20b9149 flat. International shipping is "
         "available to select countries with rates calculated at checkout.", "policy", "shipping"),
        ("How to track your order", "Once shipped, you'll receive a tracking number by email. You can "
         "track it from the Orders page in your account, or by contacting support with your order ID.", "guide", "shipping,tracking"),
        ("Resetting your account password", "Go to the login page and click 'Forgot password'. If the "
         "reset email doesn't arrive within 5 minutes, check spam, then confirm the email matches your "
         "account exactly -- case and typos matter.", "guide", "account"),
        ("Subscription and billing cycle", "Premium and Enterprise plans renew monthly on the signup "
         "date. You can cancel anytime from Account > Billing; cancellation takes effect at the end of "
         "the current billing cycle, no partial refunds for unused days.", "policy", "billing"),
        ("Warranty claims", "All Nimbus products carry a 1-year manufacturer warranty against defects. "
         "Warranty claims require proof of purchase and are handled separately from the standard return "
         "window.", "policy", "warranty"),
        ("International shipping", "We currently ship to 12 countries outside India. Customs duties, if "
         "applicable, are the responsibility of the recipient and are not included in the order total.", "policy", "shipping,international"),
        ("Accepted payment methods", "We accept all major credit/debit cards, UPI, net banking, and "
         "Nimbus Wallet credit. EMI is available on orders above \u20b93000 for select banks.", "guide", "billing,payments"),
        ("Cancelling an order", "Orders can be cancelled for free as long as they haven't entered "
         "'shipped' status. Once shipped, you'll need to refuse delivery or use the standard return "
         "process instead.", "guide", "billing,shipping"),
    ]
    cur.executemany(
        "INSERT INTO knowledge_base (title, content, category, tags) VALUES (%s, %s, %s, %s)",
        kb_articles,
    )

    # ---- customer_memory --------------------------------------------------
    memory_seed = [
        (5, "Customer had a defective headphone order escalated to a human agent in June 2026. "
            "Generally polite but has now had two issues (defective item + late refund pattern) -- "
            "worth extra care on shipping-related requests.", "2026-06-13"),
        (7, "Long-time enterprise customer since 2022, high satisfaction historically (4.7/5). "
            "Currently has an urgent unresolved refund complaint -- handle with priority.", "2026-06-19"),
    ]
    cur.executemany(
        "INSERT INTO customer_memory (customer_id, summary, updated_at) VALUES (%s, %s, %s)",
        memory_seed,
    )

    # ---- users (dev/test login credentials) -----------------------------
    import bcrypt
    TEST_PASSWORD = "nimbus123"
    password_hash = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt()).decode()
    user_rows = [
        (customer_id, email, password_hash, "2026-01-01")
        for customer_id, (_, email, *_rest) in enumerate(customers, start=1)
    ]
    cur.executemany(
        "INSERT INTO users (customer_id, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
        user_rows,
    )

    # One staff account, role='staff', no customer_id -- same test
    # password as everyone else, for the same dev-convenience reason.
    cur.execute(
        "INSERT INTO users (customer_id, email, password_hash, role, created_at) "
        "VALUES (NULL, %s, %s, 'staff', %s)",
        ("staff@nimbusgear.com", password_hash, "2026-01-01"),
    )

    conn.commit()


if __name__ == "__main__":
    conn = get_connection()
    build_schema(conn)
    seed(conn)
    conn.close()
    print("Seeded Postgres database.")