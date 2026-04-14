"""
legal_schema.py — Hohfeldian legal node schema for Phase 4 extraction.

This is the Pydantic model passed to Gemma 4 26B MoE via:
    response_mime_type = "application/json"
    response_schema = LegalNode
Guaranteed schema-conformant output. Schema violations fail the call.

References:
    Phase 4 roadmap, SCHEMA-012, SCHEMA-023
"""

from __future__ import annotations

from typing import Literal

from base_schema import (
    BaseNode,
    CommencementStatus,
    ConfidenceLevel,
    DeonticStrength,
    DomainEnum,
    JurisdictionEnum,
    NodeType,
    StructuralStability,
)


class LegalNode(BaseNode):
    """
    Hohfeldian legal node. Extends BaseNode with legal-specific fields.
    Structural signals denormalised from lex_provisions for MC engine access.

    Used as Gemma's response_schema for constrained extraction.
    Used by Claude Code sessions for Track C bootstrap.
    """
    node_type: Literal[
        NodeType.RIGHT,
        NodeType.DUTY,
        NodeType.POWER,
        NodeType.LIABILITY,
        NodeType.PRIVILEGE,
        NodeType.IMMUNITY,
        NodeType.REGULATORY_BODY,
        NodeType.MECHANISM,
        NodeType.EVIDENCE_REQUIREMENT,
        NodeType.ESCALATION_PATH,
        NodeType.PRECEDENT,
    ]

    # Link to source provision
    lex_provision_id: str  # FK to lex_provisions.lex_id

    # Who this applies to and who bears the duty/liability
    applies_to: list[str]  # ['tenant', 'homeowner', 'local_authority', ...]
    duty_holder: str | None = None
    duty_holder_type: Literal[
        "local_authority", "private_landlord",
        "public_body", "employer", "individual",
    ] | None = None

    # Deontic strength (SCHEMA-012: replaces PRINCIPLE node type for 80% of cases)
    deontic_strength: DeonticStrength | None = None

    # Structural signals from lex_provisions (denormalised for MC)
    structural_stability: StructuralStability | None = None
    commencement_status: CommencementStatus | None = None
    commencement_notes: str | None = None  # plain English for partial/conditional

    extraction_notes: str | None = None


class RegulatoryBodyNode(BaseNode):
    """A body with enforcement or oversight powers."""
    node_type: Literal[NodeType.REGULATORY_BODY] = NodeType.REGULATORY_BODY
    body_name: str
    powers: list[str] | None = None  # summary of key powers
    contact_url: str | None = None
    complaint_url: str | None = None
    extraction_notes: str | None = None


class PrecedentNode(BaseNode):
    """A court decision establishing or modifying legal interpretation."""
    node_type: Literal[NodeType.PRECEDENT] = NodeType.PRECEDENT
    case_name: str
    court: str
    date: str
    citation: str  # e.g. '[2023] UKSC 14'
    lex_provision_id: str | None = None  # provision interpreted
    ratio: str  # the legal principle established
    extraction_notes: str | None = None
