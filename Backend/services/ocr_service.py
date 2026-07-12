"""OCR Service — real text extraction from uploaded documents using Tesseract.

Tesseract is installed in the Docker container (tesseract-ocr, tesseract-ocr-eng, etc.).
This service writes uploaded file bytes to a temp file and runs tesseract on it,
returning the actual garbled OCR text for the AI to analyze.
"""

import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger("ocr")

# Supported image formats — try OCR on these
_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp",
    ".pnm", ".pgm", ".ppm",
}

# File extensions whose content is already text (skip OCR)
_TEXT_EXTENSIONS = {".txt", ".csv", ".html", ".htm", ".xml", ".json", ".md"}


class OCRService:

    async def extract_text(self, file_path: str, file_bytes: Optional[bytes] = None) -> str:
        """
        Extract text from an uploaded document using Tesseract OCR.

        For image files (PNG, JPG, etc.), runs tesseract on the file bytes.
        For PDFs, extracts text via PDL (fallback to tesseract per-page if needed).
        For text files, decodes the bytes directly.

        Returns raw OCR text — garbled, noisy, and exactly what the AI should see.
        """
        if not file_bytes:
            return ""

        ext = os.path.splitext(file_path)[1].lower()

        # ── Text files — decode directly ──────────────────────────────
        if ext in _TEXT_EXTENSIONS:
            try:
                content = file_bytes.decode("utf-8", errors="replace").strip()
                return content[:5000]
            except Exception as e:
                logger.warning("Failed to decode text file %s: %s", file_path, e)
                return ""

        # ── Images — run Tesseract ─────────────────────────────────────
        if ext in _IMAGE_EXTENSIONS:
            return await self._ocr_image(file_bytes)

        # ── PDF — try to extract / convert ────────────────────────────
        if ext == ".pdf":
            return await self._ocr_pdf(file_bytes)

        # ── Unknown — try OCR anyway as a fallback ────────────────────
        return await self._ocr_image(file_bytes)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    async def _ocr_image(image_bytes: bytes) -> str:
        """Run Tesseract OCR on raw image bytes."""
        try:
            import pytesseract
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_bytes))

            # Convert to RGB if paletted or RGBA (tesseract prefers RGB)
            if img.mode in ("P", "RGBA", "LA"):
                img = img.convert("RGB")

            # Run tesseract with multiple language support
            custom_config = (
                "--oem 3 --psm 3 "    # LSTM engine + automatic page segmentation
                "-c tessedit_char_whitelist="  # no char restrictions — capture everything
            )
            text = pytesseract.image_to_string(
                img,
                lang="eng+fra+deu+spa",
                config=custom_config,
            )

            clean = text.strip()
            if clean:
                logger.info("OCR extracted %d chars from image", len(clean))
            else:
                # Retry with different PSM for documents with little text
                text = pytesseract.image_to_string(
                    img,
                    lang="eng",
                    config="--oem 3 --psm 6",
                )
                clean = text.strip()
                logger.info("OCR (PSM=6) extracted %d chars from image", len(clean))

            return clean[:5000]  # cap at 5k chars

        except ImportError:
            logger.error("pytesseract or Pillow not installed — cannot OCR images")
            return "(OCR unavailable: pytesseract/Pillow not installed)"
        except Exception as e:
            logger.warning("Tesseract OCR failed: %s", e)
            return f"(OCR error: {e})"

    @staticmethod
    async def _ocr_pdf(pdf_bytes: bytes) -> str:
        """Extract text from a PDF — try pypdf2/pdfminer, fall back to tesseract on page images."""
        try:
            # Try pypdf2 first for digital PDFs
            try:
                import PyPDF2

                reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
                text_parts = []
                for page in reader.pages:
                    txt = page.extract_text()
                    if txt and txt.strip():
                        text_parts.append(txt.strip())
                if text_parts:
                    full = "\n\n".join(text_parts)
                    if len(full) > 100:
                        logger.info("Extracted %d chars from PDF (PyPDF2)", len(full))
                        return full[:5000]
            except ImportError:
                pass

            # Fallback: render pages as images and OCR each one
            try:
                import io
                from PIL import Image
                import pytesseract

                try:
                    from pdf2image import convert_from_bytes
                    images = convert_from_bytes(pdf_bytes, dpi=300)
                except ImportError:
                    # No pdf2image — write temp file and use pdftoppm if available
                    import subprocess
                    import tempfile

                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(pdf_bytes)
                        pdf_path = tmp.name

                    img_dir = tempfile.mkdtemp()
                    try:
                        subprocess.run(
                            ["pdftoppm", "-png", "-r", "300", pdf_path, os.path.join(img_dir, "page")],
                            capture_output=True,
                            timeout=30,
                        )
                        images = []
                        for f in sorted(os.listdir(img_dir)):
                            if f.endswith(".png"):
                                images.append(Image.open(os.path.join(img_dir, f)))
                    finally:
                        os.unlink(pdf_path)
                        for f in os.listdir(img_dir):
                            os.unlink(os.path.join(img_dir, f))
                        os.rmdir(img_dir)

                texts = []
                for img in images:
                    if img.mode in ("P", "RGBA", "LA"):
                        img = img.convert("RGB")
                    t = pytesseract.image_to_string(img, lang="eng+fra+deu+spa")
                    if t.strip():
                        texts.append(t.strip())

                full = "\n\n".join(texts)
                if full:
                    logger.info("OCR'd %d chars from PDF (%d pages)", len(full), len(images))
                    return full[:5000]

                return "(PDF OCR: no text extracted)"

            except Exception as e:
                logger.warning("PDF OCR fallback failed: %s", e)
                return f"(PDF OCR error: {e})"

        except Exception as e:
            logger.warning("PDF extraction failed: %s", e)
            return f"(PDF extraction error: {e})"