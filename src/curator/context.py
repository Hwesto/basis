"""
context.py — RoutingContext: per-call state the routing module needs.

The routing module is pure. It doesn't query the DB. Counts and
flags it needs to make a decision are passed in via this dataclass.

Caller (typically src/ingest/cli.py) computes these values from
local state (data/v2_graph/*.jsonl during Phase 1) or Supabase
(once the MCP is live in Phase 2).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RoutingContext:
    """
    Per-call context for the routing module.

    All fields default to "no calibration concerns" so callers that
    don't have the data yet still get a sensible result. Calibration
    windows trigger when counts are below their thresholds — see
    SCHEMA-024 calibration knobs in docs/status.md.
    """

    # How many curator-touched (any tier) nodes from this domain so far.
    # Calibration window: first 20 nodes from a new domain → Tier 3.
    nodes_in_domain_so_far: int = 999  # default = "established domain"

    # How many curator-touched nodes from this source so far.
    # Calibration window: first 5 nodes from a new source → Tier 3.
    nodes_from_source_so_far: int = 999  # default = "established source"

    # Set when the extraction model has been upgraded since the last
    # routing pass. Forces every node to Tier 3 until operator
    # confirms agreement holds. Cleared by operator config flag.
    model_version_changed_recently: bool = False
