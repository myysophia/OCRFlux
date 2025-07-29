# OCRFlux API Service Dockerfile
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel && \
    pip install -e .

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    OCRFLUX_ENV=production

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    # PDF processing
    poppler-utils \
    poppler-data \
    # Fonts for better text recognition
    fonts-liberation \
    fonts-dejavu-core \
    # Image processing
    libmagic1 \
    # System utilities
    curl \
    procps \
    # Cleanup
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r ocrflux && useradd -r -g ocrflux -d /app -s /bin/bash ocrflux

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=ocrflux:ocrflux . .

# Create necessary directories
RUN mkdir -p /app/logs /app/tmp /app/models && \
    chown -R ocrflux:ocrflux /app

# Switch to non-root user
USER ocrflux

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "run_server.py", "--mode", "prod", "--host", "0.0.0.0", "--port", "8000"]

# Labels for metadata
LABEL maintainer="OCRFlux Team <support@ocrflux.example.com>" \
      version="1.0.0" \
      description="OCRFlux API Service - Fast, efficient OCR powered by open visual language models" \
      org.opencontainers.image.title="OCRFlux API Service" \
      org.opencontainers.image.description="REST API service for PDF and image OCR processing" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.vendor="OCRFlux Team" \
      org.opencontainers.image.licenses="MIT"