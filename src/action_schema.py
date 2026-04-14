"""
action_schema.py — Action layer models for Phase 5.

Every issue maps to one or more action channels. The escalation tree
is itself part of the knowledge graph.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from base_schema import (
    BaseNode,
    ConfidenceLevel,
    DomainEnum,
    JurisdictionEnum,
    NodeType,
)


class MechanismNode(BaseNode):
    """
    An action a citizen can take: complaint, FOI, tribunal, etc.
    Carries routing logic and links to templates.
    """
    node_type: Literal[NodeType.MECHANISM] = NodeType.MECHANISM
    mechanism_id: str
    applicable_issues: list[str]       # ['housing_disrepair', 'mould', 'pests']
    applicable_to: list[str]           # ['tenant', 'homeowner']
    prerequisite_ids: list[str] = []   # mechanism_ids that must be completed first
    statutory_response_window_days: int | None = None
    template_id: str | None = None
    evidence_required: list[str] | None = None
    success_rate: float | None = None  # populated from outcomes (Phase 6)
    escalates_to: list[str] = []       # mechanism_ids
    escalation_trigger: str | None = None  # 'no_response_21_days', etc.
    contact_resolution: str | None = None  # how to find the right contact


class TemplateNode(BaseNode):
    """
    A document template with named slots.
    Slots are populated from user data, local data, legal layer, evidence layer.
    """
    node_type: Literal[NodeType.TEMPLATE] = NodeType.TEMPLATE
    template_id: str
    template_type: Literal[
        "council_complaint", "mp_letter", "ombudsman_complaint",
        "foi_request", "eir_request", "pre_action_protocol",
        "letter_before_action", "tribunal_application",
        "public_inquiry_submission", "petition_text",
        "regulatory_complaint", "legal_aid_referral",
    ]
    mechanism_id: str              # which mechanism this template serves
    slots: list[str]               # named slots: ['council_name', 'mp_name', 'statute_ref']
    slot_sources: dict[str, str] | None = None  # slot -> data source layer
    body_template: str             # the template text with {slot_name} placeholders
    legal_basis: str | None = None # statute reference
    solicitor_signed_off: bool = False  # governance gate (separate from curator_approved)


class SubmissionNode(BaseNode):
    """Tracks a citizen's use of a mechanism."""
    node_type: Literal[NodeType.SUBMISSION] = NodeType.SUBMISSION
    user_id: str | None = None     # optional, privacy-preserving
    mechanism_id: str
    template_id: str | None = None
    issue_type: str
    area_code: str | None = None
    submitted_at: datetime | None = None
    response_deadline: datetime | None = None


class OutcomeNode(BaseNode):
    """
    Records the result of a citizen action.
    Outcomes feed back into the graph (Phase 6):
    - success -> MECHANISM confidence strengthens
    - no_response -> response_rate decrements
    - escalated -> escalation edge strengthens
    """
    node_type: Literal[NodeType.OUTCOME] = NodeType.OUTCOME
    submission_id: str
    mechanism_id: str
    outcome: Literal[
        "resolved", "escalated", "withdrawn", "pending", "no_response"
    ]
    outcome_recorded_at: datetime | None = None
    escalated_to: str | None = None  # mechanism_id of next step
    resolution_days: int | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# Action tracking SQL model (for citizen_actions table)
# ---------------------------------------------------------------------------

class CitizenAction(BaseModel):
    """Mirrors the citizen_actions SQL table for API use."""
    id: str
    user_id: str | None = None
    issue_type: str
    jurisdiction: str
    mechanism_id: str
    template_id: str | None = None
    submitted_at: datetime | None = None
    response_deadline: datetime | None = None
    outcome: Literal[
        "resolved", "escalated", "withdrawn", "pending", "no_response"
    ] | None = None
    outcome_recorded_at: datetime | None = None
    escalated_to: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
