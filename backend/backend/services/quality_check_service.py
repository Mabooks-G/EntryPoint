import os
import io
import logging
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image, ImageFilter, ImageStat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

MIN_IMAGE_WIDTH = 200   # pixels — hard block only truly tiny images
MIN_IMAGE_HEIGHT = 200  # pixels
WARN_IMAGE_WIDTH = 600  # pixels — warn but still allow through
WARN_IMAGE_HEIGHT = 600  # pixels
MIN_DPI = 150           # dots per inch (applied to images that carry DPI metadata)

BLUR_VARIANCE_THRESHOLD = 80.0   # Laplacian variance below this → blurry
MAX_FILE_SIZE_MB = 20


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------

@dataclass
class QualityCheckResult:
    passed: bool
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "warnings": self.warnings,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def check_document_quality(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str] = None,
) -> QualityCheckResult:
    """
    Run all quality checks against an uploaded document.

    Args:
        file_bytes:  Raw file content.
        filename:    Original filename (used to infer type when mime_type is absent).
        mime_type:   MIME type reported by the client (optional but preferred).

    Returns:
        QualityCheckResult with passed flag, warnings, and errors.
    """
    warnings: list[str] = []
    errors: list[str] = []

    ext = os.path.splitext(filename.lower())[1]
    effective_mime = mime_type or _mime_from_extension(ext)

    # 1. Format check
    if not _is_supported_format(ext, effective_mime):
        errors.append(
            f"Unsupported file format '{ext or effective_mime}'. "
            f"Please upload a PDF, JPG, or PNG."
        )
        return QualityCheckResult(passed=False, errors=errors)

    # 2. File size check
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        errors.append(
            f"File is too large ({size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB."
        )
        return QualityCheckResult(passed=False, errors=errors)

    if size_mb == 0:
        errors.append("File appears to be empty.")
        return QualityCheckResult(passed=False, errors=errors)

    # 3. Route to type-specific checks
    if effective_mime == "application/pdf" or ext == ".pdf":
        pdf_errors, pdf_warnings = _check_pdf(file_bytes)
        errors.extend(pdf_errors)
        warnings.extend(pdf_warnings)
    else:
        img_errors, img_warnings = _check_image(file_bytes, filename)
        errors.extend(img_errors)
        warnings.extend(img_warnings)

    passed = len(errors) == 0
    return QualityCheckResult(passed=passed, warnings=warnings, errors=errors)


# ---------------------------------------------------------------------------
# PDF checks
# ---------------------------------------------------------------------------

def _check_pdf(file_bytes: bytes) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    # Corruption / open check
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as exc:
        logger.warning("PDF open failed: %s", exc)
        errors.append("The PDF file is corrupted or could not be read.")
        return errors, warnings

    # Empty document
    page_count = doc.page_count
    if page_count == 0:
        errors.append("The PDF has no pages.")
        doc.close()
        return errors, warnings

    # Warn on single-page multi-page docs (e.g. passport should have 2 pages)
    if page_count == 1:
        warnings.append(
            "Only one page was detected. If this document has multiple pages "
            "(e.g. a passport data page and bio page), please re-scan all pages."
        )

    # Check each page for content and image quality
    blank_pages: list[int] = []
    blurry_pages: list[int] = []

    for page_num in range(page_count):
        page = doc[page_num]

        # Blank page detection via text + image presence
        text = page.get_text().strip()
        image_list = page.get_images(full=False)
        if not text and not image_list:
            blank_pages.append(page_num + 1)
            continue

        # Quality-check embedded images on the page
        for img_index, img_info in enumerate(image_list):
            xref = img_info[0]
            try:
                base_image = doc.extract_image(xref)
                img_bytes = base_image["image"]
                img = Image.open(io.BytesIO(img_bytes)).convert("L")  # greyscale
                if _is_blurry(img):
                    blurry_pages.append(page_num + 1)
                    break  # one blurry image per page is enough to flag
            except Exception as exc:
                logger.debug("Could not analyse image on page %d: %s", page_num + 1, exc)

    if blank_pages:
        page_list = ", ".join(str(p) for p in blank_pages)
        warnings.append(f"Page(s) {page_list} appear to be blank or contain no readable content.")

    if blurry_pages:
        page_list = ", ".join(str(p) for p in blurry_pages)
        warnings.append(
            f"Page(s) {page_list} contain blurry or low-quality images. "
            "Please re-scan for better results."
        )

    doc.close()
    return errors, warnings


# ---------------------------------------------------------------------------
# Image checks
# ---------------------------------------------------------------------------

def _check_image(file_bytes: bytes, filename: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        img = Image.open(io.BytesIO(file_bytes))
        img.verify()  # catches truncated / corrupted images
        img = Image.open(io.BytesIO(file_bytes))  # re-open after verify (verify closes it)
    except Exception as exc:
        logger.warning("Image open failed for %s: %s", filename, exc)
        errors.append("The image file is corrupted or could not be opened.")
        return errors, warnings

    width, height = img.size

    # Resolution check — hard block if truly tiny, warn if below recommended
    if width < MIN_IMAGE_WIDTH or height < MIN_IMAGE_HEIGHT:
        errors.append(
            f"Image is too small to process ({width}×{height} px). "
            f"Minimum required is {MIN_IMAGE_WIDTH}×{MIN_IMAGE_HEIGHT} px."
        )
    elif width < WARN_IMAGE_WIDTH or height < WARN_IMAGE_HEIGHT:
        warnings.append(
            f"Image resolution is low ({width}×{height} px). "
            f"For best results, {WARN_IMAGE_WIDTH}×{WARN_IMAGE_HEIGHT} px or higher is recommended."
        )

    # DPI metadata check (not all images carry this)
    dpi_info = img.info.get("dpi")
    if dpi_info:
        dpi = min(dpi_info)  # use the lower of x/y DPI
        if dpi < MIN_DPI:
            warnings.append(
                f"Image DPI is low ({dpi:.0f} DPI). "
                f"A minimum of {MIN_DPI} DPI is recommended for accurate text extraction."
            )

    # Blur check
    greyscale = img.convert("L")
    if _is_blurry(greyscale):
        warnings.append(
            "The image appears blurry. Please re-scan or retake the photo with better focus."
        )

    return errors, warnings


# ---------------------------------------------------------------------------
# Blur detection (Laplacian variance)
# ---------------------------------------------------------------------------

def _is_blurry(greyscale_img: Image.Image) -> bool:
    """
    Detect blur using the variance of the Laplacian.
    A low variance indicates a lack of edges → blurry image.
    """
    laplacian = greyscale_img.filter(ImageFilter.Kernel(
        size=(3, 3),
        kernel=[0, 1, 0, 1, -4, 1, 0, 1, 0],
        scale=1,
        offset=128,
    ))
    stat = ImageStat.Stat(laplacian)
    variance = stat.var[0]
    return variance < BLUR_VARIANCE_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_supported_format(ext: str, mime_type: Optional[str]) -> bool:
    return ext in SUPPORTED_EXTENSIONS or mime_type in SUPPORTED_MIME_TYPES


def _mime_from_extension(ext: str) -> Optional[str]:
    mapping = {
        ".pdf": "application/pdf",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(ext)