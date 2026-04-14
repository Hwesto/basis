"""
testimony.py — ingester for TESTIMONY sources.

Stated positions: Hansard debates, select committee submissions, FOI
responses, ombudsman rulings, citizen challenge submissions. Tier
ceiling is T3 (never T1/T2) per SCHEMA-008.

Current scaffold:
    - Accepts metadata (actor, actor_type, context, verbatim_ref) and
      produces a schema-valid TestimonySource
    - Hansard API / TheyWorkForYou wrappers: TODO
    - FOI platform fetcher: TODO
    - Candidate POSITION node generation from testimony text: TODO
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError

from source_models import TestimonySource, TestimonyTier
from ingest.base import Adapter, IngestionResult, IngestStatus


class TestimonyAdapter:
    source_type = "TESTIMONY"

    def can_handle(self, url_or_id: str, metadata: dict | None = None) -> bool:
        meta = metadata or {}
        if meta.get("source_type") == "TESTIMONY":
            return True
        if meta.get("actor") or meta.get("verbatim_ref"):
            return True
        u = (url_or_id or "").lower()
        return any(
            p in u for p in [
                "hansard.parliament.uk", "theyworkforyou.com",
                "whatdotheyknow.com", "parliamentlive.tv",
            ]
        )

    def ingest(
        self,
        url_or_id: str,
        metadata: dict | None = None,
    ) -> IngestionResult:
        meta = metadata or {}
        run_id = meta.get("run_id") or f"ingest_test_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Required fields
        actor = meta.get("actor")
        actor_type = meta.get("actor_type")
        context = meta.get("context")
        testimony_date = meta.get("date") or date.today().isoformat()
        tier = meta.get("tier", "T4")

        if not actor or not actor_type or not context:
            return IngestionResult(
                status=IngestStatus.PARSE_FAILED,
                errors=[
                    "TESTIMONY ingestion requires actor, actor_type, and "
                    "context in metadata. Automated Hansard/FOI extraction "
                    "is not yet wired (TODO in testimony.py)."
                ],
                run_id=run_id,
            )

        try:
            parsed_date = (
                testimony_date if isinstance(testimony_date, date)
                else date.fromisoformat(testimony_date)
            )
            src = TestimonySource(
                source_id=meta.get("source_id") or f"SRC-TEST-{_short(url_or_id)}",
                actor=actor,
                actor_type=actor_type,
                date=parsed_date,
                context=context,
                verbatim_ref=meta.get("verbatim_ref"),
                tier=TestimonyTier(tier),
                domain=meta.get("domain"),
            )
        except (ValidationError, ValueError) as exc:
            return IngestionResult(
                status=IngestStatus.VALIDATION_FAILED,
                errors=[f"TestimonySource validation failed: {exc}"],
                run_id=run_id,
            )

        return IngestionResult(
            status=IngestStatus.OK,
            source=src,
            notes=[
                f"Testimony by {actor} ({actor_type}) at tier {tier}",
                "POSITION node extraction deferred to curator-led Phase 2 "
                "re-ingestion.",
            ],
            run_id=run_id,
        )


def _short(identifier: str) -> str:
    import hashlib
    return hashlib.sha1(identifier.encode()).hexdigest()[:8].upper()
