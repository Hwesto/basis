"""
cli.py — ingestion orchestrator.

Routes a single URL/ID to the right adapter, persists the result,
and reports.

CLI:
    python -m ingest <url-or-id> [--dry-run] [--backend local_json|supabase]
    python -m ingest backlog [--path data/v1_ingestion_backlog.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.base import IngestionResult, IngestStatus
from ingest.documentary import DocumentaryAdapter
from ingest.structured_data import StructuredDataAdapter
from ingest.structural import StructuralAdapter
from ingest.testimony import TestimonyAdapter
from ingest.derived import DerivedAdapter
from ingest.persistence import get_persistence

REPO = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# Adapter registry (first match wins)
# ---------------------------------------------------------------------------

ADAPTERS = [
    DerivedAdapter(),          # metadata-driven, no URL
    StructuredDataAdapter(),   # API endpoints, specific provider matches
    StructuralAdapter(),       # registry-flagged or legislation URLs
    TestimonyAdapter(),        # Hansard / FOI / declared testimony
    DocumentaryAdapter(),      # default fallback for URLs
]


def route(url_or_id: str, metadata: dict | None = None):
    for adapter in ADAPTERS:
        if adapter.can_handle(url_or_id, metadata):
            return adapter
    return DocumentaryAdapter()  # safety net


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def ingest_one(
    url_or_id: str,
    metadata: dict | None = None,
    dry_run: bool = False,
    backend: str | None = None,
) -> IngestionResult:
    """
    Ingest a single input. Returns the adapter's IngestionResult.

    If dry_run=True: adapter runs, result is returned, but not persisted.
    If dry_run=False: result is passed to the selected persistence backend.
    """
    adapter = route(url_or_id, metadata)
    result = adapter.ingest(url_or_id, metadata)

    if dry_run:
        return result

    persistence = get_persistence(backend)
    summary = persistence.write(result)
    result.notes.append(f"Persistence summary: {summary}")
    return result


def ingest_backlog(
    path: Path = REPO / "data" / "v1_ingestion_backlog.json",
    dry_run: bool = False,
    backend: str | None = None,
    limit: int | None = None,
) -> dict:
    """
    Batch-ingest a backlog JSON file.

    Expected file shape:
        [
          {"source_id": "SRC-NHS-001", "url": "...", "title": "...",
           "metadata": {...}},
          ...
        ]

    Returns summary counts by status.
    """
    if not path.exists():
        raise FileNotFoundError(f"Backlog file not found: {path}")

    entries = json.loads(path.read_text())
    if limit is not None:
        entries = entries[:limit]

    counts: dict[str, int] = {}
    for entry in entries:
        url_or_id = entry.get("url") or entry.get("id") or ""
        meta = entry.get("metadata") or {}
        # Propagate top-level fields into metadata so the adapter sees them
        for k in ("source_id", "title", "author", "domain", "published_date",
                  "default_tier", "default_tier_justification"):
            if entry.get(k) is not None:
                meta.setdefault(k, entry[k])
        result = ingest_one(url_or_id, metadata=meta, dry_run=dry_run, backend=backend)
        counts[result.status.value] = counts.get(result.status.value, 0) + 1

    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(prog="ingest", description="BASIS ingestion CLI")
    parser.add_argument("target", help="URL, ID, or the literal 'backlog'")
    parser.add_argument("--dry-run", action="store_true",
                        help="Route and validate but do not persist")
    parser.add_argument("--backend", default=None,
                        choices=["local_json", "supabase"])
    parser.add_argument("--path", type=Path, default=None,
                        help="Path to backlog JSON (only with 'backlog')")
    parser.add_argument("--limit", type=int, default=None,
                        help="Process only first N backlog entries")
    parser.add_argument("--domain", default=None, help="Hint for adapter routing")

    args = parser.parse_args()

    if args.target == "backlog":
        path = args.path or REPO / "data" / "v1_ingestion_backlog.json"
        counts = ingest_backlog(
            path=path, dry_run=args.dry_run,
            backend=args.backend, limit=args.limit,
        )
        print(f"Backlog summary: {counts}")
        return

    metadata = {"domain": args.domain} if args.domain else {}
    result = ingest_one(
        args.target, metadata=metadata,
        dry_run=args.dry_run, backend=args.backend,
    )
    print(f"Status: {result.status.value}")
    if result.source is not None:
        print(f"Source: {result.source.source_id} ({result.source.source_type})")
    for n in result.notes:
        print(f"  note: {n}")
    for e in result.errors:
        print(f"  error: {e}")


if __name__ == "__main__":
    _main()
