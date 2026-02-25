FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --frozen

# Copy code
COPY case/ ./case/

# Expose port
EXPOSE 8004

# Run
CMD ["uv", "run", "python", "main.py"]
