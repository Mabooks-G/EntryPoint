"""Query API routes — user queries and admin replies."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from backend.database.db import supabase
from backend.middleware.auth import get_current_user, get_admin_user

router = APIRouter(prefix="/api/applications", tags=["queries"])


class QueryRequest(BaseModel):
    message: str


@router.post("/{application_id}/queries")
async def create_query(application_id: str, body: QueryRequest, request: Request):
    """User sends a query about their application."""
    user = await get_current_user(request)

    # Verify application
    app = supabase.table("visa_applications") \
        .select("userid") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not body.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    result = supabase.table("queries").insert({
        "application_id": application_id,
        "user_id": user["id"],
        "message": body.message.strip(),
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create query")

    return {"query": result.data[0]}


@router.get("/{application_id}/queries")
async def list_queries(application_id: str, request: Request):
    """List all queries for an application."""
    user = await get_current_user(request)

    app = supabase.table("visa_applications") \
        .select("userid") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"] and user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    result = supabase.table("queries") \
        .select("*") \
        .eq("application_id", application_id) \
        .order("created_at") \
        .execute()

    return {"queries": result.data or []}


# Queries sub-router for admin-only reply
admin_router = APIRouter(prefix="/api/queries", tags=["queries"])


class ReplyRequest(BaseModel):
    reply: str


class ResolveRequest(BaseModel):
    resolved: bool = True


@admin_router.post("/{query_id}/reply")
async def reply_to_query(query_id: str, body: ReplyRequest, request: Request):
    """Admin replies to a user query."""
    admin = await get_admin_user(request)

    if not body.reply.strip():
        raise HTTPException(status_code=400, detail="Reply is required")

    result = supabase.table("queries") \
        .update({
            "reply": body.reply.strip(),
            "admin_id": admin["id"],
            "replied_at": "now()",
        }) \
        .eq("id", query_id) \
        .execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Query not found")

    return {"query": result.data[0]}


@admin_router.patch("/{query_id}/resolution")
async def set_query_resolution(query_id: str, body: ResolveRequest, request: Request):
    """Mark an admin query resolved or reopen it."""
    admin = await get_admin_user(request)
    values = {
        "status": "resolved" if body.resolved else "open",
        "resolved_at": "now()" if body.resolved else None,
        "resolved_by": admin["id"] if body.resolved else None,
    }
    result = supabase.table("queries").update(values).eq("id", query_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Query not found")
    return {"query": result.data[0]}
