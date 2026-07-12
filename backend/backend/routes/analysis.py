"""AI Analysis API routes — submit application for OCR + AI pipeline."""

import logging
from fastapi import APIRouter, HTTPException, Request, Query, Body
from typing import Optional

from backend.database.db import supabase

logger = logging.getLogger("analysis")
from backend.middleware.auth import get_current_user, get_admin_user
from backend.services.ocr_service import OCRService
from backend.services.gemma_service import GemmaService
from backend.services.requirements_service import requirement_applies

router = APIRouter(prefix="/api/applications", tags=["analysis"])
ocr = OCRService()
gemma = GemmaService()


@router.post("/classify")
async def classify_text(
    text: str = Body(""),
    document_type: str = Body("passport"),
):
    """
    Direct text classification endpoint for testing.
    Accepts raw OCR text and returns the AI's analysis.
    Bypasses auth for quick testing.
    """
    if not text:
        raise HTTPException(status_code=400, detail="No text provided")
    result = await gemma.classify_document(text, document_type, document_type)
    return {
        "success": True,
        "analysis": result,
        "input_length": len(text),
        "input_preview": text[:200],
    }


@router.post("/{application_id}/submit")
async def submit_application(application_id: str, request: Request):
    """
    Submit an application for OCR + AI analysis.
    
    1. OCR all uploaded documents
    2. Classify each with Gemma
    3. Compute readiness score
    4. Update application status to 'submitted'
    """
    user = await get_current_user(request)

    # Verify application
    app = supabase.table("visa_applications") \
        .select("*") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get all documents
    docs = supabase.table("documents") \
        .select("*") \
        .eq("application_id", application_id) \
        .execute()

    if not docs.data:
        raise HTTPException(status_code=400, detail="No documents uploaded. Please upload documents first.")

    # Process each document: OCR → Classify
    classifications = []
    for doc in docs.data:
        # Step 1: Use pre-extracted OCR text from upload, or re-OCR from storage
        extracted_text = doc.get("file_contents", "") or ""
        if not extracted_text:
            # Fallback: try to download from Supabase Storage and OCR
            try:
                storage_path = doc.get("storage_path", "")
                if storage_path:
                    file_bytes = supabase.storage.from_("documents").download(storage_path)
                    extracted_text = await ocr.extract_text(
                        doc.get("file_name", "unknown"), file_bytes
                    )
                    # Persist for future runs
                    supabase.table("documents") \
                        .update({"file_contents": extracted_text[:2000]}) \
                        .eq("id", doc["id"]) \
                        .execute()
            except Exception as e:
                logger.warning("Failed to download/OCR document %s: %s", doc.get("id"), e)
                extracted_text = ""

        # Step 2: Classify with Gemma
        doc_type = doc.get("document_type", "other")
        result = await gemma.classify_document(extracted_text, doc_type, doc_type)

        # Step 3: Store classification
        try:
            classify_resp = supabase.table("document_classifications").insert({
                "document_id": doc["id"],
                "classified_as": result["classified_as"],
                "confidence": result["confidence"],
                "details": {
                    "extracted_length": len(extracted_text),
                    "extracted_info": result.get("extracted_info", {}),
                    "reasoning": result.get("reasoning", ""),
                    "is_valid": result.get("is_valid", False),
                },
                "issues": result.get("issues", []),
            }).execute()

            # Update document status
            supabase.table("documents") \
                .update({"status": "classified"}) \
                .eq("id", doc["id"]) \
                .execute()

            classifications.append({
                **result,
                "document_id": doc["id"],
                "document_name": doc["file_name"],
            })
        except Exception as e:
            classifications.append({
                "document_id": doc["id"],
                "document_name": doc["file_name"],
                "classified_as": "error",
                "confidence": 0,
                "is_valid": False,
                "issues": [f"Classification error: {str(e)}"],
            })

    # Step 4: Fetch requirements for this visa type + country
    visa_type = app.data["visa_type"]
    dest_upper = (app.data.get("destination_country") or "").upper()
    req_result = supabase.table("visa_requirements") \
        .select("*") \
        .eq("visa_type", visa_type) \
        .order("sort_order") \
        .execute()
    all_reqs = req_result.data or []
    requirements = [r for r in all_reqs if requirement_applies(r, dest_upper)]
    # Check admin overrides
    overrides = supabase.table("requirement_overrides") \
        .select("requirements") \
        .eq("country", dest_upper) \
        .eq("visa_type", visa_type) \
        .execute()
    if overrides.data and overrides.data[0].get("requirements"):
        override_items = overrides.data[0]["requirements"]
        override_labels = {o["requirement_label"] for o in override_items}
        requirements = [r for r in requirements if r["requirement_label"] not in override_labels]
        for ov in override_items:
            requirements.append({**ov, "is_override": True})
        requirements.sort(key=lambda x: x.get("sort_order", 0))

    # Step 5: Assess overall readiness with requirements
    readiness = await gemma.assess_readiness(classifications, visa_type, requirements)

    # Step 6: Update application
    supabase.table("visa_applications") \
        .update({
            "overall_score": readiness["overall_score"],
            "ai_summary": readiness["summary"],
            "status": "submitted",
        }) \
        .eq("id", application_id) \
        .execute()

    return {
        "message": "Application submitted for AI analysis",
        "readiness_score": readiness["overall_score"],
        "summary": readiness["summary"],
        "classifications": classifications,
        "stats": {
            "passed": readiness["passed"],
            "failed": readiness["failed"],
            "missing": readiness["missing"],
        },
        "requirement_statuses": readiness.get("requirement_statuses", []),
    }


@router.post("/{application_id}/analyze")
async def reanalyze_application(
    application_id: str,
    request: Request,
    mode: str = Query("all", description="'all' = re-process all docs, 'new' = only newly uploaded docs"),
):
    """
    Re-run AI analysis on an application without changing the page.
    
    Mode:
    - 'all': Re-process all documents
    - 'new': Only process documents that haven't been classified yet
    """
    user = await get_current_user(request)

    # Verify application
    app = supabase.table("visa_applications") \
        .select("*") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get documents based on mode
    if mode == "new":
        # Only unclassified documents
        docs = supabase.table("documents") \
            .select("*") \
            .eq("application_id", application_id) \
            .neq("status", "classified") \
            .execute()
    else:
        # All documents
        docs = supabase.table("documents") \
            .select("*") \
            .eq("application_id", application_id) \
            .execute()

    # Always fetch requirements, even if no docs — we need requirement_statuses
    visa_type = app.data["visa_type"]
    dest_upper = (app.data.get("destination_country") or "").upper()
    req_result = supabase.table("visa_requirements") \
        .select("*") \
        .eq("visa_type", visa_type) \
        .order("sort_order") \
        .execute()
    all_reqs = req_result.data or []
    requirements = [r for r in all_reqs if requirement_applies(r, dest_upper)]
    overrides = supabase.table("requirement_overrides") \
        .select("requirements") \
        .eq("country", dest_upper) \
        .eq("visa_type", visa_type) \
        .execute()
    if overrides.data and overrides.data[0].get("requirements"):
        override_items = overrides.data[0]["requirements"]
        override_labels = {o["requirement_label"] for o in override_items}
        requirements = [r for r in requirements if r["requirement_label"] not in override_labels]
        for ov in override_items:
            requirements.append({**ov, "is_override": True})
        requirements.sort(key=lambda x: x.get("sort_order", 0))

    if not docs.data:
        # Still compute readiness with all requirements marked as missing
        empty_classifications = []
        readiness = await gemma.assess_readiness(empty_classifications, visa_type, requirements)
        # Update the stored score so loadDetail has accurate data
        supabase.table("visa_applications") \
            .update({
                "overall_score": readiness["overall_score"],
                "ai_summary": readiness["summary"],
            }) \
            .eq("id", application_id) \
            .execute()
        return {
            "message": "No new documents to analyze" if mode == "new" else "No documents found",
            "readiness_score": readiness["overall_score"],
            "summary": readiness["summary"],
            "classifications": [],
            "stats": {
                "passed": readiness["passed"],
                "failed": readiness["failed"],
                "missing": readiness["missing"],
                "analyzed": 0,
                "total_documents": 0,
                "analysis_errors": 0,
            },
            "requirement_statuses": readiness.get("requirement_statuses", []),
        }

    # Keep the existing stored result until a replacement AI result succeeds.
    classifications = []
    total_documents = len(docs.data)
    for doc in docs.data:
        extracted_text = doc.get("file_contents", "") or ""
        if not extracted_text:
            # Fallback: download from storage and OCR
            try:
                storage_path = doc.get("storage_path", "")
                if storage_path:
                    file_bytes = supabase.storage.from_("documents").download(storage_path)
                    extracted_text = await ocr.extract_text(
                        doc.get("file_name", "unknown"), file_bytes
                    )
                    supabase.table("documents") \
                        .update({"file_contents": extracted_text[:2000]}) \
                        .eq("id", doc["id"]) \
                        .execute()
            except Exception as e:
                logger.warning("Failed to download/OCR document %s: %s", doc.get("id"), e)
                extracted_text = ""

        doc_type = doc.get("document_type", "other")
        try:
            logger.info("Analyzing document %s (%s of %s)", doc.get("file_name"), len(classifications) + 1, total_documents)
            result = await gemma.classify_document(extracted_text, doc_type, doc_type)
        except Exception as e:
            logger.exception("AI analysis failed for document %s", doc.get("id"))
            classifications.append({
                "document_id": doc["id"],
                "document_name": doc["file_name"],
                "classified_as": "error",
                "confidence": 0,
                "is_valid": False,
                "issues": [f"AI analysis failed: {str(e)}"],
            })
            continue

        try:
            if mode == "all":
                supabase.table("document_classifications") \
                    .delete() \
                    .eq("document_id", doc["id"]) \
                    .execute()
            supabase.table("document_classifications").insert({
                "document_id": doc["id"],
                "classified_as": result["classified_as"],
                "confidence": result["confidence"],
                "details": {
                    "extracted_length": len(extracted_text),
                    "extracted_info": result.get("extracted_info", {}),
                    "reasoning": result.get("reasoning", ""),
                    "is_valid": result.get("is_valid", False),
                },
                "issues": result.get("issues", []),
            }).execute()

            supabase.table("documents") \
                .update({"status": "classified"}) \
                .eq("id", doc["id"]) \
                .execute()

            classifications.append({
                **result,
                "document_id": doc["id"],
                "document_name": doc["file_name"],
            })
        except Exception as e:
            classifications.append({
                "document_id": doc["id"],
                "document_name": doc["file_name"],
                "classified_as": "error",
                "confidence": 0,
                "is_valid": False,
                "issues": [f"Classification error: {str(e)}"],
            })

    # Get ALL classifications (including pre-existing ones)
    all_classifications = supabase.table("document_classifications") \
        .select("*, documents!inner(file_name, document_type)") \
        .eq("documents.application_id", application_id) \
        .execute()

    all_class_data = []
    for c in all_classifications.data or []:
        all_class_data.append({
            "document_id": c["document_id"],
            "document_name": c.get("documents", {}).get("file_name", "Unknown"),
            "classified_as": c["classified_as"],
            "confidence": c["confidence"],
            "is_valid": len(c.get("issues", []) or []) == 0,
            "issues": c.get("issues", []) or [],
        })

    # Recompute readiness with requirements (already fetched above)
    readiness = await gemma.assess_readiness(all_class_data, visa_type, requirements)

    # Update application
    supabase.table("visa_applications") \
        .update({
            "overall_score": readiness["overall_score"],
            "ai_summary": readiness["summary"],
            "status": "submitted",
        }) \
        .eq("id", application_id) \
        .execute()

    analysis_errors = sum(1 for item in classifications if item.get("classified_as") == "error")
    analyzed = len(classifications) - analysis_errors
    return {
        "message": f"Analyzed {analyzed} of {total_documents} document(s)" + (f"; {analysis_errors} failed" if analysis_errors else ""),
        "readiness_score": readiness["overall_score"],
        "summary": readiness["summary"],
        "classifications": all_class_data,
        "stats": {
            "passed": readiness["passed"],
            "failed": readiness["failed"],
            "missing": readiness["missing"],
            "analyzed": analyzed,
            "total_documents": total_documents,
            "analysis_errors": analysis_errors,
        },
        "requirement_statuses": readiness.get("requirement_statuses", []),
    }
