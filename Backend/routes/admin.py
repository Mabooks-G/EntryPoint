"""Admin API routes for applications, queries, requirements, and users."""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.database.db import supabase
from backend.middleware.auth import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])
VISA_TYPES = ["Tourist", "Work", "Study", "Permanent Residence", "Asylum Seeker"]


class RequirementInput(BaseModel):
    visa_type: str
    requirement_label: str = Field(min_length=1, max_length=240)
    sort_order: int = 0
    scope: Literal["all", "include", "exclude"] = "all"
    countries: list[str] = []


class LegacyOverrideRequest(BaseModel):
    visa_type: str
    country: str
    requirements: list[dict]


def requirement_data(body: RequirementInput) -> dict:
    if body.visa_type not in VISA_TYPES:
        raise HTTPException(status_code=400, detail="Invalid visa type")
    countries = sorted({country.strip() for country in body.countries if country.strip()})
    if body.scope != "all" and not countries:
        raise HTTPException(status_code=400, detail="Select at least one country for this scope")
    return {
        "visa_type": body.visa_type,
        "requirement_label": body.requirement_label.strip(),
        "sort_order": body.sort_order,
        "applies_to_all": body.scope in ("all", "exclude"),
        "applies_to_countries": "[ALL]" if body.scope != "include" else "[" + ",".join(countries) + "]",
        "excluded_countries": "[ALL]" if body.scope == "all" else (
            "[ALLex," + ",".join(countries) + "]" if body.scope == "exclude" else "[ALL]"
        ),
    }


@router.get("/applications")
async def admin_list_applications(request: Request):
    await get_admin_user(request)
    result = supabase.table("visa_applications").select("*, users!inner(email, user_type)").order("created_at", desc=True).execute()
    return {"applications": result.data or []}


@router.get("/queries")
async def admin_list_queries(request: Request):
    await get_admin_user(request)
    result = supabase.table("queries").select(
        "*, users!queries_user_id_fkey(email), "
        "visa_applications!inner(visa_type, destination_country, origin_country)"
    ).order("created_at").execute()
    queries = result.data or []
    # Keep unanswered items first without relying on version-specific PostgREST
    # null-ordering arguments.
    queries.sort(key=lambda query: (bool(query.get("reply")), query.get("created_at", "")))
    return {"queries": queries}


@router.get("/requirements")
async def admin_get_requirements(request: Request, visa_type: Optional[str] = None):
    await get_admin_user(request)
    query = supabase.table("visa_requirements").select("*")
    if visa_type:
        query = query.eq("visa_type", visa_type)
    result = query.order("visa_type").order("sort_order").execute()
    requirements = result.data or []
    for requirement in requirements:
        for field in ("applies_to_countries", "excluded_countries"):
            value = requirement.get(field)
            if isinstance(value, str):
                requirement[field] = [
                    item.strip() for item in value.strip().strip("[]").split(",")
                    if item.strip() and item.strip().upper() not in {"ALL", "ALLEX"}
                ]
    return {"requirements": requirements}


@router.post("/requirements")
async def admin_create_requirement(body: RequirementInput, request: Request):
    await get_admin_user(request)
    result = supabase.table("visa_requirements").insert(requirement_data(body)).execute()
    return {"requirement": result.data[0]}


@router.put("/requirements/item/{requirement_id}")
async def admin_update_requirement(requirement_id: str, body: RequirementInput, request: Request):
    await get_admin_user(request)
    result = supabase.table("visa_requirements").update(requirement_data(body)).eq("id", requirement_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {"requirement": result.data[0]}


@router.delete("/requirements/item/{requirement_id}")
async def admin_delete_requirement(requirement_id: str, request: Request):
    await get_admin_user(request)
    result = supabase.table("visa_requirements").delete().eq("id", requirement_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {"message": "Requirement deleted"}


@router.put("/requirements/overrides")
async def admin_set_legacy_override(body: LegacyOverrideRequest, request: Request):
    """Compatibility endpoint for existing country override data."""
    await get_admin_user(request)
    country = body.country.upper()
    existing = supabase.table("requirement_overrides").select("id").eq("country", country).eq("visa_type", body.visa_type).execute()
    values = {"country": country, "visa_type": body.visa_type, "requirements": body.requirements, "updated_at": "now()"}
    if existing.data:
        supabase.table("requirement_overrides").update(values).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("requirement_overrides").insert(values).execute()
    return {"message": "Country override saved"}


@router.get("/users")
async def admin_list_users(request: Request):
    await get_admin_user(request)
    result = supabase.table("users").select("id, email, user_type, created_at").order("created_at", desc=True).execute()
    users = result.data or []
    for user in users:
        count = supabase.table("visa_applications").select("id", count="exact").eq("userid", user["id"]).execute()
        user["application_count"] = count.count if hasattr(count, "count") else 0
    return {"users": users}
