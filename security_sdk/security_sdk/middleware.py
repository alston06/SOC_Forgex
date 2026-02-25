"""FastAPI / Starlette middleware that auto-captures HTTP requests as ActivityEvents."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from .client import TelemetryClient
from .models import ActivityEvent

logger = logging.getLogger("forgex_security_sdk.middleware")


class SecurityMonitoringMiddleware(BaseHTTPMiddleware):
    """Starlette / FastAPI middleware that transparently captures every HTTP
    request and enqueues an :class:`ActivityEvent` on the supplied
    :class:`TelemetryClient`.

    Parameters
    ----------
    app:
        The ASGI application (injected by Starlette).
    client:
        A :class:`TelemetryClient` instance used to ship events.
    exclude_paths:
        A set of URL paths to ignore (e.g. ``{"/health", "/metrics"}``).
    actor_header:
        The request header from which the actor (user identity) is read.
        Defaults to ``x-user-id``.  Falls back to ``"anonymous"``.
    """

    def __init__(
        self,
        app,  # noqa: ANN001 — Starlette typing
        client: TelemetryClient,
        exclude_paths: Optional[Set[str]] = None,
        actor_header: str = "x-user-id",
    ) -> None:
        super().__init__(app)
        self.client = client
        self.exclude_paths: Set[str] = exclude_paths or set()
        self.actor_header = actor_header

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        path = request.url.path

        # Skip excluded paths (e.g. health checks)
        if path in self.exclude_paths:
            return await call_next(request)

        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        event = ActivityEvent(
            timestamp=datetime.now(timezone.utc),
            event_type="http_request",
            actor=request.headers.get(self.actor_header) or "anonymous",
            resource=path,
            action=request.method,
            source="fastapi",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            extras={
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "query_string": str(request.url.query) if request.url.query else None,
            },
        )

        try:
            self.client.enqueue_event(event)
        except Exception:
            logger.exception("Failed to enqueue security event")

        return response
