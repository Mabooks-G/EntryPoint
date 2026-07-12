FROM python:3.11-slim

# Install system dependencies: Tesseract OCR (for image text extraction)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend into a backend/ subdirectory so imports like
# "from backend.config.settings" resolve correctly
COPY . /app/backend/

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Start the server
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]