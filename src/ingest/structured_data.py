"""
structured_data.py — ingester for STRUCTURED_DATA sources.

Wraps the existing adapters in extraction/data_sources.py (ONS, Police.uk,
Postcodes.io, CQC, Land Registry, Stat-Xplore) and produces a
StructuredDataSource plus candidate AREA_METRIC node(s).

Routing: input is an (provider, dataset_id[, dimensions]) triple or a
recognised structured-data URL.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError

from source_models import StructuredDataSource, ProviderTier, get_provider_tier
from ingest.base import Adapter, IngestionResult, IngestStatus


class StructuredDataAdapter:
    source_type = "STRUCTURED_DATA"

    def can_handle(self, url_or_id: str, metadata: dict | None = None) -> bool:
        meta = metadata or {}
        if meta.get("source_type") == "STRUCTURED_DATA":
            return True
        if meta.get("provider") in [
            "ONS", "NHS Digital", "DWP Stat-Xplore", "Police.uk",
            "Land Registry", "CQC",
        ]:
            return True
        u = (url_or_id or "").lower()
        return any(
            api in u
            for api in [
                "api.beta.ons.gov.uk", "ons.gov.uk/api",
                "data.police.uk/api", "digital.nhs.uk",
                "stat-xplore.dwp.gov.uk",
            ]
        )

    def ingest(
        self,
        url_or_id: str,
        metadata: dict | None = None,
    ) -> IngestionResult:
        meta = metadata or {}
        run_id = meta.get("run_id") or f"ingest_sd_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        provider = meta.get("provider") or self._guess_provider(url_or_id)
        dataset_id = meta.get("dataset_id")
        if not provider:
            return IngestionResult(
                status=IngestStatus.PARSE_FAILED,
                errors=[
                    f"Could not determine provider from {url_or_id!r}. "
                    "Pass provider in metadata."
                ],
                run_id=run_id,
            )
        if not dataset_id:
            return IngestionResult(
                status=IngestStatus.PARSE_FAILED,
                errors=[
                    f"dataset_id required for STRUCTURED_DATA ingestion ({provider}). "
                    "Pass dataset_id in metadata."
                ],
                run_id=run_id,
            )

        provider_tier = get_provider_tier(provider)

        try:
            src = StructuredDataSource(
                source_id=meta.get("source_id") or f"SRC-SD-{provider.replace(' ', '_').upper()}-{dataset_id}",
                provider=provider,
                dataset_id=dataset_id,
                metric_id=meta.get("metric_id"),
                period_start=meta.get("period_start"),
                period_end=meta.get("period_end"),
                methodology_url=meta.get("methodology_url"),
                provider_tier=ProviderTier(provider_tier),
                api_endpoint=url_or_id if url_or_id.startswith("http") else None,
                last_refreshed=datetime.now(timezone.utc),
                domain=meta.get("domain"),
            )
        except ValidationError as exc:
            return IngestionResult(
                status=IngestStatus.VALIDATION_FAILED,
                errors=[f"StructuredDataSource validation failed: {exc}"],
                run_id=run_id,
            )

        # TODO: actually fetch observations and construct candidate
        # AREA_METRIC nodes via extraction.data_sources.ons_get_observations
        # / get_crimes_at_location / cqc_ratings_summary / etc.
        # Deferred: per-provider observation-to-node mapping is a Phase 3
        # deliverable (src/ingest/structured_data.py is the landing place).

        return IngestionResult(
            status=IngestStatus.OK,
            source=src,
            notes=[
                f"Provider {provider} mapped to tier {provider_tier} "
                "(SCHEMA-010 whitelist)",
                "AREA_METRIC node generation deferred to Phase 3 wiring.",
            ],
            run_id=run_id,
        )

    @staticmethod
    def _guess_provider(url: str) -> str | None:
        host = (urlparse(url).hostname or "").lower()
        if "ons.gov.uk" in host:
            return "ONS"
        if "police.uk" in host:
            return "Police.uk"
        if "digital.nhs.uk" in host:
            return "NHS Digital"
        if "stat-xplore" in host:
            return "DWP Stat-Xplore"
        if "landregistry" in host:
            return "Land Registry"
        if "cqc.org.uk" in host:
            return "CQC"
        return None
