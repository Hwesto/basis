"""
escalations.py — SCHEMA-024 routing tier + escalation reason enums.

The 13 EscalationReason values are deliberate. Cost of a missing
value is a code change later; cost of carrying an unused value is
one enum line. Add new values when a real situation needs one.
"""
from __future__ import annotations

from enum import Enum, IntEnum


class Tier(IntEnum):
    """Routing target. Lower number = more autonomous, higher = more human."""
    AUTO_APPROVED = 1   # all Tier 1 gates passed AND not always-tier-3
    CLAUDE_REVIEW = 2   # passed Tier 1; awaits Claude judgment
    HUMAN_REVIEW = 3    # awaits operator (Harry) review


class EscalationReason(str, Enum):
    """Why a node ended up at Tier 3.

    Tracked per-week to surface which gates are too loose (high
    frequency on extraction_ambiguous = tighten Tier 1 prompt; high
    frequency on tier1_hard_fail with the same fast_fail_check =
    promote that check to a normaliser instead of a gate).

    Per SCHEMA-024 §"Escalation reason" and §"Calibration knobs".
    """
    # No escalation — node passed Tier 1 cleanly
    NONE = "none"

    # Claude (Tier 2) asked for help
    CLAUDE_UNCERTAIN = "claude_uncertain"
    SOURCE_TEXT_UNAVAILABLE = "source_text_unavailable"
    EXTRACTION_AMBIGUOUS = "extraction_ambiguous"
    MODEL_DISAGREEMENT = "model_disagreement"
    OUT_OF_DISTRIBUTION = "out_of_distribution"

    # Always-Tier-3 categories (bypass Tier 1)
    PRECEDENT_NODE = "precedent_node"
    CIVIC_FINDING = "civic_finding"
    TEMPLATE_LEGAL_REVIEW = "template_legal_review"
    CROSS_DOMAIN = "cross_domain"

    # Calibration windows (first-N of new domain / source / model)
    FIRST_IN_WINDOW = "first_in_window"

    # Source-quality floor (TESTIMONY T5, DERIVED with unapproved inputs)
    LOW_SOURCE_PROVENANCE = "low_source_provenance"

    # Tier 1 gate failure (fast_fail_check on the decision says which one)
    TIER1_HARD_FAIL = "tier1_hard_fail"
