FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --frozen

# Copy code
COPY agents/ ./agents/

# Expose both ports
EXPOSE 8002 8003

# Default to crewai service (override with docker-compose command)
CMD ["uv", "run", "python", "crewai.py"]
