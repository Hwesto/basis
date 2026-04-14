"""
ingest.enrichment — external APIs for metadata augmentation.

Wraps the academic-publishing ecosystem so DocumentarySource records
can be populated with authoritative metadata instead of ad-hoc guesses.

Clients:
    semantic_scholar — citation counts, venue, authors, abstract, open
                       access status, by DOI or title search. Free, no
                       key required.
    crossref         — DOI registry. Definitive metadata for anything
                       with a DOI (publisher, published date, volume,
                       issue, authors). Free, no key.
    openalex         — comprehensive academic graph; successor to
                       Microsoft Academic. Free, no key. Useful for
                       works without a DOI.
    unpaywall        — open access PDF locations by DOI. Free, requires
                       email as a courtesy header.
    gov_uk           — gov.uk content API (for .gov.uk pages).

None of these carry API keys. All have rate limits; we cache by
content_hash / DOI where possible.
"""

from ingest.enrichment.semantic_scholar import enrich_by_doi, search_papers
from ingest.enrichment.crossref import resolve_doi
from ingest.enrichment.openalex import enrich_by_title
from ingest.enrichment.gov_uk import fetch_gov_uk_content

__all__ = [
    "enrich_by_doi",
    "search_papers",
    "resolve_doi",
    "enrich_by_title",
    "fetch_gov_uk_content",
]
