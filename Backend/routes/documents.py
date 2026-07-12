"""Document management API routes."""

import json
import logging
import re
import uuid
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form
from typing import Optional

from backend.database.db import supabase
from backend.middleware.auth import get_current_user
from backend.services.ocr_service import OCRService
from backend.services.gemma_service import GemmaService
from backend.services.requirements_service import requirement_applies

logger = logging.getLogger("documents")

router = APIRouter(prefix="/api/applications", tags=["documents"])
ocr = OCRService()
gemma = GemmaService()


def _sanitize_text(text: str, max_length: int = 2000) -> str:
    """Remove control characters (except tab/newline) that break JSON serialization.
    
    Strips null bytes and other control characters (U+0000-U+001F except \t, \r, \n),
    then truncates to max_length. This prevents PostgREST/JSON issues with binary
    content that OCR stubs may produce when decoding non-text files.
    """
    # Remove all control chars except \t \r \n
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return sanitized[:max_length]


def _safe_insert(table: str, data: dict) -> dict:
    """Insert into supabase with proper error logging.
    
    Catches PostgREST HTTP errors and logs the actual response body,
    which contains the real error reason (column name, constraint, etc.).
    """
    try:
        result = supabase.table(table).insert(data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        # Try to extract the actual PostgREST error from the exception
        error_detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            try:
                body = e.response.json()
                error_detail = json.dumps(body, indent=2)
            except Exception:
                error_detail = str(e.response.text or e)
        logger.error("Supabase insert failed for %s: %s\nData keys: %s", table, error_detail, list(data.keys()))
        raise HTTPException(
            status_code=400,
            detail=f"Database error inserting into {table}: {error_detail}",
        )


@router.post("/{application_id}/documents")
async def upload_document(
    application_id: str,
    request: Request,
    file: UploadFile = File(...),
    requirement_label: Optional[str] = Form(None),
):
    """Upload a document for an application's specific checklist item.
    If requirement_label is omitted, the AI will auto-classify the document."""
    user = await get_current_user(request)

    # Verify application exists and user owns it
    app = supabase.table("visa_applications") \
        .select("*") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    visa_type = app.data.get("visa_type", "")

    # Read file contents (for OCR later)
    file_bytes = await file.read()

    # Store in Supabase Storage
    storage_path = f"applications/{application_id}/{uuid.uuid4()}_{file.filename}"

    try:
        supabase.storage.from_("documents").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as e:
        # Bucket might not exist — try to create it
        try:
            supabase.storage.create_bucket("documents", {"public": True})
            supabase.storage.from_("documents").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": file.content_type or "application/octet-stream"},
            )
        except Exception as e2:
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e2)}")

    # Get public URL
    public_url = supabase.storage.from_("documents").get_public_url(storage_path)

    # Run OCR to extract text from the uploaded file
    extracted_text = await ocr.extract_text(file.filename, file_bytes)

    if requirement_label:
        # Manual upload — user specified the requirement
        doc_type = _infer_document_type(requirement_label)
        doc_data = _safe_insert("documents", {
            "application_id": application_id,
            "file_name": file.filename,
            "document_type": doc_type,
            "status": "pending",
            "file_contents": _sanitize_text(extracted_text),
            "storage_path": storage_path,
        })

        if not doc_data:
            raise HTTPException(status_code=500, detail="Failed to create document record")

        return {
            "document": {
                **doc_data,
                "public_url": public_url,
                "storage_path": storage_path,
                "requirement_label": requirement_label,
            }
        }

    # No requirement_label — auto-classify with OCR + AI (same as bulk upload)
    doc_data = _safe_insert("documents", {
        "application_id": application_id,
        "file_name": file.filename,
        "document_type": "other",
        "status": "pending",
        "file_contents": _sanitize_text(extracted_text),
        "storage_path": storage_path,
    })

    if not doc_data:
        raise HTTPException(status_code=500, detail="Failed to create document record")
    doc = doc_data

    # OCR already ran above — use the extracted text for classification
    result = await gemma.classify_document(extracted_text, "other", "other")

    try:
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
            .update({"status": "classified", "document_type": result["classified_as"]}) \
            .eq("id", doc["id"]) \
            .execute()
    except Exception:
        pass

    return {
        "document": {
            **doc,
            "public_url": public_url,
            "storage_path": storage_path,
            "classification": result,
        }
    }


@router.post("/{application_id}/documents/upload-multiple")
async def upload_multiple_documents(
    application_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
    extracted_texts: Optional[str] = Form(None),
):
    """
    Upload multiple documents at once, auto-classify each with OCR + AI,
    then compute overall readiness score.

    Optionally accepts an `extracted_texts` form field — a JSON string mapping
    filenames to `{ text, confidence }` objects from client-side OCR (Tesseract.js).
    When provided, the pre-extracted text is used instead of server-side OCR.
    """
    user = await get_current_user(request)

    # Parse pre-extracted OCR text if provided
    pre_extracted: dict[str, dict] = {}
    if extracted_texts:
        try:
            pre_extracted = json.loads(extracted_texts)
        except Exception:
            logger.warning("Failed to parse extracted_texts JSON")

    # Verify application exists and user owns it
    app = supabase.table("visa_applications") \
        .select("*") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    visa_type = app.data.get("visa_type", "")
    uploaded_docs = []
    classifications = []

    for file in files:
        if not file.filename:
            continue

        file_bytes = await file.read()

        # Store in Supabase Storage
        storage_path = f"applications/{application_id}/{uuid.uuid4()}_{file.filename}"

        try:
            supabase.storage.from_("documents").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": file.content_type or "application/octet-stream"},
            )
        except Exception:
            try:
                supabase.storage.create_bucket("documents", {"public": True})
                supabase.storage.from_("documents").upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": file.content_type or "application/octet-stream"},
                )
            except Exception as e2:
                raise HTTPException(status_code=500, detail=f"Upload failed for {file.filename}: {str(e2)}")

        public_url = supabase.storage.from_("documents").get_public_url(storage_path)

        # Run OCR to extract text from the uploaded file
        # Use client-side pre-extracted text when available (Tesseract.js)
        pre = pre_extracted.get(file.filename) if pre_extracted else None
        if pre and pre.get("text"):
            extracted_text = pre["text"]
        else:
            extracted_text = await ocr.extract_text(file.filename, file_bytes)

        # Create document record with OCR text and storage path
        doc = _safe_insert("documents", {
            "application_id": application_id,
            "file_name": file.filename,
            "document_type": "other",
            "status": "pending",
            "file_contents": _sanitize_text(extracted_text),
            "storage_path": storage_path,
        })

        if not doc:
            continue

        # Classify using the extracted OCR text
        result = await gemma.classify_document(extracted_text, "other", "other")

        try:
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
                .update({"status": "classified", "document_type": result["classified_as"]}) \
                .eq("id", doc["id"]) \
                .execute()
        except Exception:
            pass

        classification = {
            **result,
            "document_id": doc["id"],
            "document_name": doc["file_name"],
        }
        classifications.append(classification)
        uploaded_docs.append({
            **doc,
            "public_url": public_url,
            "storage_path": storage_path,
            "classification": classification,
        })

    # Get requirements for this visa type + destination
    dest_upper = (app.data.get("destination_country") or "").upper()
    all_reqs = supabase.table("visa_requirements") \
        .select("*") \
        .eq("visa_type", visa_type) \
        .order("sort_order") \
        .execute()

    filtered_reqs = [
        req for req in all_reqs.data or [] if requirement_applies(req, dest_upper)
    ]

    # Compute readiness score
    readiness = await gemma.assess_readiness(classifications, visa_type, filtered_reqs)

    # Update application
    supabase.table("visa_applications") \
        .update({
            "overall_score": readiness["overall_score"],
            "ai_summary": readiness["summary"],
        }) \
        .eq("id", application_id) \
        .execute()

    return {
        "message": f"Uploaded and classified {len(uploaded_docs)} document(s)",
        "documents": uploaded_docs,
        "readiness": readiness,
        "requirements": filtered_reqs,
    }


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, request: Request):
    """Delete a document by ID."""
    user = await get_current_user(request)

    # Get document
    doc = supabase.table("documents") \
        .select("*, visa_applications!inner(userid)") \
        .eq("id", document_id) \
        .execute()

    if not doc.data:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check ownership
    if doc.data[0].get("userid") != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Delete from storage using storage_path column
    try:
        sp = doc.data[0].get("storage_path")
        if sp:
            supabase.storage.from_("documents").remove([sp])
    except Exception:
        pass  # Storage delete is best-effort

    # Delete classifications first (FK constraint)
    supabase.table("document_classifications") \
        .delete() \
        .eq("document_id", document_id) \
        .execute()

    # Delete document record
    supabase.table("documents").delete().eq("id", document_id).execute()

    return {"message": "Document deleted"}


@router.get("/{application_id}/documents")
async def list_documents(application_id: str, request: Request):
    """List all documents for an application."""
    user = await get_current_user(request)

    # Verify app exists and user owns it
    app = supabase.table("visa_applications") \
        .select("userid") \
        .eq("id", application_id) \
        .single() \
        .execute()

    if not app.data:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.data["userid"] != user["id"] and user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    docs = supabase.table("documents") \
        .select("*, document_classifications(*)") \
        .eq("application_id", application_id) \
        .execute()

    # Enrich with public URLs
    enriched = []
    for doc in docs.data or []:
        enriched.append(doc)

    return {"documents": enriched}


def _infer_document_type(requirement_label: str) -> str:
    """Map a requirement label to a document type."""
    label_lower = requirement_label.lower()
    if "passport" in label_lower:
        return "passport"
    elif "photo" in label_lower or "photograph" in label_lower:
        return "passport_photo"
    elif "financial" in label_lower or "bank" in label_lower or "financial means" in label_lower:
        return "financial_proof"
    elif "flight" in label_lower or "itinerary" in label_lower or "travel" in label_lower:
        return "travel_document"
    elif "accommodation" in label_lower:
        return "accommodation_proof"
    elif "insurance" in label_lower:
        return "insurance"
    elif "application form" in label_lower:
        return "application_form"
    elif "medical" in label_lower:
        return "medical_report"
    elif "police" in label_lower or "clearance" in label_lower:
        return "police_clearance"
    elif "degree" in label_lower or "transcript" in label_lower or "qualification" in label_lower:
        return "education_document"
    elif "employment" in label_lower or "contract" in label_lower or "offer" in label_lower or "cv" in label_lower:
        return "employment_document"
    elif "birth" in label_lower:
        return "birth_certificate"
    elif "marriage" in label_lower:
        return "marriage_certificate"
    elif "residence" in label_lower:
        return "residence_proof"
    elif "language" in label_lower:
        return "language_certificate"
    elif "receipt" in label_lower or "fee" in label_lower:
        return "payment_receipt"
    else:
        return "other"
