# Multi-stage Docker build for llm-task-framework
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy build files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Install build tools and create wheel
RUN pip install hatch build && \
    python -m build --wheel

# Runtime stage
FROM python:3.11-slim as runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy wheel from builder stage
COPY --from=builder /app/dist/*.whl /tmp/

# Install the package
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD llm-task-framework --help || exit 1

# Set default command
CMD ["llm-task-framework"]

# Labels for better container management
LABEL maintainer="LLM Task Framework Contributors" \
      version="1.0" \
      description="Generic framework for building LLM-powered task execution systems" \
      org.opencontainers.image.source="https://github.com/yourusername/llm-task-framework" \
      org.opencontainers.image.documentation="https://llm-task-framework.readthedocs.io" \
      org.opencontainers.image.licenses="MIT"
