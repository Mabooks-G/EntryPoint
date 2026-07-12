"""Application management API routes."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from backend.database.db import supabase
from backend.middleware.auth import get_current_user
from backend.services.requirements_service import requirement_applies

router = APIRouter(prefix="/api/applications", tags=["applications"])

VISA_TYPES = ["Tourist", "Work", "Study", "Permanent Residence", "Asylum Seeker"]


class CreateApplicationRequest(BaseModel):
    visa_type: str
    origin_country: str
    destination_country: str
    applicant_name: Optional[str] = ""


@router.post("")
async def create_application(body: CreateApplicationRequest, request: Request):
    """Create a new visa application."""
    user = await get_current_user(request)

    if body.visa_type not in VISA_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid visa type. Must be one of: {', '.join(VISA_TYPES)}")

    result = supabase.table("visa_applications").insert({
        "userid": user["id"],
        "visa_type": body.visa_type,
        "origin_country": body.origin_country.upper(),
        "destination_country": body.destination_country.upper(),
        "applicant_name": body.applicant_name or "",
        "status": "in_progress",
        "overall_score": 0,
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create application")

    return {"application": result.data[0]}


@router.get("")
async def list_applications(request: Request):
    """List all applications for the current user."""
    user = await get_current_user(request)

    result = supabase.table("visa_applications") \
        .select("*") \
        .eq("userid", user["id"]) \
        .order("created_at", desc=True) \
        .execute()

    return {"applications": result.data}


@router.get("/{application_id}")
async def get_application(application_id: str, request: Request):
    """Get full application details including requirements and document status."""
    user = await get_current_user(request)

    # Get the application
    app_result = supabase.table("visa_applications") \
        .select("*") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app_result.data:
        raise HTTPException(status_code=404, detail="Application not found")

    app = app_result.data

    # Check ownership (admin can view any)
    if app["userid"] != user["id"] and user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this application")

    # Get requirements for this visa type + destination
    req_query = supabase.table("visa_requirements") \
        .select("*") \
        .eq("visa_type", app["visa_type"]) \
        .order("sort_order")

    req_result = req_query.execute()
    all_requirements = req_result.data

    dest_upper = (app.get("destination_country") or "").upper()
    filtered_reqs = [req for req in all_requirements if requirement_applies(req, dest_upper)]

    # Check for admin overrides
    overrides = supabase.table("requirement_overrides") \
        .select("requirements") \
        .eq("country", dest_upper) \
        .eq("visa_type", app["visa_type"]) \
        .execute()

    if overrides.data and overrides.data[0].get("requirements"):
        override_items = overrides.data[0]["requirements"]
        override_labels = {o["requirement_label"] for o in override_items}
        filtered_reqs = [r for r in filtered_reqs if r["requirement_label"] not in override_labels]
        for ov in override_items:
            filtered_reqs.append({
                **ov,
                "is_override": True,
            })
        filtered_reqs.sort(key=lambda x: x.get("sort_order", 0))

    # Get documents for this application
    docs_result = supabase.table("documents") \
        .select("*, document_classifications(*)") \
        .eq("application_id", application_id) \
        .execute()

    documents = docs_result.data or []

    # Get queries for this application
    queries_result = supabase.table("queries") \
        .select("*") \
        .eq("application_id", application_id) \
        .order("created_at") \
        .execute()

    return {
        "application": app,
        "requirements": filtered_reqs,
        "documents": documents,
        "queries": queries_result.data or [],
    }
