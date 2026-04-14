"""
base.py — Adapter interface shared by every source-type ingester.

Each concrete adapter (documentary, structured_data, structural,
testimony, derived) implements `ingest()` to produce an IngestionResult
carrying:
    - a schema-valid BaseSource subclass (or None on failure)
    - zero or more candidate node payloads (dicts, not yet persisted)
    - zero or more candidate citation_edge payloads
    - a status + rejection log

The orchestrator (`ingest.cli`) routes an input to the right adapter,
collects its result, then hands the payloads to `ingest.persistence`
for DB insertion (with Pydantic validation as a final gate).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol


class IngestStatus(str, Enum):
    OK = "ok"
    SKIPPED = "skipped"            # input valid but intentionally not ingested
    FETCH_FAILED = "fetch_failed"  # couldn't retrieve content
    PARSE_FAILED = "parse_failed"  # retrieved but couldn't understand it
    VALIDATION_FAILED = "validation_failed"  # Pydantic rejected
    ADAPTER_ERROR = "adapter_error"


@dataclass
class IngestionResult:
    """What every adapter must return."""
    status: IngestStatus
    source: Any = None                              # BaseSource subclass instance
    candidate_nodes: list[dict] = field(default_factory=list)
    candidate_citations: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    run_id: str | None = None

    def ok(self) -> bool:
        return self.status == IngestStatus.OK


class Adapter(Protocol):
    """Every source-type adapter implements this."""

    source_type: str  # 'DOCUMENTARY', 'STRUCTURED_DATA', etc.

    def can_handle(self, url_or_id: str, metadata: dict | None = None) -> bool:
        """Cheap routing check. No IO."""
        ...

    def ingest(self, url_or_id: str, metadata: dict | None = None) -> IngestionResult:
        """
        Fetch, parse, validate. Return IngestionResult with
        schema-valid source and candidate nodes/citations.
        """
        ...
