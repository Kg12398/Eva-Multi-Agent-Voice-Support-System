# ============================================
# KG ElectroPower Voice Agent - Production Dockerfile
# ============================================

# Use a specific, stable version of Python slim
FROM python:3.11-slim as builder

# Set environment variables for non-interactive installs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies required for building C extensions and audio libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download the SentenceTransformer model to avoid runtime downloads
# This improves startup time and allows air-gapped/firewalled deployments
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Final Stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache/torch /root/.cache/torch

# Install lightweight runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application source
COPY . .

# Ensure the app doesn't run as root for security
RUN useradd -m gauri && chown -R gauri:gauri /app
USER gauri

# Expose FastAPI port (if used)
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Command to run the agent
# In production, we typically use the entrypoint script or direct python call
CMD ["python", "-m", "app.voice_pipeline.livekit_worker", "dev"]
