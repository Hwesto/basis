"""
src/curator — three-tier routing per SCHEMA-024.

Public entry point:
    from curator import route, RoutingDecision, RoutingContext
    from curator import Tier, EscalationReason

The route() function takes a candidate node + its source + an optional
RoutingContext (per-call state like in-domain counts) and returns a
RoutingDecision. Pure function. No DB writes. No HTTP calls.

Caller (ingest/cli.py) is responsible for:
- Computing RoutingContext from local state or Supabase
- Persisting the decision via ingest/persistence.py
- Reporting tier counts (run_agent.py)

References:
    SCHEMA-024 (three-tier curator routing)
    docs/schema/decisions/SCHEMA-024-three-tier-curator-routing.md
"""
from curator.escalations import EscalationReason, Tier
from curator.routing import RoutingDecision, route
from curator.context import RoutingContext

__all__ = [
    "EscalationReason",
    "Tier",
    "RoutingDecision",
    "RoutingContext",
    "route",
]
