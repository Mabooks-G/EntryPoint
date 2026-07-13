FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libleptonica-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install Python deps
COPY backend/requirements.txt /app/backend/
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy the rest of the backend
COPY backend/ /app/backend/

# Copy frontend source and build it
COPY package.json package-lock.json /app/
RUN npm install
COPY . /app/
RUN npm run build

# Expose port
EXPOSE 10000

# Run FastAPI app
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "10000"]