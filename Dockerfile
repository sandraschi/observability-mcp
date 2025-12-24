# Observability MCP Server - FastMCP 2.14.1 with OpenTelemetry
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for OpenTelemetry and monitoring
RUN apt-get update && apt-get install -y \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/

# Create data directory for persistent storage
RUN mkdir -p /app/data && chmod 755 /app/data

# Set data directory environment variable
ENV MCP_DATA_DIR=/app/data

# Expose Prometheus metrics port
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9090/metrics || exit 1

# Default command
CMD ["python", "-m", "observability_mcp.server"]

# Labels for metadata
LABEL org.opencontainers.image.title="Observability MCP Server" \
      org.opencontainers.image.description="FastMCP 2.14.1-powered observability server for MCP ecosystems" \
      org.opencontainers.image.version="0.1.0" \
      org.opencontainers.image.authors="Sandra Schipal" \
      org.opencontainers.image.source="https://github.com/sandraschi/observability-mcp" \
      org.opencontainers.image.licenses="MIT"
