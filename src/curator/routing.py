"""
routing.py — SCHEMA-024 routing orchestrator.

Single public function: `route(node, source, context) -> RoutingDecision`.

Order of evaluation:
    1. Always-Tier-3 bypass rules (PRECEDENT, TEMPLATE, civic findings,
       cross-domain edges, calibration windows). First match → Tier 3.
    2. Tier 1 gate pipeline. First failure → Tier 3 with TIER1_HARD_FAIL.
    3. All clear → Tier 2 (awaits Claude review).

Pure function. No DB writes. No HTTP calls. Caller persists the decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from curator.always_tier3 import check_always_tier3
from curator.checks import CheckFailure, run_tier1_checks
from curator.context import RoutingContext
from curator.escalations import EscalationReason, Tier


@dataclass
class RoutingDecision:
    """The output of route(). Persisted by the caller."""
    tier: Tier
    escalation_reason: Optional[EscalationReason] = None
    fast_fail_check: Optional[str] = None        # set when a Tier 1 gate failed
    auto_approval_conditions: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialise for persistence (jsonl row, SQL insert, etc)."""
        return {
            "tier": int(self.tier),
            "escalation_reason": (
                self.escalation_reason.value if self.escalation_reason else None
            ),
            "fast_fail_check": self.fast_fail_check,
            "auto_approval_conditions": self.auto_approval_conditions,
            "notes": self.notes,
        }


def route(
    node: dict,
    source: dict | None = None,
    context: RoutingContext | None = None,
) -> RoutingDecision:
    """Apply SCHEMA-024 Tier 1 + always-Tier-3 logic to a candidate node.

    Args:
        node: the candidate node payload (from the extractor)
        source: the source the node was extracted from
        context: per-call state (calibration counts, model flags)

    Returns:
        RoutingDecision indicating the queue and (when escalating) why.
    """
    source = source if source is not None else {}
    context = context if context is not None else RoutingContext()

    # 1. Always-Tier-3 bypass rules — precedence, civic findings, calibration.
    bypass = check_always_tier3(node, source, context)
    if bypass is not None:
        return RoutingDecision(
            tier=Tier.HUMAN_REVIEW,
            escalation_reason=bypass,
            notes=[f"Always-Tier-3 rule fired: {bypass.value}"],
        )

    # 2. Tier 1 gates — first failure short-circuits.
    failure: CheckFailure | None = run_tier1_checks(node, source)
    if failure is not None:
        return RoutingDecision(
            tier=Tier.HUMAN_REVIEW,
            escalation_reason=EscalationReason.TIER1_HARD_FAIL,
            fast_fail_check=failure.check_name,
            notes=[failure.reason],
        )

    # 3. All gates passed → route to Claude for judgment.
    #    auto_approval_conditions records WHICH checks passed so the
    #    audit trail can show "Tier 1: schema OK, source quality OK,
    #    boilerplate OK, adversarial OK, flash cross-check OK".
    return RoutingDecision(
        tier=Tier.CLAUDE_REVIEW,
        escalation_reason=EscalationReason.NONE,
        auto_approval_conditions={
            "fact_has_source": True,
            "boilerplate_explanation": True,
            "adversarial_pattern": True,
            "source_quality_floor": True,
            "flash_cross_check": True,
        },
        notes=[
            "Tier 1 passed all gates; routed to Claude review (Tier 2).",
        ],
    )
