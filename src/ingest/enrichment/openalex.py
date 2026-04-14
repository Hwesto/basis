"""
openalex.py — OpenAlex API client.

OpenAlex is the successor to Microsoft Academic Graph: 250M+ works,
90M+ authors, institutions, venues. Free, no key required. The
'polite pool' requires an email in headers and gives faster responses.

Why use both OpenAlex and Semantic Scholar:
    - Semantic Scholar has better citation-count signal for recent CS
      / biomedical papers
    - OpenAlex has better coverage for social sciences, UK-specific
      journals, and older material
    - OpenAlex includes institutional affiliations (useful for tier
      decisions about think tanks)

For BASIS: use OpenAlex as a secondary lookup when a work isn't in
Semantic Scholar or when we need institutional context.

Docs: https://docs.openalex.org/
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

API_BASE = "https://api.openalex.org"
POLITE_EMAIL = "admin@example.invalid"  # replace with real mailto on deploy

_last_call: float = 0.0
_MIN_INTERVAL = 1.0


def _rate_limit() -> None:
    global _last_call
    gap = time.time() - _last_call
    if gap < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - gap)
    _last_call = time.time()


@dataclass
class OpenAlexWork:
    id: str  # OpenAlex work URI
    doi: str | None
    title: str
    authors: list[str]
    institutions: list[str]
    venue: str | None
    publisher: str | None
    publication_date: str | None
    cited_by_count: int | None
    is_open_access: bool | None
    open_access_pdf: str | None
    abstract: str | None

    def to_documentary_fields(self) -> dict:
        return {
            "title": self.title,
            "author": "; ".join(self.authors) if self.authors else None,
            "publisher": self.publisher or self.venue or "Unknown",
            "published_date": self.publication_date,
            "doi": self.doi,
            "venue": self.venue,
            "citation_count": self.cited_by_count,
            "open_access": self.is_open_access,
        }


def enrich_by_title(title: str, author_hint: str | None = None) -> OpenAlexWork | None:
    """Search OpenAlex by title. Optionally filter by first-author surname."""
    _rate_limit()

    params: dict[str, Any] = {"search": title, "per_page": 1,
                              "mailto": POLITE_EMAIL}
    if author_hint:
        params["filter"] = f"author.display_name.search:{author_hint}"

    try:
        resp = requests.get(f"{API_BASE}/works", params=params, timeout=20)
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    results = (resp.json() or {}).get("results") or []
    if not results:
        return None
    return _from_json(results[0])


def enrich_by_doi(doi: str) -> OpenAlexWork | None:
    """Look up an OpenAlex work by DOI."""
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "", 1)

    _rate_limit()
    try:
        resp = requests.get(
            f"{API_BASE}/works/doi:{doi}",
            params={"mailto": POLITE_EMAIL},
            timeout=15,
        )
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None
    return _from_json(resp.json())


def _from_json(data: dict) -> OpenAlexWork:
    authors_raw = data.get("authorships") or []
    authors = [
        (a.get("author") or {}).get("display_name", "")
        for a in authors_raw
    ]
    institutions = [
        inst.get("display_name", "")
        for a in authors_raw
        for inst in (a.get("institutions") or [])
        if inst.get("display_name")
    ]

    venue_raw = data.get("primary_location") or {}
    source = venue_raw.get("source") or {}
    venue_name = source.get("display_name")
    publisher = source.get("host_organization_name")

    oa = data.get("open_access") or {}
    pdf_url = oa.get("oa_url")

    return OpenAlexWork(
        id=data.get("id", ""),
        doi=(data.get("doi") or "").replace("https://doi.org/", "") or None,
        title=data.get("title", ""),
        authors=[a for a in authors if a],
        institutions=list(dict.fromkeys(i for i in institutions if i)),  # dedupe
        venue=venue_name,
        publisher=publisher,
        publication_date=data.get("publication_date"),
        cited_by_count=data.get("cited_by_count"),
        is_open_access=oa.get("is_oa"),
        open_access_pdf=pdf_url,
        abstract=_reconstruct_abstract(data.get("abstract_inverted_index")),
    )


def _reconstruct_abstract(inv_index: dict | None) -> str | None:
    """OpenAlex stores abstracts as inverted indexes; flatten back to text."""
    if not inv_index:
        return None
    positions: list[tuple[int, str]] = []
    for word, indices in inv_index.items():
        for idx in indices:
            positions.append((idx, word))
    positions.sort()
    return " ".join(w for _, w in positions)
