# Forgex Security SDK

> Python SDK for **SOC Forgex** — captures HTTP activity from your FastAPI / ASGI
> apps and streams it to the Forgex ingestion pipeline for real-time threat
> detection, scoring, and automated incident response.

## Installation

```bash
pip install forgex-security-sdk
```

For FastAPI middleware support:

```bash
pip install "forgex-security-sdk[fastapi]"
```

## Quick Start

### 1. Direct Client Usage

```python
from datetime import datetime, timezone
from security_sdk import TelemetryClient, ActivityEvent

client = TelemetryClient(
    api_key="your-api-key",
    endpoint="https://ingest.your-soc.example.com",
    service_name="billing-api",
    environment="production",
)

# Send an event manually
client.enqueue_event(ActivityEvent(
    timestamp=datetime.now(timezone.utc),
    event_type="user.login",
    actor="user@example.com",
    resource="/auth/login",
    action="POST",
    ip="203.0.113.42",
))

# Flush on shutdown
client.close()
```

### 2. FastAPI Middleware (Recommended)

The middleware automatically captures every HTTP request as an `ActivityEvent`
and sends it in batches to your Forgex ingestion endpoint.

```python
from fastapi import FastAPI
from security_sdk import TelemetryClient
from security_sdk.middleware import SecurityMonitoringMiddleware

app = FastAPI()

telemetry = TelemetryClient(
    api_key="your-api-key",
    endpoint="https://ingest.your-soc.example.com",
    service_name="billing-api",
    environment="production",
)

app.add_middleware(SecurityMonitoringMiddleware, client=telemetry)


@app.get("/")
def root():
    return {"status": "ok"}
```

Every request to your app will now generate a security telemetry event that
flows through:

```
SDK → Ingestion API → Kafka (raw-activity) → Normalizer → Detection Engine → Agent Team
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `api_key` | *required* | Your tenant API key (passed as `X-API-Key` header) |
| `endpoint` | *required* | Base URL of the Forgex ingestion service |
| `service_name` | `None` | Name of your service (auto-tagged on events) |
| `environment` | `"prod"` | Environment label (`prod`, `staging`, `dev`) |
| `flush_interval_s` | `5.0` | How often the background worker flushes events |
| `max_batch_size` | `100` | Max events per HTTP POST |
| `max_retry_attempts` | `3` | Retries with exponential backoff on failure |

## Middleware Options

The `SecurityMonitoringMiddleware` accepts:

| Parameter | Default | Description |
|---|---|---|
| `client` | *required* | A `TelemetryClient` instance |
| `exclude_paths` | `set()` | Paths to skip (e.g. `{"/health", "/metrics"}`) |
| `actor_header` | `"x-user-id"` | Header to extract the actor/user identity from |

## ActivityEvent Schema

```python
class ActivityEvent(BaseModel):
    timestamp: datetime          # When the event occurred (UTC)
    event_type: str              # e.g. "http_request", "user.login"
    actor: str                   # User or service identity
    resource: str                # URL path or resource identifier
    action: str                  # HTTP method or action verb
    source: str = "unknown"      # Origin system
    ip: Optional[str]            # Client IP address
    user_agent: Optional[str]    # Client user-agent string
    service_name: Optional[str]  # Service that produced the event
    environment: Optional[str]   # Deployment environment
    extras: Dict[str, Any] = {}  # Arbitrary metadata
    idempotency_key: Optional[str]  # For deduplication
```

## Publishing to PyPI

```bash
cd security_sdk/
pip install build twine
python -m build
twine upload dist/*
```

## License

MIT
