"""Reference data API routes: countries, visa types, requirements."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from backend.database.db import supabase
from backend.services.requirements_service import requirement_applies

router = APIRouter(prefix="/api/reference", tags=["reference"])

VISA_TYPES = ["Tourist", "Work", "Study", "Permanent Residence", "Asylum Seeker"]


@router.get("/countries")
async def list_countries(search: Optional[str] = Query(None, description="Filter by name or code")):
    """List all supported countries. Optional search param filters by name (case-insensitive)."""
    query = supabase.table("countries").select("name, code").order("name")

    if search and search.strip():
        query = query.ilike("name", f"%{search.strip()}%")

    result = query.execute()
    return {"countries": result.data}


@router.get("/visa-types")
async def list_visa_types():
    """Return the 5 universal visa types."""
    return {"visa_types": VISA_TYPES}


@router.get("/requirements")
async def get_requirements(
    visa_type: str = Query(..., description="Visa type (Tourist, Work, Study, Permanent Residence, Asylum Seeker)"),
    destination_country: Optional[str] = Query(None, description="Destination country code for country-specific filtering"),
):
    """
    Get requirements for a visa type.
    - If destination_country is provided, returns requirements tagged [ALL]
      plus any tagged specifically for that country.
    - If no destination_country, returns only [ALL] requirements.
    """
    if visa_type not in VISA_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid visa type. Must be one of: {', '.join(VISA_TYPES)}")

    # Fetch base requirements for this visa type
    query = supabase.table("visa_requirements") \
        .select("*") \
        .eq("visa_type", visa_type) \
        .order("sort_order")

    result = query.execute()
    base_reqs = result.data

    # Filter: applies_to_all OR applies_to_countries includes the destination
    country_code_upper = destination_country.upper() if destination_country else None

    filtered = []
    for req in base_reqs:
        if requirement_applies(req, country_code_upper):
            filtered.append(req)

    # Check for admin overrides for this specific country + visa_type
    if destination_country:
        overrides = supabase.table("requirement_overrides") \
            .select("requirements") \
            .eq("country", destination_country.upper()) \
            .eq("visa_type", visa_type) \
            .execute()

        if overrides.data and overrides.data[0].get("requirements"):
            # Override exists — merge: override replaces matching labels
            override_items = overrides.data[0]["requirements"]
            override_labels = {o["requirement_label"] for o in override_items}

            # Keep base items not in override, add override items
            merged = [r for r in filtered if r["requirement_label"] not in override_labels]
            for ov in override_items:
                merged.append({
                    "id": ov.get("id"),
                    "visa_type": visa_type,
                    "requirement_label": ov["requirement_label"],
                    "applies_to_all": False,
                    "applies_to_countries": [destination_country.upper()],
                    "sort_order": len(merged),
                    "is_override": True,
                })
            filtered = merged

    return {"requirements": filtered}
