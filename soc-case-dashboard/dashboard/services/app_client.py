import requests
from datetime import datetime, timedelta


class APIClient:
    def __init__(self, base_url: str, api_key: str, detection_url: str = None):
        self.base_url = base_url.rstrip("/")
        self.detection_url = (detection_url or "http://localhost:8005").rstrip("/")
        self.headers = {
            "X-API-Key": api_key
        }
        self.api_key = api_key

    def get_incidents(self, status="OPEN", limit=100):
        response = requests.get(
            f"{self.base_url}/v1/incidents",
            params={"status": status, "limit": limit},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_incident_detail(self, incident_id):
        response = requests.get(
            f"{self.base_url}/v1/incidents/{incident_id}",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def update_incident_notes(self, incident_id, notes):
        response = requests.post(
            f"{self.base_url}/v1/incidents/{incident_id}/notes",
            json={"notes": notes},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_alerts(self, since=None, limit=200):
        params = {"limit": limit}
        if since:
            params["since"] = since

        response = requests.get(
            f"{self.detection_url}/v1/alerts",
            params=params,
            headers={"Authorization": f"Bearer soc-internal-token-v1"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def hunt_logs(self, actor=None, service_name=None, normalized_path=None, time_from=None, time_to=None, limit=100):
        query = {}
        if actor:
            query["actor"] = actor
        if service_name:
            query["service_name"] = service_name
        if normalized_path:
            query["normalized_path"] = normalized_path

        payload = {
            "tenant_id": "placeholder",  # TODO: derive from session or API response
            "query": query,
            "time_from": time_from,
            "time_to": time_to,
            "limit": limit
        }

        response = requests.post(
            "http://normalizer:8001/internal/query-logs",
            json=payload,
            headers={"Authorization": f"Bearer soc-internal-token-v1"},
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_webhooks(self):
        response = requests.get(
            f"{self.base_url}/v1/webhooks",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def create_webhook(self, url, events):
        response = requests.post(
            f"{self.base_url}/v1/webhooks",
            json={"url": url, "events": events},
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()