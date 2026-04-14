"""
gov_uk.py — gov.uk Content API client.

gov.uk exposes every page at /api/content/<path>. Returns structured
metadata (title, description, publishing_organisation, first_published_at,
updated_at, content body). Handles policy papers, guidance, research
reports.

Docs: https://docs.publishing.service.gov.uk/repos/content-store/content-api.html

Why: most UK government evidence is published on gov.uk and the
structured content API gives us clean authorship (the publishing
organisation — DHSC, DfE, DWP, HMT, etc.) and first_published_at
without scraping HTML.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from urllib.parse import urlparse

import requests

_last_call: float = 0.0
_MIN_INTERVAL = 0.5


def _rate_limit() -> None:
    global _last_call
    gap = time.time() - _last_call
    if gap < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - gap)
    _last_call = time.time()


@dataclass
class GovUkContent:
    base_path: str
    title: str
    description: str | None
    publishing_organisation: str | None
    first_published_at: str | None
    updated_at: str | None
    document_type: str | None  # 'research', 'guidance', 'policy_paper', etc.
    body_html: str | None

    def to_documentary_fields(self) -> dict:
        """Return kwargs for a DocumentarySource constructor."""
        # gov.uk content is T2 by default (SCHEMA-009)
        return {
            "title": self.title,
            "author": self.publishing_organisation,
            "publisher": self.publishing_organisation or "gov.uk",
            "published_date": self.first_published_at,
            "default_tier": "T2",
            "default_tier_justification": (
                "gov.uk publishing_organisation " +
                (self.publishing_organisation or "(unknown)") +
                " — official government publication."
            ),
        }


def fetch_gov_uk_content(url: str) -> GovUkContent | None:
    """
    Fetch a gov.uk page via the Content API. Returns None if not a
    gov.uk URL or if the API says the path doesn't exist.
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower().lstrip("www.")
    if host not in {"gov.uk", "www.gov.uk"}:
        return None

    base_path = parsed.path or "/"
    api_url = f"https://www.gov.uk/api/content{base_path}"

    _rate_limit()
    try:
        resp = requests.get(api_url, timeout=15)
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None

    data = resp.json() or {}
    details = data.get("details") or {}
    body = details.get("body")
    if isinstance(body, list) and body:
        # multi-language body — take 'en' if present, else first
        body = next(
            (b.get("content") for b in body if b.get("locale") == "en"),
            body[0].get("content") if isinstance(body[0], dict) else None,
        )

    org = None
    orgs = (data.get("links") or {}).get("primary_publishing_organisation") or []
    if orgs:
        org = orgs[0].get("title")

    return GovUkContent(
        base_path=base_path,
        title=data.get("title", ""),
        description=data.get("description"),
        publishing_organisation=org,
        first_published_at=data.get("first_published_at"),
        updated_at=data.get("updated_at"),
        document_type=data.get("document_type"),
        body_html=body if isinstance(body, str) else None,
    )
