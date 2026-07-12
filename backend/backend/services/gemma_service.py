"""DeepSeek V4 Pro Classification Service — via Fireworks AI (OpenAI-compatible API).

Uses DeepSeek V4 Pro hosted on Fireworks AI, accessed through an OpenAI-compatible
endpoint. No local GPU or Ollama required — the heavy AI runs on Fireworks'
infrastructure using hackathon credits.

Key design: DeepSeek V4 Pro receives garbled OCR output with a smart prompt
that tells it to reason from fragments, patterns, and MRZ lines — not
to just look for exact keyword matches. It uses Fireworks AI's hosted
DeepSeek V4 Pro for deep multi-step reasoning (1M context).

Prompt strategy:
  "The OCR text below is garbled and noisy. Reason from fragments,
   recognizable patterns, MRZ lines, dates, and document structure.
   Identify the document type, country of issuance, any dates (issue,
   expiry, DOB), and whether it appears valid."
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger("deepseek")


class DeepSeekServiceError(RuntimeError):
    """Raised when Fireworks cannot return a usable DeepSeek analysis."""

# ── Fireworks AI configuration ─────────────────────────────────────────────
# Get your API key from https://app.fireworks.ai/account/api-keys
# Set it as FIREWORKS_API_KEY environment variable (in docker-compose or shell)
API_KEY = os.environ.get("FIREWORKS_API_KEY", "")

# Fireworks AI base URL (OpenAI-compatible endpoint)
FIREWORKS_BASE_URL = "https://api.fireworks.ai/inference/v1"

# DeepSeek V4 Pro on Fireworks — 1M context, great for garbled OCR
FIREWORKS_MODEL = os.environ.get("FIREWORKS_MODEL", "accounts/fireworks/models/deepseek-v4-pro")

# ── MRZ parsing — works even when surrounding text is noisy ────────────

# TD3 (passport, 2 lines × 44 chars)
_MRZ_TD3_PATTERN = re.compile(
    r"P<[A-Z]{3}[A-Z0-9<]{44}\n[A-Z0-9<]{44}"
)
_TD1_LINE = re.compile(r"^[A-Z0-9<]{30}$", re.MULTILINE)


def _parse_mrz_lines(text: str) -> dict:
    """Extract structured info from MRZ lines embedded in garbled text."""
    info = {}
    lines = text.split("\n")

    # TD3 passport (e.g. P<USAMUSTER<<MAX<<<<<<<<<...)
    for i, line in enumerate(lines):
        line_s = line.strip()
        # Line 1 of TD3: starts with P< or P <<
        if line_s.startswith("P<") or line_s.startswith("P<<"):
            # Country code is chars 2-4
            if len(line_s) >= 5 and line_s[2:5].isalpha():
                info["country"] = line_s[2:5]
            # Look ahead for surnames
            surname_part = line_s[5:].split("<")[0] if "<" in line_s[5:] else ""
            if surname_part:
                info["surname"] = surname_part.replace("<", " ").strip()

            # Next line (Line 2 of TD3) — passport number, nationality, DOB, sex, expiry
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().replace(" ", "")
                # Passport number (first 9 chars)
                if len(next_line) >= 9:
                    pnum = next_line[:9].replace("<", "")
                    if pnum:
                        info["passport_number"] = pnum
                # Nationality (chars 10-12 if available)
                if len(next_line) >= 12:
                    nat = next_line[10:13]
                    if nat.isalpha():
                        info["nationality"] = nat
                # DOB (chars 13-18: YYMMDD)
                if len(next_line) >= 19:
                    dob_raw = next_line[13:19]
                    if dob_raw.isdigit():
                        info["dob"] = dob_raw
                # Sex (char 20)
                if len(next_line) >= 21:
                    sex = next_line[20]
                    if sex in "MF":
                        info["sex"] = sex
                # Expiry (chars 21-26: YYMMDD)
                if len(next_line) >= 27:
                    exp_raw = next_line[21:27]
                    if exp_raw.isdigit():
                        info["expiry_date"] = exp_raw

    # If no TD3 found, try parsing just the raw numeric/groups
    if not info.get("passport_number"):
        # Look for USA followed by digits pattern (USA6401171F)
        usa_match = re.search(r"USA(\d{6})([MF])", text.upper())
        if usa_match:
            info["dob"] = usa_match.group(1)
            info["sex"] = usa_match.group(2)
            info["nationality"] = "USA"

    # TD1 — try 3 consecutive lines of 30 alphanumeric chars each
    td1_lines = _TD1_LINE.findall(text)
    if len(td1_lines) >= 2 and not info.get("passport_number"):
        # 2nd line of TD1 has DOB, sex, expiry
        line2 = td1_lines[1].replace(" ", "")
        if len(line2) >= 15 and line2[5:11].isdigit():
            info["dob"] = line2[5:11]
        if len(line2) >= 16:
            info["sex"] = line2[15]
        if len(line2) >= 22 and line2[17:23].isdigit():
            info["expiry_date"] = line2[17:23]

    return info


def _infer_from_garbled_text(text: str) -> dict:
    """Extract intelligence from garbled OCR text using patterns, not keywords."""
    hints = {}
    text_upper = text.upper()

    # ── Country detection ─────────────────────────────────────────────
    country_patterns = {
        "USA": ["UNITED STATES", "UNITED STATE", "U.S.A", "AMERICA", "USA"],
        "GBR": ["UNITED KINGDOM", "BRITISH", "UK ", "GREAT BRITAIN", "ENGLAND"],
        "CAN": ["CANADA", "CANADIAN"],
        "AUS": ["AUSTRALIA", "AUSTRALIAN"],
        "DEU": ["GERMANY", "GERMAN", "DEUTSCHLAND", "DEUTSCH"],
        "FRA": ["FRANCE", "FRENCH", "REPUBLIQUE FRANCAISE", "FRANCAISE"],
        "IND": ["INDIA", "INDIAN", "BHARAT"],
        "CHN": ["CHINA", "CHINESE", "PEOPLE'S REPUBLIC"],
        "NGA": ["NIGERIA", "NIGERIAN"],
        "ZAF": ["SOUTH AFRICA"],
        "JPN": ["JAPAN", "JAPANESE"],
        "BRA": ["BRAZIL", "BRASIL", "BRAZILIAN"],
        "MEX": ["MEXICO", "MEXICAN"],
        "RUS": ["RUSSIA", "RUSSIAN"],
        "ARE": ["UNITED ARAB EMIRATES", "DUBAI", "ABU DHABI", "UAE"],
        "SAU": ["SAUDI ARABIA"],
    }

    for code, patterns in country_patterns.items():
        for pat in patterns:
            if pat in text_upper:
                hints["country"] = code
                break
        if "country" in hints:
            break

    # ── Document type detection ───────────────────────────────────────
    doc_patterns = {
        "passport": ["P<", "PASSPORT", "PAS<PORT", "PA<SPORT", "TYPE P", "PAS", "MRZ"],
        "birth_certificate": ["BIRTH", "BIRTH CERTIFICATE", "CERTIFICATE OF BIRTH"],
        "identity_document": ["IDENTITY", "ID CARD", "NATIONAL ID", "IDENTITY CARD", "ID"],
        "drivers_license": ["DRIVER", "DRIVING", "LICENSE", "LICENCE"],
    }

    for doc_type, patterns in doc_patterns.items():
        for pat in patterns:
            if pat in text_upper:
                hints["document_type"] = doc_type
                break
        if "document_type" in hints:
            break

    # ── Name detection — look for recognizable words ──────────────────
    name_match = re.search(r"([A-Z]{3,}(?:\s+[A-Z]{3,}){1,3})", text)
    if name_match:
        candidate = name_match.group(0).strip()
        # Filter out known non-name phrases
        skip = {"UNITED STATES", "UNITED KINGDOM", "PASSPORT", "DEPARTMENT",
                "ISSUING", "AUTHORITY", "DATE OF BIRTH", "DATE OF ISSUE",
                "DATE OF EXPIRY", "NATIONALITY", "SIGNATURE", "TYPE",
                "CODE", "NUMBER", "SEX", "PLACE OF BIRTH"}
        if candidate not in skip and not candidate.startswith("P<"):
            hints["name_candidate"] = candidate

    # ── Date detection ────────────────────────────────────────────────
    dates = re.findall(r"20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}", text)
    if dates:
        hints["dates"] = dates
    dates2 = re.findall(r"\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}", text)
    if dates2:
        if "dates" not in hints:
            hints["dates"] = []
        hints["dates"].extend(dates2)

    # ── Keyword-based validity ────────────────────────────────────────
    text_lower = text.lower()
    if "expired" in text_lower or "expires" in text_lower:
        hints["expiry_mentioned"] = True

    return hints


class GemmaService:
    """Document classification using DeepSeek V4 Pro via Fireworks AI (OpenAI-compatible API).

    This calls Fireworks AI's hosted API using hackathon credits — no local GPU required.
    Set the FIREWORKS_API_KEY environment variable with your Fireworks AI key.
    """

    def __init__(self):
        self._ai_available = None  # lazy check

    async def _check_ai(self) -> bool:
        """Check if the Fireworks API key is configured and reachable."""
        if self._ai_available:
            return True
        if self._ai_available is False:
            raise DeepSeekServiceError(
                "DeepSeek is unavailable. Restart the backend after fixing the Fireworks configuration."
            )

        if not API_KEY:
            logger.warning(
                "FIREWORKS_API_KEY not set. "
                "Get one at https://app.fireworks.ai/account/api-keys "
                "and export FIREWORKS_API_KEY=your_key"
            )
            self._ai_available = False
            raise DeepSeekServiceError("FIREWORKS_API_KEY is not configured.")

        try:
            from openai import OpenAI
            client = OpenAI(api_key=API_KEY, base_url=FIREWORKS_BASE_URL)
            # Lightweight ping — list models
            client.models.list()
            self._ai_available = True
            logger.info("✅ DeepSeek V4 Pro (via Fireworks AI) is reachable")
        except Exception as e:
            self._ai_available = False
            logger.exception("Fireworks AI connectivity check failed")
            raise DeepSeekServiceError(f"Fireworks connectivity check failed: {e}") from e
        return True

    async def classify_document(
        self, extracted_text: str, document_type: str, requirement_label: str
    ) -> dict:
        """
        Classify extracted OCR text using DeepSeek V4 Pro.

        Returns: {
            classified_as, confidence, is_valid, issues,
            extracted_info, reasoning
        }
        """
        ai_ok = await self._check_ai()

        if ai_ok:
            try:
                result = await self._call_deepseek(extracted_text, document_type)
                if result:
                    return self._normalize_result(result, document_type)
            except Exception as e:
                logger.exception("DeepSeek analysis request failed")
                raise DeepSeekServiceError(f"DeepSeek analysis failed: {e}") from e

        # ── Fallback: pattern-based reasoning ─────────────────────────
        raise DeepSeekServiceError("DeepSeek returned no analysis.")

    async def _call_deepseek(self, text: str, doc_type: str) -> dict:
        """Call DeepSeek V4 Pro via Fireworks AI (OpenAI-compatible) API using raw HTTP.

        Key insight: DeepSeek V4 Pro puts chain-of-thought reasoning into
        ``reasoning_content`` when the prompt is short and direct. If the prompt is
        long, reasoning leaks into ``content`` instead. We use a **very short prompt**
        to keep the JSON in ``content``, and check both fields before parsing.
        """
        import httpx

        # ── Ultra-short prompt prevents DeepSeek from going into reasoning mode ──
        # Long prompts (like "Analyze this garbled OCR text and return JSON...")
        # cause DeepSeek to fill `content` with prose and never output JSON.
        # Short, direct prompts keep JSON in `content` and reasoning in `reasoning_content`.
        short_text = text[:500].strip()
        user_message = (
            f"[{doc_type}] {short_text}\n\n"
            "Output ONLY this JSON with your analysis:\n"
            '{"document_type":"","country":"","confidence":0.0,"is_valid":true,'
            '"extracted_info":{"name":"","passport_number":"","date_of_birth":"",'
            '"expiry_date":"","nationality":"","sex":""},"issues":[],"reasoning":""}'
        )

        payload = {
            "model": FIREWORKS_MODEL,
            "messages": [
                {"role": "user", "content": user_message},
            ],
            # Fireworks JSON mode guarantees a complete JSON object in content.
            "response_format": {"type": "json_object"},
            "temperature": 0.05,
            "max_tokens": 2048,
        }

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        }

        # Retry with exponential backoff
        max_retries = 3
        last_error = None
        raw = None
        data = None

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        f"{FIREWORKS_BASE_URL}/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                # Extract content from the OpenAI-compatible response
                choices = data.get("choices", [])
                if choices:
                    finish_reason = choices[0].get("finish_reason")
                    if finish_reason == "length":
                        raise ValueError(
                            "DeepSeek response was truncated; increase max_tokens or reduce the prompt."
                        )
                    msg = choices[0].get("message", {})
                    # Log full message keys to debug field structure
                    logger.info(
                        "DeepSeek message keys: %s. content len: %d, reasoning_content present: %s",
                        list(msg.keys()),
                        len(msg.get("content", "") or ""),
                        "reasoning_content" in msg,
                    )
                    content_text = msg.get("content", "") or ""
                    # With JSON mode, content is the final structured answer.
                    raw = content_text
                    logger.info("Using JSON-mode content field (len=%d)", len(content_text))
                break
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(
                        "Fireworks AI attempt %d failed: %s. Retrying in %ds...",
                        attempt + 1, e, wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        "Fireworks AI call failed after %d retries: %s",
                        max_retries, e,
                    )
                    raise

        if not raw:
            logger.error(
                "Fireworks AI returned empty response. "
                "Raw response: %s", str(data)[:500] if data else "N/A"
            )
            raise ValueError("Empty response from Fireworks AI")

        logger.info("DeepSeek raw response (first 500 chars): %s", raw[:500])
        logger.debug("DeepSeek full response length: %d", len(raw))

        # DeepSeek sometimes wraps output in markdown code fences
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.find("\n")
            if first_newline != -1:
                cleaned = cleaned[first_newline + 1:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
            logger.debug("Stripped markdown fences from response")

        # Strategy 1: Try to parse the entire response as JSON
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Find the last JSON block in the text.
        # (handles cases where a tiny bit of prose precedes the JSON)
        last_brace = cleaned.rfind("{")
        if last_brace != -1:
            depth = 0
            for i, c in enumerate(cleaned[last_brace:]):
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            parsed = json.loads(cleaned[last_brace:last_brace + i + 1])
                            logger.info(
                                "Extracted JSON from end of DeepSeek response "
                                "(found at char %d)", last_brace
                            )
                            return parsed
                        except json.JSONDecodeError:
                            break
            # Try the last '{' to end as fallback
            for candidate_end in [len(cleaned), len(cleaned) - 1, len(cleaned) - 2]:
                try:
                    return json.loads(cleaned[last_brace:candidate_end])
                except (json.JSONDecodeError, ValueError):
                    continue

        # Strategy 3: Greedy regex match as last resort
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                logger.warning(
                    "JSON decode failed on greedy-matched block: %s. "
                    "First 200 chars: %s", e, json_match.group(0)[:200]
                )

        logger.error(
            "Failed to extract JSON from DeepSeek response. "
            "Response (first 1000 chars): %s", cleaned[:1000]
        )
        raise ValueError("No valid JSON found in DeepSeek response")

    def _merge_with_fallback(
        self, ai_result: dict, text: str, doc_type: str
    ) -> dict:
        """When AI confidence is low, merge with fallback to fill gaps."""
        fallback = self._fallback_classify(text, doc_type)
        normalized = self._normalize_result(ai_result, doc_type)

        # Use AI's document type and confidence, but fill missing fields from fallback
        extracted = normalized.get("extracted_info", {})
        fb_extracted = fallback.get("extracted_info", {})
        for key in fb_extracted:
            if not extracted.get(key) and fb_extracted.get(key):
                extracted[key] = fb_extracted[key]

        issues = normalized.get("issues", [])
        if not issues:
            issues = fallback.get("issues", [])

        reasoning = normalized.get("reasoning", "")
        if not reasoning:
            reasoning = fallback.get("reasoning", "")

        return {
            "classified_as": normalized.get("classified_as", doc_type),
            "confidence": max(
                normalized.get("confidence", 0), fallback.get("confidence", 0)
            ),
            "is_valid": normalized.get("is_valid", True),
            "issues": issues,
            "extracted_info": extracted,
            "reasoning": reasoning,
        }

    @staticmethod
    def _normalize_result(result: dict, default_type: str) -> dict:
        """Normalize DeepSeek output into the standard response format."""
        extracted = result.get("extracted_info", {}) or {}
        issues = result.get("issues", []) or []
        if isinstance(issues, str):
            issues = [issues]

        return {
            "classified_as": result.get("document_type", default_type),
            "confidence": float(result.get("confidence", 0.5)),
            "is_valid": bool(result.get("is_valid", True)),
            "issues": issues,
            "extracted_info": extracted,
            "reasoning": result.get("reasoning", ""),
        }

    def _fallback_classify(self, extracted_text: str, document_type: str) -> dict:
        """Pattern-based fallback that reasons from fragments."""
        mrz_info = _parse_mrz_lines(extracted_text)
        hints = _infer_from_garbled_text(extracted_text)

        # ── Determine document type ───────────────────────────────────
        doc_type = hints.get("document_type", document_type)

        # ── Determine country ─────────────────────────────────────────
        country = mrz_info.get("country") or hints.get("country", "Unknown")

        # ── Build extracted info ──────────────────────────────────────
        extracted_info = {
            "name": hints.get("name_candidate"),
            "passport_number": mrz_info.get("passport_number"),
            "date_of_birth": self._format_dob(mrz_info.get("dob")),
            "expiry_date": self._format_mrz_date(mrz_info.get("expiry_date")),
            "nationality": mrz_info.get("nationality") or country,
            "sex": mrz_info.get("sex"),
        }

        # ── Confidence based on how much we could extract ─────────────
        found_count = sum(1 for v in extracted_info.values() if v)
        confidence = round(0.3 + (found_count * 0.12), 2)

        # ── Issues ────────────────────────────────────────────────────
        issues = []
        if not mrz_info and not hints.get("country"):
            issues.append(
                "OCR quality is very low — limited text could be extracted"
            )
        if hints.get("expiry_mentioned"):
            issues.append("Document mentions expiry — may be expired")
        if len(extracted_text) < 30:
            issues.append(
                "Very short text extracted — "
                "document may be damaged or poorly scanned"
            )

        # ── Reasoning summary ─────────────────────────────────────────
        reasoning_parts = []
        if mrz_info:
            reasoning_parts.append("MRZ data found and decoded")
        if country != "Unknown":
            reasoning_parts.append(
                f"Country ({country}) identified from document text"
            )
        if extracted_info.get("date_of_birth"):
            reasoning_parts.append(
                f"DOB extracted: {extracted_info['date_of_birth']}"
            )
        if extracted_info.get("passport_number"):
            reasoning_parts.append(
                f"Document number: {extracted_info['passport_number']}"
            )
        reasoning = (
            "; ".join(reasoning_parts)
            if reasoning_parts
            else "Analyzed from fragmented OCR text"
        )

        is_valid = confidence >= 0.4 and "expired" not in (
            extracted_text.lower()
        )

        return {
            "classified_as": doc_type,
            "confidence": min(confidence, 0.95),
            "is_valid": is_valid,
            "issues": issues,
            "extracted_info": extracted_info,
            "reasoning": reasoning,
        }

    # ── Helper utilities ──────────────────────────────────────────────

    @staticmethod
    def _format_dob(dob_raw: Optional[str]) -> Optional[str]:
        """Convert YYMMDD to YYYY-MM-DD."""
        if not dob_raw or len(dob_raw) != 6:
            return None
        try:
            yy = int(dob_raw[:2])
            mm = dob_raw[2:4]
            dd = dob_raw[4:6]
            yyyy = 1900 + yy if yy > 25 else 2000 + yy
            return f"{yyyy}-{mm}-{dd}"
        except ValueError:
            return None

    @staticmethod
    def _format_mrz_date(mrz_date: Optional[str]) -> Optional[str]:
        """Convert MRZ YYMMDD to YYYY-MM-DD."""
        if not mrz_date or len(mrz_date) != 6:
            return None
        try:
            yy = int(mrz_date[:2])
            mm = mrz_date[2:4]
            dd = mrz_date[4:6]
            yyyy = 2000 + yy if yy < 50 else 1900 + yy
            return f"{yyyy}-{mm}-{dd}"
        except ValueError:
            return None

    # ── Requirement matching & readiness assessment ──────────────────

    def _match_requirement_to_classification(
        self, requirement_label: str, classified_as: str
    ) -> bool:
        """Check if an AI classification matches a requirement label."""
        req_lower = requirement_label.lower()
        type_lower = classified_as.lower()

        # Models often return a readable name such as "passport", while the
        # checklist uses a fuller name such as "Valid Passport".
        if type_lower and type_lower not in {"other", "unknown", "document"}:
            if type_lower in req_lower or req_lower in type_lower:
                return True

        mapping = {
            "passport": ["passport"],
            "passport_photo": ["passport_photo", "photo"],
            "application_form": ["application_form"],
            "financial_proof": [
                "financial_proof", "financial", "bank"
            ],
            "travel_document": [
                "travel_document", "travel", "itinerary", "flight"
            ],
            "accommodation_proof": [
                "accommodation_proof", "accommodation", "hotel"
            ],
            "insurance": ["insurance"],
            "medical_report": ["medical_report", "medical"],
            "police_clearance": [
                "police_clearance", "police", "clearance"
            ],
            "education_document": [
                "education_document", "transcript", "degree",
                "academic", "qualification"
            ],
            "employment_document": [
                "employment_document", "employment",
                "contract", "offer", "employer"
            ],
            "birth_certificate": ["birth_certificate", "birth"],
            "marriage_certificate": ["marriage_certificate", "marriage"],
            "residence_proof": ["residence_proof", "residence"],
            "language_certificate": [
                "language_certificate", "language", "ielts"
            ],
            "cv": ["cv", "curriculum vitae", "resume"],
            "cover_letter": ["cover_letter", "cover letter"],
            "acceptance_letter": [
                "acceptance_letter", "acceptance", "admission"
            ],
            "asylum_statement": ["asylum_statement", "asylum"],
            "identity_document": [
                "identity_document", "identity", "id card"
            ],
            "travel_history": ["travel_history", "travel history"],
            "supporting_evidence": ["supporting_evidence", "evidence"],
        }

        for type_key, keywords in mapping.items():
            if type_lower == type_key:
                for kw in keywords:
                    if kw in req_lower:
                        return True
        return False

    async def assess_readiness(
        self,
        classifications: list[dict],
        visa_type: str,
        requirements: list[dict] = None,
    ) -> dict:
        """Assess overall visa readiness score and generate summary."""
        requirement_statuses = []

        if requirements and len(requirements) > 0:
            matched_count = 0
            total_reqs = len(requirements)

            for req in requirements:
                label = req.get("requirement_label", "")
                best_match = None
                best_confidence = 0

                for c in classifications:
                    if self._match_requirement_to_classification(
                        label, c.get("classified_as", "")
                    ):
                        if c.get("confidence", 0) > best_confidence:
                            best_confidence = c.get("confidence", 0)
                            best_match = c

                if best_match and best_match.get("is_valid", False):
                    matched_count += 1
                    requirement_statuses.append({
                        "requirement_label": label,
                        "status": "matched",
                        "matched_doc_name": best_match.get(
                            "document_name", "Unknown"
                        ),
                        "classified_as": best_match.get("classified_as", ""),
                        "confidence": best_match.get("confidence", 0),
                    })
                elif best_match and not best_match.get("is_valid", False):
                    requirement_statuses.append({
                        "requirement_label": label,
                        "status": "issues",
                        "matched_doc_name": best_match.get(
                            "document_name", "Unknown"
                        ),
                        "classified_as": best_match.get("classified_as", ""),
                        "confidence": best_match.get("confidence", 0),
                        "issues": best_match.get("issues", []),
                    })
                else:
                    requirement_statuses.append({
                        "requirement_label": label,
                        "status": "missing",
                        "matched_doc_name": None,
                        "classified_as": None,
                        "confidence": 0,
                    })

            score = (
                int((matched_count / total_reqs) * 100)
                if total_reqs > 0
                else 0
            )

            missing_items = [
                r for r in requirement_statuses if r["status"] == "missing"
            ]
            issue_items = [
                r for r in requirement_statuses if r["status"] == "issues"
            ]
            matched_items = [
                r for r in requirement_statuses if r["status"] == "matched"
            ]

            parts = []
            if matched_count == total_reqs:
                parts.append(
                    f"✅ All {total_reqs} requirements for {visa_type} visa "
                    "are satisfied! Your application looks complete."
                )
            elif score >= 70:
                parts.append(
                    f"👍 Good progress! {matched_count}/{total_reqs} "
                    f"requirements met for your {visa_type} visa."
                )
            elif score >= 40:
                parts.append(
                    f"📋 Moderate readiness. {matched_count}/{total_reqs} "
                    f"requirements met for your {visa_type} visa."
                )
            else:
                parts.append(
                    f"⚠️ Low readiness. Only {matched_count}/{total_reqs} "
                    f"requirements met for your {visa_type} visa."
                )

            if missing_items:
                missing_names = [
                    r["requirement_label"] for r in missing_items[:5]
                ]
                parts.append(f"Missing: {', '.join(missing_names)}.")
                if len(missing_items) > 5:
                    parts.append(
                        f"And {len(missing_items) - 5} more items."
                    )

            if issue_items:
                for r in issue_items:
                    issues_list = r.get("issues", [])
                    if issues_list:
                        parts.append(
                            f"⚠️ {r['matched_doc_name']}: "
                            f"{'; '.join(issues_list[:2])}."
                        )

            parts.append("Upload more documents to improve your score.")

            return {
                "overall_score": score,
                "summary": " ".join(parts),
                "passed": matched_count,
                "failed": len(issue_items),
                "missing": len(missing_items),
                "requirement_statuses": requirement_statuses,
            }
        else:
            total = len(classifications)
            passed = sum(
                1
                for c in classifications
                if c.get("is_valid", False) and c.get("confidence", 0) >= 0.3
            )
            failed = sum(
                1 for c in classifications if not c.get("is_valid", False)
            )
            missing = total - passed - failed

            if total == 0:
                return {
                    "overall_score": 0,
                    "summary": "No documents uploaded yet.",
                    "passed": 0,
                    "failed": 0,
                    "missing": 0,
                    "requirement_statuses": [],
                }

            score = int((passed / total) * 100)

            if score >= 80:
                summary = (
                    f"Strong application for {visa_type} visa. "
                    f"{passed}/{total} documents verified successfully."
                )
            elif score >= 50:
                summary = (
                    f"Moderate readiness for {visa_type} visa. "
                    f"{passed}/{total} documents verified."
                )
            else:
                summary = (
                    f"Low readiness. "
                    f"Only {passed}/{total} documents meet requirements."
                )

            issues_found = []
            for c in classifications:
                if c.get("issues"):
                    issues_found.extend(c["issues"])
            if issues_found:
                summary += (
                    f" Key issues: {'; '.join(issues_found[:3])}."
                )

            return {
                "overall_score": score,
                "summary": summary,
                "passed": passed,
                "failed": failed,
                "missing": missing,
                "requirement_statuses": [],
            }
