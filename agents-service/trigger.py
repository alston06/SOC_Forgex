"""Entry point for agent trigger service."""
import uvicorn

from agents.trigger.config import settings


def main():
    """Run the agent trigger service."""
    uvicorn.run(
        "agents.trigger.app:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
