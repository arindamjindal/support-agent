"""
Shared connection helper -- now backed by Postgres instead of a local
SQLite file. Every tool function still imports get_connection() exactly
as before; what changed is what's behind it, not how it's called.

DATABASE_URL must be set in .env (backend/.env), e.g.:
  DATABASE_URL=postgresql://user:pass@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require
"""

import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set in backend/.env. "
        "Copy the connection string from your Neon project dashboard."
    )


def get_connection():
    # dict_row means rows come back as plain dicts (row["email"]) instead
    # of tuples -- same row[\"column\"] access pattern the rest of the
    # codebase already relies on from the old sqlite3.Row behavior.
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)