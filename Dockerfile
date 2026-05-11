# BharatData Engine - Production Dockerfile
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH /app

# Set work directory
WORKDIR /app

# Install system dependencies for Playwright and Crawl4AI
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    librandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libvulkan1 \
    libxshmfence1 \
    libglu1-mesa \
    build-essential \
    python3-dev \
    libpq-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pipeline/requirements.txt /app/pipeline/requirements.txt
RUN pip install --no-cache-dir -r /app/pipeline/requirements.txt
RUN pip install --no-cache-dir crawl4ai

# Install Playwright browsers (Chromium only for lean build)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy project files
COPY . /app/

# Expose port (if needed for API, otherwise optional)
EXPOSE 8000

# Default command: Runs the Census PCA dry-run as a sanity check
# Alternatively, use: python -m pipeline.engine.orchestrator --source <SOURCE>
CMD ["python", "-m", "pipeline.engine.orchestrator", "--source", "census_2011_pca", "--dry-run"]
