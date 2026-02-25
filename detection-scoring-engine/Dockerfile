FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy pyproject.toml and uv.lock
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY detection/ ./detection/

# Expose port
EXPOSE 8005

# Run with uvicorn
CMD ["uv", "run", "uvicorn", "detection.app:app", "--host", "0.0.0.0", "--port", "8005"]
