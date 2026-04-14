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

# SCHEMA-024 routing — alias to avoid collision with route() local
# function below which routes URL -> adapter.
from curator import RoutingContext, route as route_node
from curator.context import RoutingContext as _RoutingContext  # noqa: F401

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

    Pipeline:
      1. Adapter routing (DocumentaryAdapter / StructuredData / etc.)
      2. Source fetch + enrichment + (optional) LLM extraction
      3. SCHEMA-024 Tier-1 routing on each candidate node
      4. Persistence (unless dry_run)

    If dry_run=True: adapter + routing run, result is returned, but
    nothing is persisted.
    If dry_run=False: result is passed to the selected persistence
    backend; SCHEMA-024 routing decisions are attached to each
    candidate node before persistence.
    """
    adapter = route(url_or_id, metadata)
    result = adapter.ingest(url_or_id, metadata)

    # Apply SCHEMA-024 routing per candidate node. Always runs (even
    # in dry-run), so the operator sees the routing decisions even
    # without persisting.
    if result.source is not None and result.candidate_nodes:
        _apply_curator_routing(result)

    if dry_run:
        return result

    persistence = get_persistence(backend)
    summary = persistence.write(result)
    result.notes.append(f"Persistence summary: {summary}")
    return result


def _apply_curator_routing(result: IngestionResult) -> None:
    """SCHEMA-024 — annotate each candidate node with a RoutingDecision.

    Tags an in-place `_routing` key on every candidate node payload so
    the persistence layer can write the routing fields alongside the
    node itself.

    Counts for the calibration windows come from local jsonl persistence
    (data/v2_graph/candidate_nodes.jsonl). When Supabase MCP is wired,
    swap to a SELECT count(*) query — only the count source changes,
    not the routing module.
    """
    source_payload = (
        result.source.model_dump() if hasattr(result.source, "model_dump")
        else dict(result.source or {})
    )
    source_id = source_payload.get("source_id")

    # tier_counts is a per-result accumulator that run_agent.py reads.
    if not hasattr(result, "tier_counts"):
        result.tier_counts = {1: 0, 2: 0, 3: 0}  # type: ignore[attr-defined]

    for node in result.candidate_nodes:
        domain = node.get("domain") or source_payload.get("domain")
        ctx = _build_context(domain, source_id)
        decision = route_node(node, source_payload, ctx)
        node["_routing"] = decision.to_dict()
        result.tier_counts[int(decision.tier)] += 1  # type: ignore[attr-defined]

    result.notes.append(
        f"Routing summary: tier1={result.tier_counts.get(1, 0)} "
        f"tier2={result.tier_counts.get(2, 0)} "
        f"tier3={result.tier_counts.get(3, 0)}"
    )


def _build_context(domain: str | None, source_id: str | None) -> "_RoutingContext":
    """Compute a RoutingContext from local jsonl state.

    For Phase 1 we read data/v2_graph/candidate_nodes.jsonl. The file
    may not exist on a clean run — in that case all counts are 0
    (every node falls inside a calibration window, which is correct
    for a fresh start).
    """
    from ingest.persistence import LOCAL_NODES_PATH

    in_domain = 0
    in_source = 0
    if LOCAL_NODES_PATH.exists():
        with LOCAL_NODES_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if domain and row.get("domain") == domain:
                    in_domain += 1
                # The candidate node carries the source via citation_edges
                # in the persistence file. Approximate by checking whether
                # any citation in the row points at our source_id.
                if source_id:
                    cites = row.get("citations") or []
                    if any(c.get("source_id") == source_id for c in cites):
                        in_source += 1

    return RoutingContext(
        nodes_in_domain_so_far=in_domain,
        nodes_from_source_so_far=in_source,
    )


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

    Returns summary counts by status, plus aggregated tier_counts
    (SCHEMA-024) across all candidate nodes routed during the batch.
    """
    if not path.exists():
        raise FileNotFoundError(f"Backlog file not found: {path}")

    entries = json.loads(path.read_text())
    if limit is not None:
        entries = entries[:limit]

    counts: dict[str, int] = {}
    tier_counts: dict[int, int] = {1: 0, 2: 0, 3: 0}
    escalation_counts: dict[str, int] = {}

    for entry in entries:
        if entry.get("_meta"):
            continue
        url_or_id = entry.get("url") or entry.get("id") or ""
        meta = entry.get("metadata") or {}
        # Propagate top-level fields into metadata so the adapter sees them
        for k in ("source_id", "title", "author", "domain", "published_date",
                  "default_tier", "default_tier_justification"):
            if entry.get(k) is not None:
                meta.setdefault(k, entry[k])
        result = ingest_one(url_or_id, metadata=meta, dry_run=dry_run, backend=backend)
        counts[result.status.value] = counts.get(result.status.value, 0) + 1

        # Aggregate routing decisions across the batch (SCHEMA-024).
        per_result = getattr(result, "tier_counts", None) or {}
        for tier, n in per_result.items():
            tier_counts[int(tier)] = tier_counts.get(int(tier), 0) + n
        for node in result.candidate_nodes:
            r = node.get("_routing") or {}
            reason = r.get("escalation_reason")
            if reason and reason != "none":
                escalation_counts[reason] = escalation_counts.get(reason, 0) + 1

    return {
        "by_status": counts,
        "by_tier": tier_counts,
        "by_escalation_reason": escalation_counts,
    }


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
