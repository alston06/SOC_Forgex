"""Telemetry client — batches and ships ActivityEvents to the ingestion API."""

from __future__ import annotations

import gzip
import json
import logging
import queue
import threading
import time
from typing import List, Optional

import requests

from .models import ActivityEvent

logger = logging.getLogger("forgex_security_sdk")


class TelemetryClient:
    """Background-threaded telemetry client.

    Events are enqueued and flushed in batches on a configurable interval.
    Payloads >1 KiB are gzip-compressed automatically.  Failed sends are
    retried with exponential back-off and eventually dropped to avoid blocking
    the host application.

    Parameters
    ----------
    api_key:
        Tenant API key — sent as ``X-API-Key`` header.
    endpoint:
        Base URL of the Forgex ingestion service (e.g. ``http://localhost:8000``).
        ``/v1/logs`` is appended automatically.
    service_name:
        Optional service label stamped onto every event that lacks one.
    environment:
        Environment label (``prod``, ``staging``, ``dev``).
    flush_interval_s:
        Seconds between automatic flushes (default 5).
    max_batch_size:
        Maximum number of events sent in a single HTTP request.
    max_retry_attempts:
        Number of retries (with exponential backoff) before dropping a batch.
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        service_name: Optional[str] = None,
        environment: str = "prod",
        flush_interval_s: float = 5.0,
        max_batch_size: int = 100,
        max_retry_attempts: int = 3,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/") + "/v1/logs"
        self.service_name = service_name
        self.environment = environment
        self.flush_interval_s = flush_interval_s
        self.max_batch_size = max_batch_size
        self.max_retry_attempts = max_retry_attempts

        self._queue: queue.Queue[ActivityEvent] = queue.Queue()
        self._stop = False
        self._stop_event = threading.Event()
        self._session = requests.Session()

        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue_event(self, event: ActivityEvent) -> None:
        """Add *event* to the send queue.

        If *service_name* / *environment* were configured on the client and
        the event doesn't already have them, they are injected automatically.
        """
        if self.service_name and not event.service_name:
            event.service_name = self.service_name
        if self.environment and not event.environment:
            event.environment = self.environment
        try:
            self._queue.put_nowait(event)
        except Exception:
            logger.exception("Failed to enqueue telemetry event")

    def flush(self) -> None:
        """Immediately flush any buffered events."""
        self._flush_batch()

    def close(self, timeout: float = 5.0) -> None:
        """Stop the background worker, flush remaining events, and close the
        HTTP session.

        Call this when the application is shutting down.
        """
        self._stop = True
        self._stop_event.set()
        self._flush_batch()
        self._thread.join(timeout)
        try:
            self._session.close()
        except Exception:
            logger.exception("Error closing HTTP session")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _worker(self) -> None:
        while not self._stop:
            self._stop_event.wait(self.flush_interval_s)
            self._stop_event.clear()
            self._flush_batch()

    def _flush_batch(self) -> None:
        events: List[ActivityEvent] = []
        while not self._queue.empty() and len(events) < self.max_batch_size:
            try:
                events.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if not events:
            return

        try:
            payload = [e.model_dump(mode="json") for e in events]
            payload_bytes = json.dumps(payload, default=str).encode()

            headers = {
                "X-API-Key": self.api_key,
                "Content-Type": "application/json",
            }

            if len(payload_bytes) > 1024:
                payload_bytes = gzip.compress(payload_bytes)
                headers["Content-Encoding"] = "gzip"

            attempt = 0
            while attempt < self.max_retry_attempts:
                try:
                    resp = self._session.post(
                        self.endpoint,
                        headers=headers,
                        data=payload_bytes,
                        timeout=5,
                    )
                    resp.raise_for_status()
                    return  # success
                except Exception:
                    attempt += 1
                    logger.exception(
                        "Telemetry batch post failed (attempt %d/%d)",
                        attempt,
                        self.max_retry_attempts,
                    )
                    time.sleep(0.5 * (2 ** (attempt - 1)))

            logger.error(
                "Dropping telemetry batch after %d failed attempts (events=%d)",
                self.max_retry_attempts,
                len(events),
            )
        except Exception:
            logger.exception("Unexpected error while preparing telemetry payload")
