import requests


class DashboardClient:
    """API client for the SOC Case Service dashboard endpoints."""

    def __init__(self, base_url: str, jwt_token: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {jwt_token}"}

    @staticmethod
    def login(base_url: str, username: str, password: str) -> dict:
        resp = requests.post(
            f"{base_url.rstrip('/')}/dashboard/auth/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def register(
        base_url: str, username: str, password: str, organization: str
    ) -> dict:
        resp = requests.post(
            f"{base_url.rstrip('/')}/dashboard/auth/register",
            json={
                "username": username,
                "password": password,
                "organization": organization,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_me(self) -> dict:
        resp = requests.get(
            f"{self.base_url}/dashboard/auth/me",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # --- Stats ---
    def get_stats(self) -> dict:
        resp = requests.get(
            f"{self.base_url}/dashboard/stats",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # --- Incidents ---
    def get_incidents(self, status=None, severity=None, limit=50) -> list:
        params = {"limit": limit}
        if status:
            params["status"] = status
        if severity:
            params["severity"] = severity
        resp = requests.get(
            f"{self.base_url}/dashboard/incidents",
            params=params,
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def get_incident_detail(self, incident_id: str) -> dict:
        resp = requests.get(
            f"{self.base_url}/dashboard/incidents/{incident_id}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def update_incident_status(self, incident_id: str, status: str) -> dict:
        resp = requests.post(
            f"{self.base_url}/dashboard/incidents/{incident_id}/status",
            json={"status": status},
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def update_incident_notes(self, incident_id: str, notes: str) -> dict:
        resp = requests.post(
            f"{self.base_url}/dashboard/incidents/{incident_id}/notes",
            json={"notes": notes},
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # --- Alerts ---
    def get_alerts(self, limit=100, since=None) -> list:
        params = {"limit": limit}
        if since:
            params["since"] = since
        resp = requests.get(
            f"{self.base_url}/dashboard/alerts",
            params=params,
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # --- API Keys ---
    def get_api_keys(self) -> list:
        resp = requests.get(
            f"{self.base_url}/dashboard/api-keys",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def create_api_key(self, name: str) -> dict:
        resp = requests.post(
            f"{self.base_url}/dashboard/api-keys",
            json={"name": name},
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def revoke_api_key(self, key_id: str) -> dict:
        resp = requests.delete(
            f"{self.base_url}/dashboard/api-keys/{key_id}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    # --- Webhooks ---
    def get_webhooks(self) -> list:
        resp = requests.get(
            f"{self.base_url}/dashboard/webhooks",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def create_webhook(self, url: str, events: list) -> dict:
        resp = requests.post(
            f"{self.base_url}/dashboard/webhooks",
            json={"url": url, "events": events},
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def delete_webhook(self, webhook_id: str) -> dict:
        resp = requests.delete(
            f"{self.base_url}/dashboard/webhooks/{webhook_id}",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
