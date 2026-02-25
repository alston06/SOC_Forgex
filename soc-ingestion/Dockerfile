FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync

# Copy code
COPY app/ ./app/
COPY main.py ./

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "python", "main.py"]
