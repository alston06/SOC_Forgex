"""Entry point for CrewAI service."""
import uvicorn

from agents.crewai.config import settings


def main():
    """Run CrewAI service."""
    uvicorn.run(
        "agents.crewai.app:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
