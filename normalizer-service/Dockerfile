FROM python:3.14-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync

# Copy code
COPY normalizer/ ./normalizer/
COPY data/ ./data/
COPY main.py ./

# Expose port
EXPOSE 8001

# Run
CMD ["uv", "run", "python", "main.py"]
