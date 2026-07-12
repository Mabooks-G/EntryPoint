"""Authentication middleware for FastAPI routes."""

import uuid
from typing import Optional
from functools import wraps
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.database.db import supabase

# In-memory token store for MVP
# Maps token -> user_id
_active_tokens: dict[str, str] = {}


def create_token(user_id: str) -> str:
    """Generate a new token for a user and store it."""
    token = str(uuid.uuid4())
    _active_tokens[token] = user_id
    return token


def remove_token(token: str) -> None:
    """Invalidate a token."""
    _active_tokens.pop(token, None)


def get_user_id_from_token(token: str) -> Optional[str]:
    """Look up the user ID for a given token."""
    return _active_tokens.get(token)


async def get_current_user(request: Request) -> dict:
    """Extract and validate the Bearer token, return the user record."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = supabase.table("users").select("*").eq("id", user_id).single().execute()
    if not user.data:
        raise HTTPException(status_code=401, detail="User not found")

    return user.data


async def get_admin_user(request: Request) -> dict:
    """Same as get_current_user but also enforces admin role."""
    user = await get_current_user(request)
    if user.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user