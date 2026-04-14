"""
data_sources.py — Live API clients for Phase 3 local data layer.

All open, no authentication required:
  - ONS Beta API: https://api.beta.ons.gov.uk/v1
  - Police.uk: https://data.police.uk/api/
  - Postcodes.io: https://api.postcodes.io/ (geography resolution)
  - CQC: https://api.cqc.org.uk/public/v1
  - Land Registry: http://landregistry.data.gov.uk/
  - ONS Geography: https://api.postcodes.io/ (uses ONS NSPL under the hood)

Rate limits:
  - ONS: 120 req/10s, 200 req/min
  - Police.uk: no published limit, be polite
  - Postcodes.io: 100 req/min free tier
  - CQC: no published limit
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

_last_request: dict[str, float] = {}

def _rate_limit(api: str, delay: float = 0.5):
    now = time.time()
    last = _last_request.get(api, 0)
    if now - last < delay:
        time.sleep(delay - (now - last))
    _last_request[api] = time.time()


# ---------------------------------------------------------------------------
# Postcodes.io — Geography resolution
# ---------------------------------------------------------------------------

POSTCODES_BASE = "https://api.postcodes.io"

@dataclass
class GeographyResult:
    """Postcode -> all geographic levels. Feeds geography_lookup table."""
    postcode: str
    lsoa_code: str | None = None
    lsoa_name: str | None = None
    ward_code: str | None = None
    ward_name: str | None = None
    la_code: str | None = None
    la_name: str | None = None
    constituency_code: str | None = None
    constituency_name: str | None = None
    country: str | None = None  # england, wales, scotland, ni
    latitude: float | None = None
    longitude: float | None = None

def resolve_postcode(postcode: str) -> GeographyResult | None:
    """Resolve a postcode to all geographic levels via postcodes.io."""
    _rate_limit("postcodes", 0.6)
    clean = postcode.replace(" ", "").upper()
    try:
        resp = requests.get(f"{POSTCODES_BASE}/postcodes/{clean}", timeout=10)
        if resp.status_code != 200:
            return None
        data = resp.json().get("result")
        if not data:
            return None

        country_raw = (data.get("country") or "").lower()
        country_map = {
            "england": "england",
            "wales": "wales",
            "scotland": "scotland",
            "northern ireland": "ni",
        }

        return GeographyResult(
            postcode=clean,
            lsoa_code=data.get("codes", {}).get("lsoa"),
            lsoa_name=data.get("lsoa"),
            ward_code=data.get("codes", {}).get("admin_ward"),
            ward_name=data.get("admin_ward"),
            la_code=data.get("codes", {}).get("admin_district"),
            la_name=data.get("admin_district"),
            constituency_code=data.get("codes", {}).get("parliamentary_constituency"),
            constituency_name=data.get("parliamentary_constituency"),
            country=country_map.get(country_raw),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
        )
    except requests.exceptions.RequestException:
        return None

def bulk_resolve_postcodes(postcodes: list[str]) -> list[GeographyResult]:
    """Bulk resolve up to 100 postcodes in one request."""
    _rate_limit("postcodes", 1.0)
    clean = [p.replace(" ", "").upper() for p in postcodes[:100]]
    try:
        resp = requests.post(
            f"{POSTCODES_BASE}/postcodes",
            json={"postcodes": clean},
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        results = []
        for item in resp.json().get("result", []):
            r = item.get("result")
            if not r:
                continue
            country_raw = (r.get("country") or "").lower()
            country_map = {"england": "england", "wales": "wales",
                           "scotland": "scotland", "northern ireland": "ni"}
            results.append(GeographyResult(
                postcode=item.get("query", ""),
                lsoa_code=r.get("codes", {}).get("lsoa"),
                lsoa_name=r.get("lsoa"),
                ward_code=r.get("codes", {}).get("admin_ward"),
                ward_name=r.get("admin_ward"),
                la_code=r.get("codes", {}).get("admin_district"),
                la_name=r.get("admin_district"),
                constituency_code=r.get("codes", {}).get("parliamentary_constituency"),
                constituency_name=r.get("parliamentary_constituency"),
                country=country_map.get(country_raw),
                latitude=r.get("latitude"),
                longitude=r.get("longitude"),
            ))
        return results
    except requests.exceptions.RequestException:
        return []


# ---------------------------------------------------------------------------
# Police.uk — Crime data
# ---------------------------------------------------------------------------

POLICE_BASE = "https://data.police.uk/api"

@dataclass
class CrimeRecord:
    category: str
    location_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    street_name: str | None = None
    month: str | None = None
    outcome_status: str | None = None

def get_crimes_at_location(
    lat: float, lng: float, date: str | None = None
) -> list[CrimeRecord]:
    """
    Street-level crimes within 1 mile of a point.
    date format: YYYY-MM (e.g. '2024-06'). None = latest month.
    """
    _rate_limit("police", 0.5)
    params: dict[str, Any] = {"lat": lat, "lng": lng}
    if date:
        params["date"] = date
    try:
        resp = requests.get(
            f"{POLICE_BASE}/crimes-street/all-crime",
            params=params, timeout=15,
        )
        if resp.status_code != 200:
            return []
        crimes = []
        for c in resp.json():
            loc = c.get("location", {})
            outcome = c.get("outcome_status")
            crimes.append(CrimeRecord(
                category=c.get("category", ""),
                location_type=loc.get("type"),
                latitude=float(loc["latitude"]) if loc.get("latitude") else None,
                longitude=float(loc["longitude"]) if loc.get("longitude") else None,
                street_name=loc.get("street", {}).get("name"),
                month=c.get("month"),
                outcome_status=outcome.get("category") if outcome else None,
            ))
        return crimes
    except requests.exceptions.RequestException:
        return []

def get_crime_categories() -> list[dict]:
    """List all crime categories."""
    _rate_limit("police", 0.5)
    try:
        resp = requests.get(f"{POLICE_BASE}/crime-categories", timeout=10)
        return resp.json() if resp.status_code == 200 else []
    except requests.exceptions.RequestException:
        return []

def get_crime_summary(lat: float, lng: float, date: str | None = None) -> dict[str, int]:
    """Crime counts by category for a location."""
    crimes = get_crimes_at_location(lat, lng, date)
    summary: dict[str, int] = {}
    for c in crimes:
        summary[c.category] = summary.get(c.category, 0) + 1
    return summary


# ---------------------------------------------------------------------------
# ONS Beta API — Datasets
# ---------------------------------------------------------------------------

ONS_BASE = "https://api.beta.ons.gov.uk/v1"

def ons_list_datasets() -> list[dict]:
    """List all available ONS datasets."""
    _rate_limit("ons", 0.5)
    try:
        resp = requests.get(f"{ONS_BASE}/datasets", timeout=15)
        if resp.status_code != 200:
            return []
        return resp.json().get("items", [])
    except requests.exceptions.RequestException:
        return []

def ons_get_dataset(dataset_id: str) -> dict | None:
    """Get metadata for a specific ONS dataset."""
    _rate_limit("ons", 0.5)
    try:
        resp = requests.get(f"{ONS_BASE}/datasets/{dataset_id}", timeout=15)
        return resp.json() if resp.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None

def ons_get_latest_version(dataset_id: str) -> dict | None:
    """Get the latest version of a dataset (for download URL or observations)."""
    _rate_limit("ons", 0.5)
    try:
        # Get editions
        resp = requests.get(f"{ONS_BASE}/datasets/{dataset_id}/editions", timeout=15)
        if resp.status_code != 200:
            return None
        editions = resp.json().get("items", [])
        if not editions:
            return None

        edition = editions[0]
        edition_name = edition.get("edition", "time-series")

        # Get latest version
        links = edition.get("links", {})
        latest_url = links.get("latest_version", {}).get("href")
        if latest_url:
            _rate_limit("ons", 0.5)
            resp2 = requests.get(latest_url, timeout=15)
            if resp2.status_code == 200:
                return resp2.json()

        return None
    except requests.exceptions.RequestException:
        return None

def ons_get_observations(
    dataset_id: str,
    edition: str = "time-series",
    version: str = "1",
    dimensions: dict[str, str] | None = None,
) -> list[dict]:
    """
    Query observations from an ONS dataset.
    dimensions: dict of dimension_name -> option_value (use '*' for wildcard).
    """
    _rate_limit("ons", 0.5)
    url = f"{ONS_BASE}/datasets/{dataset_id}/editions/{edition}/versions/{version}/observations"
    params = dimensions or {}
    try:
        resp = requests.get(url, params=params, timeout=20)
        if resp.status_code != 200:
            return []
        return resp.json().get("observations", [])
    except requests.exceptions.RequestException:
        return []

def ons_get_timeseries(cdid: str, dataset_id: str = "") -> dict | None:
    """
    Get a time series by CDID (series identifier).
    Uses the older ons.gov.uk timeseries API.
    """
    _rate_limit("ons", 0.5)
    base = "https://api.ons.gov.uk"
    url = f"{base}/timeseries/{cdid.lower()}"
    if dataset_id:
        url += f"/dataset/{dataset_id.lower()}"
    url += "/data"
    try:
        resp = requests.get(url, timeout=15)
        return resp.json() if resp.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None


# ---------------------------------------------------------------------------
# CQC — Care Quality Commission ratings
# ---------------------------------------------------------------------------

CQC_BASE = "https://api.cqc.org.uk/public/v1"

def cqc_search_locations(
    la_name: str | None = None,
    postcode: str | None = None,
    service_type: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> dict:
    """Search CQC locations (care homes, hospitals, GP practices)."""
    _rate_limit("cqc", 0.5)
    params: dict[str, Any] = {"page": page, "perPage": per_page}
    if la_name:
        params["localAuthority"] = la_name
    if postcode:
        params["postcode"] = postcode
    if service_type:
        params["serviceType"] = service_type
    try:
        resp = requests.get(f"{CQC_BASE}/locations", params=params, timeout=15)
        return resp.json() if resp.status_code == 200 else {}
    except requests.exceptions.RequestException:
        return {}

def cqc_get_location(location_id: str) -> dict | None:
    """Get full details for a CQC location including ratings."""
    _rate_limit("cqc", 0.5)
    try:
        resp = requests.get(f"{CQC_BASE}/locations/{location_id}", timeout=15)
        return resp.json() if resp.status_code == 200 else None
    except requests.exceptions.RequestException:
        return None

def cqc_ratings_summary(la_name: str) -> dict[str, int]:
    """Get rating distribution for care homes in a local authority."""
    data = cqc_search_locations(la_name=la_name, per_page=200)
    locations = data.get("locations", [])
    ratings: dict[str, int] = {}
    for loc in locations:
        rating = loc.get("currentRatings", {}).get("overall", {}).get("rating", "Not rated")
        ratings[rating] = ratings.get(rating, 0) + 1
    return ratings


# ---------------------------------------------------------------------------
# Land Registry — Property prices
# ---------------------------------------------------------------------------

def land_registry_average_price(
    area: str, year: int | None = None
) -> list[dict]:
    """
    Query Land Registry SPARQL endpoint for average prices.
    area: local authority name or district.
    """
    _rate_limit("land_registry", 1.0)
    # Land Registry provides a SPARQL endpoint
    endpoint = "http://landregistry.data.gov.uk/landregistry/query"

    year_filter = f'FILTER(YEAR(?date) = {year})' if year else ""

    query = f"""
    PREFIX lrppi: <http://landregistry.data.gov.uk/def/ppi/>
    PREFIX lrcommon: <http://landregistry.data.gov.uk/def/common/>

    SELECT (AVG(?amount) AS ?avgPrice) (COUNT(?amount) AS ?txCount) ?date
    WHERE {{
        ?tx lrppi:pricePaid ?amount ;
            lrppi:transactionDate ?date ;
            lrppi:propertyAddress ?addr .
        ?addr lrcommon:district "{area}"^^<http://www.w3.org/2001/XMLSchema#string> .
        {year_filter}
    }}
    GROUP BY ?date
    ORDER BY DESC(?date)
    LIMIT 12
    """

    try:
        resp = requests.get(
            endpoint,
            params={"query": query, "output": "json"},
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        results = resp.json().get("results", {}).get("bindings", [])
        return [
            {
                "avg_price": float(r["avgPrice"]["value"]),
                "tx_count": int(r["txCount"]["value"]),
                "date": r["date"]["value"],
            }
            for r in results
        ]
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return []


# ---------------------------------------------------------------------------
# DWP Stat-Xplore (open data, no auth for headline stats)
# ---------------------------------------------------------------------------

STAT_XPLORE_BASE = "https://stat-xplore.dwp.gov.uk/webapi/rest/v1"

def statxplore_list_schemas() -> list[dict]:
    """List available Stat-Xplore schemas (requires API key for full access)."""
    # Note: Stat-Xplore provides some open data but full access needs a free API key
    # Register at: https://stat-xplore.dwp.gov.uk/
    _rate_limit("statxplore", 1.0)
    try:
        resp = requests.get(f"{STAT_XPLORE_BASE}/schema", timeout=15)
        return resp.json() if resp.status_code == 200 else []
    except requests.exceptions.RequestException:
        return []


# ---------------------------------------------------------------------------
# Convenience: fetch all metrics for a postcode
# ---------------------------------------------------------------------------

def fetch_local_data(postcode: str) -> dict:
    """
    Master function: resolve postcode and fetch all available local metrics.
    Returns a dict ready for area_metrics upsert.
    """
    geo = resolve_postcode(postcode)
    if not geo:
        return {"error": f"Could not resolve postcode: {postcode}"}

    result = {
        "postcode": postcode,
        "geography": {
            "la_name": geo.la_name,
            "la_code": geo.la_code,
            "ward_name": geo.ward_name,
            "constituency_name": geo.constituency_name,
            "country": geo.country,
            "latitude": geo.latitude,
            "longitude": geo.longitude,
        },
        "metrics": {},
    }

    # Crime data
    if geo.latitude and geo.longitude:
        crimes = get_crime_summary(geo.latitude, geo.longitude)
        total_crimes = sum(crimes.values())
        result["metrics"]["crime_total"] = {
            "value": total_crimes,
            "breakdown": crimes,
            "source": "police.uk",
            "provider_tier": "T2",
        }

    # CQC care home ratings
    if geo.la_name:
        ratings = cqc_ratings_summary(geo.la_name)
        if ratings:
            total = sum(ratings.values())
            good_plus = ratings.get("Good", 0) + ratings.get("Outstanding", 0)
            result["metrics"]["cqc_good_pct"] = {
                "value": round(100 * good_plus / total, 1) if total else None,
                "breakdown": ratings,
                "source": "cqc",
                "provider_tier": "T2",
            }

    return result
