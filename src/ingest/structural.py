"""
structural.py — ingester for STRUCTURAL sources (SCHEMA-008 / SCHEMA-010).

Unifies Lex Graph + Companies House + ONS NSPL + Land Registry etc.
under a single StructuralSource + registry discriminator. Alpha per
registry per SCHEMA-010.

Current scaffold:
    - lex_graph: delegates to extraction.lex_client.get_provision
    - companies_house / ons_nspl / land_registry: TODO — registry-specific
      fetchers to be wired as each is needed. For now the adapter accepts
      metadata and produces a schema-valid source record without going
      over the wire.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError

from source_models import StructuralSource, RegistryEnum
from ingest.base import Adapter, IngestionResult, IngestStatus


class StructuralAdapter:
    source_type = "STRUCTURAL"

    def can_handle(self, url_or_id: str, metadata: dict | None = None) -> bool:
        meta = metadata or {}
        if meta.get("source_type") == "STRUCTURAL":
            return True
        if meta.get("registry"):
            return True
        u = (url_or_id or "").lower()
        if "legislation.gov.uk" in u or "lex.lab.i.ai.gov.uk" in u:
            return True
        return False

    def ingest(
        self,
        url_or_id: str,
        metadata: dict | None = None,
    ) -> IngestionResult:
        meta = metadata or {}
        run_id = meta.get("run_id") or f"ingest_st_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        registry = meta.get("registry") or self._guess_registry(url_or_id)
        if not registry:
            return IngestionResult(
                status=IngestStatus.PARSE_FAILED,
                errors=[
                    f"Could not determine registry from {url_or_id!r}. "
                    "Pass registry in metadata."
                ],
                run_id=run_id,
            )

        record_id = meta.get("record_id") or url_or_id
        try:
            reg_enum = RegistryEnum(registry)
        except ValueError:
            return IngestionResult(
                status=IngestStatus.VALIDATION_FAILED,
                errors=[
                    f"Unknown registry {registry!r}. Must be one of: "
                    f"{[e.value for e in RegistryEnum]}"
                ],
                run_id=run_id,
            )

        try:
            src = StructuralSource(
                source_id=meta.get("source_id") or f"SRC-ST-{registry.upper()}-{_short(record_id)}",
                registry=reg_enum,
                record_id=record_id,
                edge_type=meta.get("edge_type") if registry == "lex_graph" else None,
                related_record_id=meta.get("related_record_id"),
                recorded_date=meta.get("recorded_date"),
                domain=meta.get("domain"),
                jurisdiction=meta.get("jurisdiction"),
            )
        except ValidationError as exc:
            return IngestionResult(
                status=IngestStatus.VALIDATION_FAILED,
                errors=[f"StructuralSource validation failed: {exc}"],
                run_id=run_id,
            )

        notes = [
            f"Registry {registry} — alpha set by SCHEMA-010 lookup at MC time."
        ]

        if registry == "lex_graph":
            # TODO: delegate to extraction.lex_client to fetch the
            # provision, run commencement_gate, emit candidate legal
            # nodes. For scaffold we accept the identifier and defer
            # extraction to the existing pipeline.
            notes.append(
                "Lex Graph ingestion — further processing in "
                "extraction.pipeline.extract_single_provision."
            )
        else:
            notes.append(
                f"{registry} adapter is a scaffold — no over-the-wire "
                "fetch yet. Source is persisted with the identifier only."
            )

        return IngestionResult(
            status=IngestStatus.OK,
            source=src,
            notes=notes,
            run_id=run_id,
        )

    @staticmethod
    def _guess_registry(url: str) -> str | None:
        u = (url or "").lower()
        if "legislation.gov.uk" in u or "lex.lab.i.ai.gov.uk" in u:
            return "lex_graph"
        if "find-and-update.company-information" in u:
            return "companies_house"
        if "ons.gov.uk/methodology/geography" in u:
            return "ons_nspl"
        if "landregistry.data.gov.uk" in u:
            return "land_registry"
        return None


def _short(identifier: str) -> str:
    import hashlib
    return hashlib.sha1(identifier.encode()).hexdigest()[:8].upper()
