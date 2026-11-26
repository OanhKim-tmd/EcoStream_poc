# Lightweight Python 3.11 Image for Cloud & On-Premise Deployment (Railway, Cloud Run, Render, HF Spaces)
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOST=0.0.0.0

WORKDIR /app

# Vietnamese-capable font for PDF report rendering (no OCR packages needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files (.dockerignore keeps runs/, .git/, caches and local data out of the image)
COPY . .

# Unprivileged user. Only runs/ and the ingestion cache are writable; the code and
# bundled sample data stay read-only for the app user.
RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin ecostream \
    && mkdir -p /app/runs /app/.cache \
    && chown -R ecostream:ecostream /app/runs /app/.cache

USER ecostream

EXPOSE 7860 8000

# Start FastAPI server (automatically binds to $PORT). Refuses to start without
# ECOSTREAM_API_KEY and ECOSTREAM_ENCRYPTION_KEY (see ecostream/app/server.py).
CMD ["python", "-m", "ecostream.app"]
