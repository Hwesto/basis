"""
crossref.py — CrossRef REST API client.

CrossRef is the DOI registrar. Every paper with a DOI has authoritative
metadata here: title, authors, publisher, published date, journal,
volume, issue, page range, funders. Free, no key required. Polite
User-Agent with an email gets you into a faster pool.

Docs: https://api.crossref.org/
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

API_BASE = "https://api.crossref.org"
USER_AGENT = "BASIS-ingestion/0.1 (mailto:admin@example.invalid)"

_last_call: float = 0.0
_MIN_INTERVAL = 1.0


def _rate_limit() -> None:
    global _last_call
    gap = time.time() - _last_call
    if gap < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - gap)
    _last_call = time.time()


@dataclass
class CrossRefRecord:
    doi: str
    title: str
    authors: list[str]
    publisher: str | None
    journal: str | None
    published_date: str | None
    type: str | None  # 'journal-article', 'book-chapter', etc.
    url: str | None

    def to_documentary_fields(self) -> dict:
        return {
            "title": self.title,
            "author": "; ".join(self.authors) if self.authors else None,
            "publisher": self.publisher or self.journal or "Unknown",
            "published_date": self.published_date,
            "doi": self.doi,
            "url": self.url,
            "venue": self.journal,
        }


def resolve_doi(doi: str) -> CrossRefRecord | None:
    """Look up a DOI. Returns None if not registered."""
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "", 1)

    _rate_limit()
    try:
        resp = requests.get(
            f"{API_BASE}/works/{doi}",
            headers={"User-Agent": USER_AGENT},
            timeout=15,
        )
    except requests.RequestException:
        return None

    if resp.status_code != 200:
        return None

    msg = (resp.json() or {}).get("message", {})
    return _from_message(msg)


def _from_message(msg: dict) -> CrossRefRecord:
    title_list = msg.get("title") or []
    title = title_list[0] if title_list else ""

    authors_raw = msg.get("author") or []
    authors = [
        " ".join(filter(None, [a.get("given"), a.get("family")])).strip()
        for a in authors_raw
    ]

    issued = msg.get("issued") or {}
    date_parts = issued.get("date-parts", [[]])[0]
    published = "-".join(str(p).zfill(2) for p in date_parts) if date_parts else None

    return CrossRefRecord(
        doi=msg.get("DOI", ""),
        title=title,
        authors=authors,
        publisher=msg.get("publisher"),
        journal=(msg.get("container-title") or [None])[0],
        published_date=published,
        type=msg.get("type"),
        url=msg.get("URL"),
    )
