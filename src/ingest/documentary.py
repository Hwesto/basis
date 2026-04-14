"""
documentary.py — ingester for DOCUMENTARY sources.

Covers: academic papers (DOI-based enrichment), gov.uk reports, IFS /
NAO / OBR reports, think-tank publications, manifestos.

Produces a DocumentarySource + candidate FACT/CLAIM nodes via LLM
extraction.

Enrichment order (cheap-to-expensive):
    1. If DOI present: CrossRef → authoritative publisher/authors/journal
    2. Also Semantic Scholar by DOI → citation_count +
       influential_citation_count (feeds SCHEMA-019 high_citation signal)
    3. If gov.uk host: gov.uk Content API → publishing_organisation,
       first_published_at, tier T2
    4. Otherwise: URL heuristic tier + <title> scrape

Current scaffold status:
    - URL fetch: implemented (HTML/plain text)
    - PDF extraction: TODO (pdfplumber — deferred to Phase 2)
    - Semantic Scholar / CrossRef / gov.uk enrichment: implemented
    - OpenAlex fallback: available via ingest.enrichment.openalex
    - LLM extraction: deferred to curator-led Phase 2 pass
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from pydantic import ValidationError

from source_models import DocumentarySource, DocumentaryTier
from ingest.base import Adapter, IngestionResult, IngestStatus
from ingest.enrichment import (
    enrich_by_doi as ss_enrich_by_doi,
    resolve_doi as crossref_resolve_doi,
    fetch_gov_uk_content,
)


# ---------------------------------------------------------------------------
# Tier heuristic (SCHEMA-009 default_tier from publisher signal)
# ---------------------------------------------------------------------------

PUBLISHER_TIER_HINT: dict[str, str] = {
    # T1 — peer-reviewed academic / authoritative govt stats
    "ons.gov.uk":       "T1",
    "www.ons.gov.uk":   "T1",
    "jstor.org":        "T1",
    "nature.com":       "T1",
    "sciencedirect.com":"T1",
    "springer.com":     "T1",
    "academic.oup.com": "T1",
    # T2 — official government publications
    "gov.uk":                  "T2",
    "www.gov.uk":              "T2",
    "parliament.uk":           "T2",
    "data.gov.uk":             "T2",
    # T3 — institutional research bodies
    "ifs.org.uk":              "T3",
    "obr.uk":                  "T3",
    "nao.org.uk":              "T3",
    "resolutionfoundation.org":"T3",
    "niesr.ac.uk":             "T3",
    "kingsfund.org.uk":        "T3",
    "health.org.uk":           "T3",
    "jrf.org.uk":              "T3",
    # T4 — think tanks / policy institutes
    "iea.org.uk":                 "T4",
    "smf.co.uk":                  "T4",
    "policyexchange.org.uk":      "T4",
    "newstatesman.com":           "T4",
    "centreforsocialjustice.org.uk":"T4",
    # T5 — political (party sites)
    "labour.org.uk":       "T5",
    "conservatives.com":   "T5",
    "libdems.org.uk":      "T5",
    "greenparty.org.uk":   "T5",
    "reformparty.uk":      "T5",
}


def suggest_tier_from_url(url: str) -> tuple[str, str]:
    """Return (tier, justification) from domain. Default T4."""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        host = ""
    host = host.lower().lstrip("www.")

    # exact match
    if host in PUBLISHER_TIER_HINT:
        tier = PUBLISHER_TIER_HINT[host]
        return tier, f"Publisher {host} tier-mapped to {tier} by SCHEMA-009 whitelist."

    # suffix match on common groups
    if host.endswith(".ac.uk"):
        return "T1", "UK academic institution (.ac.uk)."
    if host.endswith(".gov.uk"):
        return "T2", "UK government publication (.gov.uk)."
    if host.endswith(".org.uk"):
        return "T4", "UK third sector / policy institute (.org.uk)."

    return "T4", f"Unknown publisher {host or '(no host)'}; defaulting to T4."


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class DocumentaryAdapter:
    source_type = "DOCUMENTARY"

    def can_handle(self, url_or_id: str, metadata: dict | None = None) -> bool:
        meta = metadata or {}
        if meta.get("source_type") == "DOCUMENTARY":
            return True
        if url_or_id.startswith("http"):
            # Most URLs are documentary unless specifically routed elsewhere
            u = url_or_id.lower()
            if any(x in u for x in ["ons.gov.uk/api", "api.beta.ons.gov.uk",
                                    "data.police.uk/api", "digital.nhs.uk",
                                    "stat-xplore"]):
                return False  # structured_data
            if "lex" in u and ("provision" in u or "legislation" in u):
                return False  # structural
            if "hansard" in u or "theyworkforyou" in u:
                return False  # testimony
            return True
        return False

    def ingest(
        self,
        url_or_id: str,
        metadata: dict | None = None,
    ) -> IngestionResult:
        meta = metadata or {}
        run_id = meta.get("run_id") or f"ingest_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # 1. Fetch content (HTML / plain text only in this scaffold)
        #    PDF handling: TODO — route .pdf URLs through pdfplumber.
        is_pdf = url_or_id.lower().endswith(".pdf")
        if is_pdf:
            return IngestionResult(
                status=IngestStatus.FETCH_FAILED,
                errors=[
                    f"PDF extraction not yet implemented in documentary adapter "
                    f"({url_or_id}). TODO: wire up pdfplumber."
                ],
                notes=["This source should be added to the manual-fetch backlog."],
                run_id=run_id,
            )

        try:
            resp = requests.get(url_or_id, timeout=20,
                                headers={"User-Agent": "BASIS-ingestion/0.1"})
            if resp.status_code != 200:
                return IngestionResult(
                    status=IngestStatus.FETCH_FAILED,
                    errors=[f"HTTP {resp.status_code} fetching {url_or_id}"],
                    run_id=run_id,
                )
            content = resp.text
        except requests.RequestException as exc:
            return IngestionResult(
                status=IngestStatus.FETCH_FAILED,
                errors=[f"Request failed: {exc}"],
                run_id=run_id,
            )

        content_hash = hashlib.sha256(content.encode()).hexdigest()

        # 2. Enrich from external registries (DOI, gov.uk, etc.)
        enriched: dict = {}
        enrichment_notes: list[str] = []

        doi = meta.get("doi")
        if doi:
            # CrossRef is authoritative for publisher/authors/journal
            cr = crossref_resolve_doi(doi)
            if cr:
                enriched.update(cr.to_documentary_fields())
                enrichment_notes.append(f"CrossRef: {cr.journal or cr.publisher}")

            # Semantic Scholar gives citation counts
            ss = ss_enrich_by_doi(doi)
            if ss:
                enriched.update(ss.to_documentary_fields())
                enrichment_notes.append(
                    f"Semantic Scholar: citation_count={ss.citation_count}, "
                    f"influential={ss.influential_citation_count}"
                )

        # gov.uk Content API — wins for gov.uk URLs
        if "gov.uk" in (urlparse(url_or_id).hostname or ""):
            gov = fetch_gov_uk_content(url_or_id)
            if gov:
                enriched.update(gov.to_documentary_fields())
                enrichment_notes.append(
                    f"gov.uk: {gov.publishing_organisation} / {gov.document_type}"
                )

        # 3. Determine tier — caller > enrichment > URL heuristic
        if meta.get("default_tier"):
            tier = meta["default_tier"]
            tier_justification = meta.get(
                "default_tier_justification",
                f"Tier set by caller to {tier}.",
            )
        elif enriched.get("default_tier"):
            tier = enriched["default_tier"]
            tier_justification = enriched.get(
                "default_tier_justification",
                "Tier set by enrichment.",
            )
        else:
            tier, tier_justification = suggest_tier_from_url(url_or_id)
            # Bump T1 papers with high citation counts: SCHEMA-019 signal
            if (tier == "T1" and enriched.get("citation_count") and
                    enriched.get("influential_citation_count") and
                    enriched["citation_count"] > 100 and
                    enriched["influential_citation_count"] > 5):
                tier_justification += (
                    f" High-citation signal (c={enriched['citation_count']}, "
                    f"influential={enriched['influential_citation_count']}) "
                    "triggers SCHEMA-019 alpha bump."
                )

        # 4. Build source record — caller metadata wins, then enrichment,
        #    then URL fallbacks
        def pick(key: str, fallback=None):
            return meta.get(key) or enriched.get(key) or fallback

        try:
            src = DocumentarySource(
                source_id=meta.get("source_id") or self._derive_source_id(url_or_id),
                title=pick("title") or _extract_title(content) or url_or_id,
                author=pick("author"),
                publisher=pick("publisher") or (urlparse(url_or_id).hostname or "unknown"),
                published_date=pick("published_date") or date.today().isoformat(),
                url=url_or_id,
                doi=doi,
                default_tier=tier,
                default_tier_justification=tier_justification,
                full_text=content[:20000],  # cap for DB; full kept by content_hash
                content_hash=content_hash,
                fetched_at=datetime.now(timezone.utc),
                citation_count=enriched.get("citation_count"),
                influential_citation_count=enriched.get("influential_citation_count"),
                venue=enriched.get("venue"),
                open_access=enriched.get("open_access"),
                domain=meta.get("domain"),
            )
        except ValidationError as exc:
            return IngestionResult(
                status=IngestStatus.VALIDATION_FAILED,
                errors=[f"DocumentarySource validation failed: {exc}"],
                run_id=run_id,
            )

        # 5. Candidate node extraction — if Google AI key is present, run
        #    the skeleton's extract_evidence pipeline on the fetched text
        #    to produce candidate FACT/CLAIM/ASSUMPTION nodes.
        #    Per docs/basis-extraction-agent-spec.md this is a single-pass
        #    call — nodes + intra-domain edges come out together.
        candidate_nodes: list[dict] = []
        candidate_citations: list[dict] = []
        llm_note: str | None = None

        api_key = os.environ.get("GOOGLE_AI_API_KEY")
        extract_domain = meta.get("domain") or "economy"  # fallback for routing
        if api_key and not meta.get("skip_extraction"):
            try:
                from extraction.pipeline import extract_evidence
                extraction = extract_evidence(
                    text=content[:8000],
                    title=src.title,
                    domain=extract_domain,
                    tier=tier,
                    publisher=src.publisher,
                    api_key=api_key,
                )
                if extraction.get("status") == "extracted":
                    parsed = extraction.get("nodes")
                    if isinstance(parsed, dict):
                        parsed = [parsed]
                    if isinstance(parsed, list):
                        candidate_nodes = parsed
                        # One citation edge per candidate node back to
                        # this source. claim_tier_override left None so
                        # source.default_tier is used as the MC prior.
                        for i, node in enumerate(candidate_nodes):
                            node_id = node.get("id") or f"{src.source_id}-CAND-{i:03d}"
                            node.setdefault("id", node_id)
                            candidate_citations.append({
                                "source_id": src.source_id,
                                "node_id": node_id,
                                "citation_locator": None,
                                "claim_tier_override": None,
                                "claim_tier_justification": None,
                                "created_by": run_id,
                            })
                        llm_note = (
                            f"Gemma extraction: {len(candidate_nodes)} "
                            f"candidate node(s), {len(candidate_citations)} "
                            "citation edge(s)"
                        )
                    else:
                        llm_note = (
                            f"Gemma returned unexpected shape: {type(parsed)}"
                        )
                else:
                    llm_note = (
                        f"Gemma extraction error: "
                        f"{extraction.get('error', 'unknown')}"
                    )
            except Exception as exc:  # pragma: no cover — defensive
                llm_note = f"Gemma extraction skipped ({exc!r})"
        elif not api_key:
            llm_note = (
                "GOOGLE_AI_API_KEY not set — source persisted, "
                "candidate node extraction deferred"
            )
        else:
            llm_note = "skip_extraction=True in metadata; nodes not extracted"

        return IngestionResult(
            status=IngestStatus.OK,
            source=src,
            candidate_nodes=candidate_nodes,
            candidate_citations=candidate_citations,
            notes=[
                f"Fetched {len(content)} chars from {url_or_id}",
                f"Default tier {tier} — {tier_justification}",
                *enrichment_notes,
                llm_note,
            ],
            run_id=run_id,
        )

    @staticmethod
    def _derive_source_id(url: str) -> str:
        h = hashlib.sha1(url.encode()).hexdigest()[:8]
        return f"SRC-DOC-{h.upper()}"


def _extract_title(html: str) -> str | None:
    """Quick-and-dirty HTML <title> extractor. Avoids pulling a full HTML parser."""
    import re
    m = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        return m.group(1).strip()[:500]
    return None
