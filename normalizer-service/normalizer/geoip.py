"""GeoIP enrichment using MaxMind GeoLite2."""
from typing import Optional, Tuple

import geoip2.database


def init_geoip_reader(db_path: str) -> geoip2.database.Reader:
    """Initialize GeoIP database reader.

    Args:
        db_path: Path to the GeoLite2 City database file.

    Returns:
        GeoIP database reader.
    """
    return geoip2.database.Reader(db_path)


def enrich_geoip(
    reader: geoip2.database.Reader, ip: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Enrich IP address with country and city information.

    Args:
        reader: GeoIP database reader.
        ip: IP address to look up.

    Returns:
        Tuple of (country_code, city_name) or (None, None) if lookup fails.
    """
    if not ip:
        return None, None
    try:
        resp = reader.city(ip)
        return resp.country.iso_code, resp.city.name
    except Exception:
        return None, None
