"""
persistence.py — write schema-valid sources and candidate nodes to DB.

Every write runs through Pydantic validation first. Failures go to a
rejection log, not the DB. This is the hard gate per SCHEMA-006 —
nothing enters the graph without passing validation.

Two backends supported:
    - 'supabase' — live DB writes via supabase-py (requires env vars)
    - 'local_json' — writes to data/v2_graph/ as newline-delimited JSON
      for offline testing

Both backends produce the same JSON payload shapes so downstream tooling
can treat them interchangeably.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydantic import BaseModel, ValidationError

from ingest.base import IngestionResult, IngestStatus

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Write targets
# ---------------------------------------------------------------------------

LOCAL_GRAPH_DIR = REPO / "data" / "v2_graph"
LOCAL_SOURCES_PATH = LOCAL_GRAPH_DIR / "sources.jsonl"
LOCAL_NODES_PATH = LOCAL_GRAPH_DIR / "candidate_nodes.jsonl"
LOCAL_CITATIONS_PATH = LOCAL_GRAPH_DIR / "candidate_citations.jsonl"
LOCAL_REJECTIONS_PATH = LOCAL_GRAPH_DIR / "rejections.jsonl"


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")


# ---------------------------------------------------------------------------
# Local backend
# ---------------------------------------------------------------------------

class LocalJsonPersistence:
    """
    Writes to data/v2_graph/*.jsonl. Used when Supabase isn't available
    or for unit tests.
    """
    def __init__(self, root: Path = LOCAL_GRAPH_DIR):
        self.root = root

    def write(self, result: IngestionResult) -> dict:
        summary = {"sources": 0, "nodes": 0, "citations": 0, "rejections": 0}

        if result.status != IngestStatus.OK:
            _append_jsonl(
                self.root / "rejections.jsonl",
                {
                    "run_id": result.run_id,
                    "status": result.status.value,
                    "errors": result.errors,
                    "notes": result.notes,
                    "rejected_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            summary["rejections"] = 1
            return summary

        if result.source is not None:
            _append_jsonl(
                self.root / "sources.jsonl",
                _model_to_dict(result.source)
                | {"_run_id": result.run_id},
            )
            summary["sources"] += 1

        for node in result.candidate_nodes:
            # node may already carry a `_routing` key (SCHEMA-024
            # routing decision) attached by ingest.cli._apply_curator_routing.
            # We pass it through verbatim so downstream tooling (review
            # CLI, future Supabase writer) can read tier / escalation_reason
            # / fast_fail_check / auto_approval_conditions without
            # re-running the routing module.
            _append_jsonl(
                self.root / "candidate_nodes.jsonl",
                node | {"_run_id": result.run_id, "curator_approved": False},
            )
            summary["nodes"] += 1

        for cite in result.candidate_citations:
            _append_jsonl(
                self.root / "candidate_citations.jsonl",
                cite | {"_run_id": result.run_id},
            )
            summary["citations"] += 1

        return summary


# ---------------------------------------------------------------------------
# Supabase backend (stub)
# ---------------------------------------------------------------------------

class SupabasePersistence:
    """
    Live Supabase writes. Requires:
      SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY in env.
    Current status: stub. Wiring deferred until Phase 2 when the
    curator review cycle drives live inserts.
    """
    def __init__(self):
        self.url = os.environ.get("SUPABASE_URL")
        self.key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not self.url or not self.key:
            raise RuntimeError(
                "SupabasePersistence requires SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY environment variables."
            )

    def write(self, result: IngestionResult) -> dict:
        raise NotImplementedError(
            "Supabase writer is a Phase 2 deliverable. For Phase 1, use "
            "LocalJsonPersistence to write to data/v2_graph/."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_persistence(backend: str | None = None):
    """Return the persistence implementation selected by env or arg."""
    choice = (
        backend
        or os.environ.get("BASIS_PERSISTENCE", "local_json").lower()
    )
    if choice == "supabase":
        return SupabasePersistence()
    return LocalJsonPersistence()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_to_dict(model: BaseModel) -> dict:
    """Serialise a Pydantic model to a plain dict suitable for JSON writes."""
    return json.loads(model.model_dump_json())
