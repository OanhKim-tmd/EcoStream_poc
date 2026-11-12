# Lightweight Python 3.11 Image for Cloud & On-Premise Deployment (Railway, Cloud Run, Render, HF Spaces)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOST=0.0.0.0

WORKDIR /app

# Install system dependencies for PDF rendering, Vietnamese fonts & OCR (Poppler + Tesseract + DejaVu)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-vie \
    poppler-utils \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create writable directories for non-root containers
RUN mkdir -p /app/runs /app/data/samples && chmod -R 777 /app/runs /app/data

EXPOSE 7860 8000

# Start FastAPI server (automatically binds to $PORT)
CMD ["python", "-m", "ecostream.app"]
