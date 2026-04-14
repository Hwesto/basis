"""
always_tier3.py — bypass rules that send certain node shapes straight
to human review regardless of any Tier 1 / Tier 2 check.

Per SCHEMA-024 §"Tier 3 — Human (exception queue only)".

Each rule is a function (node, source, context) → EscalationReason | None.
First match wins. Routing module checks these BEFORE running Tier 1.
"""
from __future__ import annotations

from typing import Callable

from curator.context import RoutingContext
from curator.escalations import EscalationReason


def is_precedent(node: dict, source: dict, context: RoutingContext) -> EscalationReason | None:
    """PRECEDENT (legal-layer node type, SCHEMA-012/Phase 4).

    Court decisions have legal weight. Misclassifying ratio creates
    downstream errors that propagate into action templates.
    """
    if node.get("node_type") == "PRECEDENT":
        return EscalationReason.PRECEDENT_NODE
    return None


def is_template(node: dict, source: dict, context: RoutingContext) -> EscalationReason | None:
    """TEMPLATE (action-layer, Phase 5).

    Templates are documents citizens send to councils, ombudsmen,
    courts. Wrong wording can damage a real case. Always solicitor-
    reviewed (handled at Tier 3 with the additional solicitor_signed_off
    flag on the node itself).
    """
    if node.get("node_type") == "TEMPLATE":
        return EscalationReason.TEMPLATE_LEGAL_REVIEW
    return None


def is_civic_finding(node: dict, source: dict, context: RoutingContext) -> EscalationReason | None:
    """ENFORCEMENT_GAP and MISSING_CORRELATIVE findings from CI checks 7+8
    (SCHEMA-023). Both are civic findings with political consequence —
    cannot be auto-approved.

    The CI check sets node['civic_finding_kind'] when it produces a
    candidate. The flag is the discriminator; Claude won't be invoked
    to second-guess the CI check on this category.
    """
    if node.get("civic_finding_kind") in ("ENFORCEMENT_GAP", "MISSING_CORRELATIVE"):
        return EscalationReason.CIVIC_FINDING
    return None


def is_cross_domain(node: dict, source: dict, context: RoutingContext) -> EscalationReason | None:
    """Cross-domain edge — depends on understanding two domains'
    epistemics. Claude review is provisional pending audit, so we
    escalate.

    Edge payloads carry from_id and to_id. If the routing module is
    called on an edge (rather than a node), and we can determine the
    domains of both endpoints, mismatch escalates.

    The endpoint domains come in via auxiliary fields the caller
    populates: from_domain, to_domain. If they aren't set we can't
    decide and let the Tier 1 pipeline run.
    """
    if not (node.get("from_id") and node.get("to_id")):
        return None
    a, b = node.get("from_domain"), node.get("to_domain")
    if a and b and a != b:
        return EscalationReason.CROSS_DOMAIN
    return None


def is_calibration_window(
    node: dict, source: dict, context: RoutingContext
) -> EscalationReason | None:
    """Calibration windows from SCHEMA-024 §"Always-Tier-3 categories":
      - first 20 nodes from a new domain
      - first 5 nodes from a new source
      - first batch after a model version change
    """
    if context.model_version_changed_recently:
        return EscalationReason.FIRST_IN_WINDOW
    if context.nodes_in_domain_so_far < 20:
        return EscalationReason.FIRST_IN_WINDOW
    if context.nodes_from_source_so_far < 5:
        return EscalationReason.FIRST_IN_WINDOW
    return None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

ALWAYS_TIER3_RULES: list[Callable[[dict, dict, RoutingContext], EscalationReason | None]] = [
    is_precedent,
    is_template,
    is_civic_finding,
    is_cross_domain,
    is_calibration_window,
]


def check_always_tier3(
    node: dict, source: dict, context: RoutingContext
) -> EscalationReason | None:
    """Run all always-tier-3 rules. Return the first triggered reason,
    or None if no rule applies.
    """
    for rule in ALWAYS_TIER3_RULES:
        reason = rule(node, source, context)
        if reason is not None:
            return reason
    return None
