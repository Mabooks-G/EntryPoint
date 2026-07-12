"""Auth API routes: register, login, me."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from backend.services.auth_service import register_user, login_user
from backend.middleware.auth import get_current_user, remove_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AuthRequest(BaseModel):
    email: str
    password: str


@router.post("/register", status_code=201)
async def register(body: AuthRequest):
    """Register a new user (user_type = 'applicant')."""
    email = body.email.strip().lower()
    if not email or not body.password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    if len(body.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    return register_user(email, body.password)


@router.post("/login")
async def login(body: AuthRequest):
    """Login with email and password."""
    email = body.email.strip().lower()
    return login_user(email, body.password)


@router.get("/me")
async def me(request: Request):
    """Get the currently authenticated user."""
    user = await get_current_user(request)
    return {
        "id": user["id"],
        "email": user["email"],
        "user_type": user["user_type"],
        "created_at": user["created_at"],
    }


@router.post("/logout")
async def logout(request: Request):
    """Invalidate the current token."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        remove_token(token)
    return {"message": "Logged out"}