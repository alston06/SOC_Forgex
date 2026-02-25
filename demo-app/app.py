"""SOC Forgex Demo — FastAPI app with security_sdk middleware.

This app simulates a realistic web application (user auth, admin panel,
file storage) while automatically streaming every HTTP request to the
SOC Forgex ingestion pipeline through the security_sdk middleware.

A background simulator generates suspicious activity patterns (brute-force
login attempts, privilege escalation, data exfiltration) so the detection
engine and AI agents have interesting data to analyse.
"""

from __future__ import annotations

import asyncio
import random
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from security_sdk import TelemetryClient, ActivityEvent
from security_sdk.middleware import SecurityMonitoringMiddleware

# ── SDK client ──────────────────────────────────────────────────────
API_KEY = "test-api-key-123"  # matches init-mongo.js seed
INGESTION_URL = "http://localhost:8000"

sdk_client = TelemetryClient(
    api_key=API_KEY,
    endpoint=INGESTION_URL,
    flush_interval_s=3,  # flush every 3 s for demo speed
    service_name="demo-web-app",
    environment="development",
)


# ── Background event simulator ─────────────────────────────────────
async def _background_simulator():
    """Generate a continuous stream of realistic security events.

    Patterns simulated — each one maps to a detection rule:
    1. Normal HTTP traffic (baseline noise)
    2. Brute-force login bursts   → rule: brute-force-001 (event_type=auth, action=login_failed)
    3. Admin abuse                → rule: admin-abuse-001 (action in ADMIN_ACTIONS)
    4. Data exfiltration          → rule: data-exfil-001  (action=export, extras.bytes > 1M)
    5. HTTP error storms          → rule: error-storm-001 (event_type=http, extras.status_code 5xx)
    """
    users = ["alice", "bob", "charlie", "eve", "mallory", "admin"]
    normal_paths = [
        "/", "/dashboard", "/profile", "/settings",
        "/api/v1/users/me", "/api/v1/notifications",
    ]
    source_ips = [
        "192.168.1.42", "10.0.0.15", "203.0.113.77",
        "198.51.100.23", "172.16.0.99", "45.33.32.156",
    ]

    cycle = 0
    while True:
        cycle += 1
        try:
            # ── 1. Normal HTTP traffic (every cycle) ──
            for _ in range(random.randint(2, 4)):
                sdk_client.enqueue_event(ActivityEvent(
                    timestamp=datetime.now(timezone.utc),
                    event_type="http",
                    actor=random.choice(users[:4]),
                    resource=random.choice(normal_paths),
                    action="GET",
                    ip=random.choice(source_ips[:3]),
                    extras={"status_code": "200"},
                ))

            # ── 2. Brute-force login burst (every 2nd cycle) ──
            # Rule: brute-force-001 needs event_type="auth", action="login_failed"
            # Triggers at ≥5 failed logins from same (actor, ip) in 5 min
            if cycle % 2 == 0:
                attacker_ip = "45.33.32.156"
                target_user = "alice"
                for _ in range(random.randint(6, 12)):
                    sdk_client.enqueue_event(ActivityEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type="auth",
                        actor=target_user,
                        resource="/auth/login",
                        action="login_failed",
                        ip=attacker_ip,
                        extras={
                            "reason": "invalid_credentials",
                            "user_agent": "python-requests/2.31.0",
                        },
                    ))

            # ── 3. Admin abuse (every 3rd cycle) ──
            # Rule: admin-abuse-001 needs action in ADMIN_ACTIONS, user_role != admin
            # Triggers at ≥10 admin actions by non-admin in 1 hour
            if cycle % 3 == 0:
                admin_actions = [
                    "user_create", "user_delete", "user_role_change",
                    "config_modify", "data_delete", "export_all",
                ]
                for _ in range(random.randint(4, 8)):
                    sdk_client.enqueue_event(ActivityEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type="admin",
                        actor="eve",
                        resource=f"/admin/{random.choice(['users', 'settings', 'config'])}",
                        action=random.choice(admin_actions),
                        ip="203.0.113.77",
                        extras={"elevated": True},
                    ))

            # ── 4. Data exfiltration (every 5th cycle) ──
            # Rule: data-exfil-001 needs action="export", extras.bytes > 1_000_000
            if cycle % 5 == 0:
                for _ in range(random.randint(2, 4)):
                    sdk_client.enqueue_event(ActivityEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type="data",
                        actor="mallory",
                        resource=f"/api/v1/export/{random.choice(['users', 'transactions', 'secrets'])}",
                        action="export",
                        ip="198.51.100.23",
                        extras={
                            "bytes": random.randint(2_000_000, 50_000_000),
                            "format": random.choice(["csv", "json", "zip"]),
                        },
                    ))

            # ── 5. HTTP error storm (every 4th cycle) ──
            # Rule: error-storm-001 needs event_type="http", extras.status_code in 5xx
            # Triggers at ≥50 errors from same (ip, normalized_path) in 10 min
            if cycle % 4 == 0:
                storm_ip = "172.16.0.99"
                storm_path = "/api/v1/process"
                for _ in range(random.randint(15, 25)):
                    sdk_client.enqueue_event(ActivityEvent(
                        timestamp=datetime.now(timezone.utc),
                        event_type="http",
                        actor="system",
                        resource=storm_path,
                        action="POST",
                        ip=storm_ip,
                        extras={"status_code": random.choice(["500", "502", "503"])},
                    ))

        except Exception as exc:
            print(f"[simulator] error: {exc}")

        await asyncio.sleep(random.uniform(3, 6))  # faster pace for demo


# ── App lifespan ────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background simulator on startup, clean up SDK on shutdown."""
    task = asyncio.create_task(_background_simulator())
    print("✅  Background event simulator started")
    print(f"✅  SDK shipping events to {INGESTION_URL}")
    yield
    task.cancel()
    sdk_client.close()
    print("🛑  SDK flushed & closed")


# ── FastAPI app ─────────────────────────────────────────────────────
app = FastAPI(
    title="SOC Forgex Demo App",
    description="Simulated web app protected by SOC Forgex security monitoring.",
    version="0.1.0",
    lifespan=lifespan,
)

# Attach SDK middleware — every HTTP request is auto-captured
app.add_middleware(
    SecurityMonitoringMiddleware,
    client=sdk_client,
    exclude_paths={"/health", "/docs", "/openapi.json", "/favicon.ico"},
)


# ── Simulated app endpoints ────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "demo-web-app"}


@app.get("/")
async def homepage():
    return {"message": "Welcome to the SOC Forgex Demo App", "docs": "/docs"}


# ── Auth endpoints ──────────────────────────────────────────────────

FAKE_USERS: dict[str, str] = {
    "alice": "password123",
    "bob": "s3cret!",
    "admin": "admin",
}


@app.post("/auth/login")
async def login(request: Request):
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")
    if FAKE_USERS.get(username) == password:
        return {"token": f"fake-jwt-{uuid.uuid4().hex[:16]}", "user": username}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/logout")
async def logout():
    return {"message": "Logged out"}


# ── User endpoints ──────────────────────────────────────────────────

@app.get("/api/v1/users/me")
async def get_me(x_user_id: str = Header(default="anonymous")):
    return {"user_id": x_user_id, "role": "viewer", "active": True}


@app.get("/api/v1/notifications")
async def notifications():
    return {"notifications": [], "unread": 0}


@app.get("/dashboard")
async def dashboard():
    return {"widgets": ["alerts", "metrics", "recent_activity"]}


@app.get("/profile")
async def profile():
    return {"name": "Demo User", "email": "demo@example.com"}


@app.get("/settings")
async def settings_page():
    return {"theme": "dark", "mfa_enabled": False}


# ── Admin endpoints (these will trigger detection rules) ────────────

@app.get("/admin/users")
async def admin_users():
    return {"users": list(FAKE_USERS.keys()), "total": len(FAKE_USERS)}


@app.get("/admin/settings")
async def admin_settings():
    return {"maintenance_mode": False, "debug": False}


@app.get("/admin/logs")
async def admin_logs():
    return {"logs": ["[INFO] system healthy", "[WARN] disk 80% full"]}


@app.get("/admin/api-keys")
async def admin_api_keys():
    return {"keys": ["sk-***redacted***"]}


@app.get("/admin/export-all")
async def admin_export():
    """Simulates a bulk data export — suspicious in large volumes."""
    return {"status": "export_started", "estimated_rows": 150_000}


# ── Data export endpoints (exfiltration signals) ────────────────────

@app.get("/api/v1/export/{resource}")
async def export_data(resource: str):
    return {
        "resource": resource,
        "rows": random.randint(1000, 50000),
        "format": "csv",
        "download_url": f"/files/{uuid.uuid4().hex}.csv",
    }


# ── Status & info ──────────────────────────────────────────────────

@app.get("/status")
async def pipeline_status():
    """Quick view of what the demo is doing."""
    return {
        "demo_app": "running",
        "sdk_target": INGESTION_URL + "/v1/logs",
        "sdk_service": "demo-web-app",
        "background_simulator": "active",
        "description": (
            "The background simulator generates brute-force login attempts, "
            "privilege escalation, data exfiltration, and API scanning events. "
            "These flow through: Ingestion → Kafka → Normalizer → OpenSearch → "
            "Detection Engine → Agent Trigger → CrewAI Agents → Case Service."
        ),
        "view_dashboard": "http://localhost:8501",
        "view_cases": "http://localhost:8004/docs",
        "view_detections": "http://localhost:8005/docs",
        "cache_stats": "http://localhost:8003/cache/stats",
    }
