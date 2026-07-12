"""Authentication service — register and login logic."""

import bcrypt
from fastapi import HTTPException

from backend.database.db import supabase
from backend.middleware.auth import create_token


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def register_user(email: str, password: str) -> dict:
    """Register a new user. Returns token + user info."""
    # Check if email already exists
    existing = supabase.table("users").select("id").eq("email", email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    hashed_pw = hash_password(password)
    user_resp = supabase.table("users").insert({
        "email": email,
        "password": hashed_pw,
        "user_type": "applicant",
    }).execute()

    if not user_resp.data:
        raise HTTPException(status_code=500, detail="Failed to create user")

    user = user_resp.data[0]
    token = create_token(user["id"])

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "user_type": user["user_type"],
        },
    }


def login_user(email: str, password: str) -> dict:
    """Login a user. Returns token + user info."""
    user_resp = supabase.table("users").select("*").eq("email", email).execute()
    if not user_resp.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = user_resp.data[0]

    if not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user["id"])

    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "user_type": user["user_type"],
        },
    }