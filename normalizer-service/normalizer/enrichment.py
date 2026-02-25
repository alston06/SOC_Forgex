"""Enrichment functions for activity events."""
import re
from typing import Optional
from urllib.parse import urlparse

import httpx

from .config import settings

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{12}$"
)


def normalize_path(resource: str) -> str:
    """Normalize a resource path by replacing numeric and UUID segments with {id}.

    Args:
        resource: The full resource URL/path.

    Returns:
        Normalized path without query string, with IDs replaced.
    """
    parsed = urlparse(resource)
    segments = [s for s in parsed.path.split("/") if s]

    norm_segments = []
    for seg in segments:
        if seg.isdigit():
            norm_segments.append("{id}")
        elif UUID_RE.match(seg):
            norm_segments.append("{id}")
        else:
            norm_segments.append(seg)

    return "/" + "/".join(norm_segments)


async def enrich_user_role(client: httpx.AsyncClient, actor: str) -> Optional[str]:
    """Enrich user role by querying the user service.

    Args:
        client: HTTP client for making requests.
        actor: The user/actor identifier.

    Returns:
        User role string or None if not found/error.
    """
    if not actor:
        return None

    url = f"{settings.user_service_base_url}/roles/{actor}"
    try:
        resp = await client.get(url, timeout=settings.user_service_timeout_s)
        if resp.status_code != 200:
            return None
        data = resp.json()
        return data.get("role")
    except Exception:
        return None
