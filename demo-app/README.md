# SOC Forgex Demo App

A minimal FastAPI application that demonstrates the **SOC Forgex** security monitoring platform end-to-end.

## What it does

1. **SDK Middleware** — Every HTTP request to this app is automatically captured by the `security_sdk` middleware and streamed to the ingestion pipeline.

2. **Background Simulator** — Generates realistic attack patterns in the background:
   - 🔐 **Brute-force login** — Rapid failed login attempts from suspicious IPs
   - 🔓 **Privilege escalation** — User self-promoting to admin role
   - 📤 **Data exfiltration** — Large bulk data downloads
   - 🔍 **API scanning** — Probing for `.env`, `wp-admin`, path traversal, etc.

3. **Full Pipeline Flow** — Events travel through:
   ```
   Demo App → SDK → Ingestion → Kafka → Normalizer → OpenSearch
                                                    → Detection Engine → Agent Trigger → CrewAI Agents → Cases
   ```

## Quick start

```bash
# 1. Start infrastructure (from repo root)
docker compose up -d

# 2. Run the demo app
cd demo-app
uv run uvicorn app:app --port 9000 --reload

# 3. Open the dashboard
open http://localhost:8501        # SOC Dashboard
open http://localhost:9000/docs   # Demo app Swagger
open http://localhost:9000/status # Pipeline status
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Homepage |
| POST | `/auth/login` | Simulated login |
| POST | `/auth/logout` | Simulated logout |
| GET | `/dashboard` | User dashboard |
| GET | `/admin/users` | Admin panel |
| GET | `/admin/export-all` | Bulk export (sus) |
| GET | `/api/v1/export/{resource}` | Data export |
| GET | `/status` | Pipeline status & links |
| GET | `/health` | Health check (not tracked) |
