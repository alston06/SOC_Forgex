# Copilot / AI Agent Instructions

Quick context
- This repo is a small FastAPI-style service layer using MongoDB. Key folders:
  - `core/` — configuration and security helpers ([core/config.py](core/config.py#L1-L20), [core/security.py](core/security.py#L1-L40)).
  - `db/` — Mongo client and `db` object used across services ([db/mongo.py](db/mongo.py#L1-L20)).
  - `models/` — Pydantic request schemas (see [models/internal_case_action.py](models/internal_case_action.py#L1-L40), [models/agent_output.py](models/agent_output.py#L1-L40)).
  - `services/` — business logic; interact with `db` collections (examples: [services/incident_service.py](services/incident_service.py#L1-L100), [services/notification_service.py](services/notification_service.py#L1-L120)).

What matters for code changes
- Imports use the `app` package root (e.g. `from app.db.mongo import db`). Ensure `PYTHONPATH` or test runner includes the repository root so `app` resolves.
- Configuration lives in `core/config.py` via Pydantic `Settings` (discoverable envs: `MONGO_URI`, `DB_NAME`, `INTERNAL_TOKEN`). Use a `.env` file for local dev.

Data & runtime patterns (concrete examples)
- Mongo collections used: `incidents`, `tenant_webhooks`, `notifications`, `api_keys`. Services read/write directly using `db.<collection>`.
- Incident documents follow the shape inserted by `open_incident` in `services/incident_service.py`: `_id` (UUID string), `tenant_id`, `detection_id`, `status` (`OPEN`/`RESOLVED`), `severity`, `created_at`/`updated_at` (UTC datetimes), `agent_summary` and `human_notes`.
- Tenant resolution: `core/security.py` resolves `X-API-Key` by hashing with SHA256 and looking up `db.api_keys`.
- Internal service auth: uses an `Authorization: Bearer <token>` header compared to `settings.INTERNAL_TOKEN`.

Coding conventions specific to this repo
- Use Pydantic models in `models/` for incoming payload validation — functions in `services/` expect these models.
- Use `from app.db.mongo import db` for DB access; do not re-create Mongo clients in service functions.
- Timestamps use `datetime.utcnow()` before inserting/updating documents.
- Use `str(uuid4())` for generating `_id` values for incidents (see `open_incident`).
- External HTTP calls use `requests` with short timeouts (see `notification_service.py`); treat these as potentially failing and record status to `notifications` collection.

Developer workflows & quick commands
- Install runtime deps (libraries inferred from imports):

  pip install fastapi pydantic pymongo requests uvicorn

- Local dev: set env vars (or `.env`) and ensure Mongo is running. For interactive testing, set `PYTHONPATH` and import modules directly:

  export PYTHONPATH=$(pwd)
  python -c "from app.services import incident_service; print(incident_service)"

- There is no app entrypoint or tests in the repo root. If you add an ASGI app, run via `uvicorn` from the project root and keep `PYTHONPATH` so `app.*` imports work.

Where to look when adding features
- New endpoints / API glue: add a top-level FastAPI app module (not present currently). Keep business logic inside `services/` and schemas in `models/`.
- DB schema changes: update all services that touch the collection and add migration notes in a new `docs/` file.

Safety notes for automated edits
- Don't change the `core/config.py` keys names — code references `settings.<NAME>` directly.
- Preserve synchronous behavior in `notification_service.py` unless you also add an async runtime and update callers.

If anything here is unclear or you'd like more examples (endpoints, tests, CI), tell me which area to expand.
