"""
semantic_scholar.py — Semantic Scholar Graph API client.

Covers ~200M papers. Free, no API key required (rate limit: ~100
req/5min unaffiliated). Per-paper data: title, authors, venue, year,
citation_count, influential_citation_count, open_access, abstract,
DOI, topics, citing / cited papers.

Why this matters for BASIS: the v1 corpus relied on hand-assigned
tiers. Semantic Scholar's citation_count + influential_citation_count
directly feed SCHEMA-019's `high_citation` signal that bumps T1 alpha
from 0.75 to 0.95. Without this client, every academic source is stuck
at the lower end of its tier band.

Docs: https://api.semanticscholar.org/
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

API_BASE = "https://api.semanticscholar.org/graph/v1"
FIELDS = (
    "title,authors,venue,year,publicationDate,citationCount,"
    "influentialCitationCount,openAccessPdf,isOpenAccess,abstract,"
    "externalIds"
)

_last_call: float = 0.0
_MIN_INTERVAL = 3.0  # polite spacing, unaffiliated tier is ~100/5min


def _rate_limit() -> None:
    global _last_call
    gap = time.time() - _last_call
    if gap < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - gap)
    _last_call = time.time()


@dataclass
class SemanticScholarPaper:
    paper_id: str
    title: str
    authors: list[str]
    venue: str | None
    year: int | None
    publication_date: str | None
    citation_count: int | None
    influential_citation_count: int | None
    is_open_access: bool | None
    open_access_pdf: str | None
    abstract: str | None
    doi: str | None

    def to_documentary_fields(self) -> dict:
        """Return a dict mergeable into DocumentarySource constructor kwargs."""
        return {
            "title": self.title,
            "author": "; ".join(self.authors) if self.authors else None,
            "published_date": self.publication_date or (str(self.year) if self.year else None),
            "venue": self.venue,
            "doi": self.doi,
            "citation_count": self.citation_count,
            "influential_citation_count": self.influential_citation_count,
            "open_access": self.is_open_access,
        }


def enrich_by_doi(doi: str) -> SemanticScholarPaper | None:
    """Look up a paper by DOI. Returns None if not found."""
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "", 1)

    _rate_limit()
    try:
        resp = requests.get(
            f"{API_BASE}/paper/DOI:{doi}",
            params={"fields": FIELDS},
            timeout=15,
        )
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None
    return _from_json(resp.json())


def search_papers(query: str, limit: int = 5) -> list[SemanticScholarPaper]:
    """Full-text search. Returns up to `limit` matches, most-cited first."""
    _rate_limit()
    try:
        resp = requests.get(
            f"{API_BASE}/paper/search",
            params={"query": query, "limit": limit, "fields": FIELDS},
            timeout=20,
        )
    except requests.RequestException:
        return []

    if resp.status_code != 200:
        return []
    data = resp.json().get("data") or []
    return [_from_json(p) for p in data if p]


def _from_json(data: dict) -> SemanticScholarPaper:
    external = data.get("externalIds") or {}
    authors_raw = data.get("authors") or []
    open_access = data.get("openAccessPdf") or {}
    return SemanticScholarPaper(
        paper_id=data.get("paperId", ""),
        title=data.get("title", ""),
        authors=[a.get("name", "") for a in authors_raw if a.get("name")],
        venue=data.get("venue"),
        year=data.get("year"),
        publication_date=data.get("publicationDate"),
        citation_count=data.get("citationCount"),
        influential_citation_count=data.get("influentialCitationCount"),
        is_open_access=data.get("isOpenAccess"),
        open_access_pdf=open_access.get("url") if isinstance(open_access, dict) else None,
        abstract=data.get("abstract"),
        doi=external.get("DOI"),
    )
