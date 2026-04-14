"""
derived.py — ingester for DERIVED sources.

A DERIVED source is a computation over other nodes. Examples:
    - Fiscal gap aggregation across FACT/CLAIM/POLICY nodes
    - Monte Carlo confidence result on a node
    - Percentile ranks of AREA_METRIC observations within peer group
    - Sensitivity analysis outputs

No external fetch. No author. No tier — quality inherits from input nodes
via MC propagation.

The adapter takes a computation_id + algorithm_version + list of input
node ids and persists the DerivedSource. The computation itself runs
elsewhere (extraction.mc_engine, scripts/compute_confidence.py, etc.).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import ValidationError

from source_models import DerivedSource
from ingest.base import Adapter, IngestionResult, IngestStatus


class DerivedAdapter:
    source_type = "DERIVED"

    def can_handle(self, url_or_id: str, metadata: dict | None = None) -> bool:
        meta = metadata or {}
        if meta.get("source_type") == "DERIVED":
            return True
        if meta.get("computation_id"):
            return True
        return False

    def ingest(
        self,
        url_or_id: str,
        metadata: dict | None = None,
    ) -> IngestionResult:
        meta = metadata or {}
        run_id = meta.get("run_id") or f"ingest_d_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        computation_id = meta.get("computation_id") or url_or_id
        algorithm_version = meta.get("algorithm_version")
        input_node_ids = meta.get("input_node_ids") or []

        if not algorithm_version:
            return IngestionResult(
                status=IngestStatus.PARSE_FAILED,
                errors=["DERIVED ingestion requires algorithm_version."],
                run_id=run_id,
            )
        if not input_node_ids:
            return IngestionResult(
                status=IngestStatus.PARSE_FAILED,
                errors=[
                    "DERIVED ingestion requires input_node_ids (list of node "
                    "ids the computation depends on). Cannot be empty — this "
                    "is what ties provenance back through the graph."
                ],
                run_id=run_id,
            )

        try:
            src = DerivedSource(
                source_id=meta.get("source_id") or f"SRC-DER-{computation_id}",
                computation_id=computation_id,
                algorithm_version=algorithm_version,
                input_node_ids=input_node_ids,
                computed_at=datetime.now(timezone.utc),
                domain=meta.get("domain"),
            )
        except ValidationError as exc:
            return IngestionResult(
                status=IngestStatus.VALIDATION_FAILED,
                errors=[f"DerivedSource validation failed: {exc}"],
                run_id=run_id,
            )

        return IngestionResult(
            status=IngestStatus.OK,
            source=src,
            notes=[
                f"Derived source over {len(input_node_ids)} input node(s)",
                "No independent alpha — MC engine propagates from inputs.",
            ],
            run_id=run_id,
        )
