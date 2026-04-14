"""
basis.ingest — generalised ingestion pipeline.

One adapter per source type (SCHEMA-008). Each adapter consumes a URL
or identifier, produces a schema-valid source plus candidate node(s),
and routes the result to persistence.

Public entry points:
    from ingest import ingest_one, ingest_backlog
    from ingest.base import IngestionResult

Usage (CLI):
    python -m ingest <url-or-id> [--dry-run]
    python -m ingest backlog [--path data/v1_ingestion_backlog.json]
"""

from ingest.base import IngestionResult, Adapter
from ingest.cli import ingest_one, ingest_backlog

__all__ = ["IngestionResult", "Adapter", "ingest_one", "ingest_backlog"]
