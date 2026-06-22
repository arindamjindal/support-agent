"""
Password hashing (bcrypt) and session tokens (JWT).

No hardcoded fallback secret on purpose -- a secret key that defaults to
something if you forget to set it is exactly how real apps end up
deployed with a publicly-known signing key. This fails loudly instead.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set. Generate one and add it to backend/.env:\n"
        '  python -c "import secrets; print(secrets.token_hex(32))"'
    )

ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(user_id: int, role: str, customer_id: Optional[int] = None) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "customer_id": customer_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Returns the full payload: {user_id, role, customer_id, exp}.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError if the
    token is expired or invalid."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])