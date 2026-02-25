# SOC Case Management Dashboard

Streamlit-based dashboard for managing security incidents and viewing alerts.

## Features

- **Overview**: View active incidents count, alerts/hour, severity distribution, and MTTA/MTTR metrics
- **Alerts**: Browse recent detections with filtering and detail view
- **Incidents**: List and search active incidents with session-based detail navigation
- **Incident Detail**: View full incident context including agent analysis, detection info, related logs, and human notes
- **Hunting**: Query logs by actor, service name, resource path, and time range
- **Settings**: Manage webhooks, view API key, and SDK integration health

## Setup

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run the dashboard

From the `dashboard/` directory:

```bash
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`.

### Configuration

At login, configure:

- **API Key**: From your SOC platform (used for public API calls to case service)
- **Case Service URL**: Default `http://localhost:8004` (must be reachable)
- **Detection Service URL**: Default `http://localhost:8005` (must be reachable)

## Architecture

- `app.py` — Main entry point; manages tabs and session state
- `pages/` — Individual page implementations (overview, alerts, incidents, etc.)
- `services/app_client.py` — API client wrapper for case and detection services

## API Dependencies

The dashboard calls:

- **Case Service** (port 8004):
  - `GET /v1/incidents` — list incidents
  - `GET /v1/incidents/{id}` — get incident detail with detection and logs
  - `POST /v1/incidents/{id}/notes` — update human notes
  - `GET /v1/webhooks` — list webhooks
  - `POST /v1/webhooks` — create webhook

- **Detection Service** (port 8005):
  - `GET /v1/alerts` — list detections (requires internal auth token)

- **Normalizer Service** (internal, for hunting):
  - `POST /internal/query-logs` — query logs (stub in app_client.py)

## Notes

- Hunting and some advanced features require backend services to be running
- MTTA/MTTR metrics are stubs and require case status history from the backend
- SDK integration health is a stub and should be fed from `ingestion_metrics` collection
