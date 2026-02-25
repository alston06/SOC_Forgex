"""Entry point for case service."""
import uvicorn

from case.config import settings


def main():
    """Run the case service."""
    uvicorn.run(
        "case.app:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
