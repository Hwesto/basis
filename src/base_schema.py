"""
base_schema.py — The contract everything is built against.

Implements the schema decisions under docs/schema/ (v0.3). Every node in
BASIS is a BaseNode subclass. The curator queue, CI validator, and MC
engine operate against BaseNode only. Domain-specific fields belong on
subclasses, never on the base.

References:
    SCHEMA-001 through SCHEMA-023 (docs/schema/decisions/)
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DomainEnum(str, Enum):
    """
    SCHEMA-002: Typed, extensible. New domains require a code change.

    The three entries at the end (energy, eu_trade, electoral_reform)
    were added in the v2 revision after the v1 audit showed 22% of the
    v1 corpus was in these domains with ad-hoc labels.
    """
    housing = "housing"
    health = "health"
    education = "education"
    benefits = "benefits"
    economy = "economy"
    taxation = "taxation"
    environment = "environment"
    immigration = "immigration"
    policing = "policing"
    defence = "defence"
    transport = "transport"
    social_care = "social_care"
    employment = "employment"
    consumer = "consumer"
    justice = "justice"
    # SCHEMA-002 v2 extension (see docs/migration/README.md)
    energy = "energy"
    eu_trade = "eu_trade"
    electoral_reform = "electoral_reform"


class JurisdictionEnum(str, Enum):
    """
    SCHEMA-003: Hard constraint on legal content.
    england_and_wales resolves OQ-005 for joint-jurisdiction legislation.
    """
    england = "england"
    wales = "wales"
    scotland = "scotland"
    ni = "ni"
    england_and_wales = "england_and_wales"
    uk_wide = "uk_wide"


class ConfidenceLevel(str, Enum):
    """SCHEMA-004: Categorical, not decimal."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class NodeType(str, Enum):
    """All allowed node_type values across all layers."""
    # Evidence layer
    FACT = "FACT"
    ASSUMPTION = "ASSUMPTION"
    CLAIM = "CLAIM"
    POLICY = "POLICY"
    POSITION = "POSITION"
    # Legal layer (Hohfeldian)
    RIGHT = "RIGHT"
    DUTY = "DUTY"
    POWER = "POWER"
    LIABILITY = "LIABILITY"
    PRIVILEGE = "PRIVILEGE"
    IMMUNITY = "IMMUNITY"
    REGULATORY_BODY = "REGULATORY_BODY"
    MECHANISM = "MECHANISM"
    EVIDENCE_REQUIREMENT = "EVIDENCE_REQUIREMENT"
    ESCALATION_PATH = "ESCALATION_PATH"
    PRECEDENT = "PRECEDENT"
    # Local data layer
    AREA_METRIC = "AREA_METRIC"
    # Action layer
    TEMPLATE = "TEMPLATE"
    SUBMISSION = "SUBMISSION"
    OUTCOME = "OUTCOME"


class EdgeType(str, Enum):
    """
    SCHEMA-016: Six evidence edge types.
    Properties enforced in MC engine:
        SUPPORTS      — noisy-OR, not transitive
        CONTRADICTS   — discount, symmetric
        DEPENDS_ON    — weakest-link, transitive
        ENABLES       — deontic, not transitive
        COMPETES      — normative, symmetric
        SUPERSEDES    — temporal, marks earlier as deprecated
    """
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DEPENDS_ON = "DEPENDS_ON"
    ENABLES = "ENABLES"
    COMPETES = "COMPETES"
    SUPERSEDES = "SUPERSEDES"


class LegalEdgeType(str, Enum):
    """Edge types for the legal layer."""
    CREATES = "CREATES"
    IMPOSES = "IMPOSES"
    ENFORCED_BY = "ENFORCED_BY"
    ACCEPTED_BY = "ACCEPTED_BY"
    REQUIRES = "REQUIRES"
    ESCALATES_TO = "ESCALATES_TO"
    ESTABLISHED_BY = "ESTABLISHED_BY"
    SUPERSEDES = "SUPERSEDES"


class CrossLayerEdgeType(str, Enum):
    """Edge types connecting nodes across layers."""
    EVIDENCES = "EVIDENCES"
    ESTABLISHES = "ESTABLISHES"
    TRIGGERS = "TRIGGERS"
    QUANTIFIES = "QUANTIFIES"


class GapRole(str, Enum):
    """SCHEMA-014: Fiscal gap_role taxonomy."""
    additional_need = "additional_need"
    baseline = "baseline"
    position_only = "position_only"
    summary = "summary"
    uplift = "uplift"
    target_total = "target_total"


class DeonticStrength(str, Enum):
    """SCHEMA-012: Covers 80% of weight-based norms without PRINCIPLE node type."""
    ABSOLUTE = "ABSOLUTE"
    QUALIFIED = "QUALIFIED"
    CONDITIONAL = "CONDITIONAL"
    DIRECTORY = "DIRECTORY"
    ASPIRATIONAL = "ASPIRATIONAL"


class CommencementStatus(str, Enum):
    """
    SCHEMA-011: Six-value enum.
    Driven by Renters' Rights Act 2025 edge cases. Resolves OQ-002.
    """
    in_force = "in_force"
    partially_in_force = "partially_in_force"
    not_commenced = "not_commenced"
    prospectively_repealed = "prospectively_repealed"
    repealed = "repealed"
    unknown = "unknown"


class StructuralStability(str, Enum):
    """Derived from Lex Graph amendment history. Feeds MC prior."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ApprovedBy(str, Enum):
    """SCHEMA-024: who flipped curator_approved last (audit trail)."""
    auto = "auto"
    claude = "claude"
    human = "human"


class VerificationLevel(str, Enum):
    """SCHEMA-024: cumulative assurance label, displayed publicly.

    auto_verified  = passed Tier 1 only
    ai_reviewed    = passed Tier 1 + Claude judgment
    human_curated  = above + human spot-confirmed (or human-approved direct)
    """
    auto_verified = "auto_verified"
    ai_reviewed = "ai_reviewed"
    human_curated = "human_curated"


# ---------------------------------------------------------------------------
# Nested models
# ---------------------------------------------------------------------------

class ComputedConfidence(BaseModel):
    """SCHEMA-005: MC engine output. Separate from extraction-time confidence."""
    mean: float = Field(ge=0.0, le=1.0)
    std: float = Field(ge=0.0)
    p5: float = Field(ge=0.0, le=1.0)
    p95: float = Field(ge=0.0, le=1.0)
    label: ConfidenceLevel


class FiscalMetadata(BaseModel):
    """
    SCHEMA-014: Attached to FACT, CLAIM, POLICY nodes with monetary content.
    gap_role determines contribution to the computed fiscal gap.

    v2 adds amount_low / amount_high range fields. v1 stored ranges as
    separate keys and lost them on the v2 draft's scalar-only model;
    this is the restoration. When either bound is set both must be set
    and amount_low <= amount <= amount_high.
    """
    amount: float
    amount_low: float | None = None
    amount_high: float | None = None
    unit: Literal["bn_gbp", "m_gbp", "pct_gdp"]
    gap_role: GapRole
    direction: Literal["spending", "revenue", "net"]
    horizon_years: int | None = None
    year: int | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def range_is_consistent(self) -> "FiscalMetadata":
        lo, hi = self.amount_low, self.amount_high
        if (lo is None) != (hi is None):
            raise ValueError(
                "FiscalMetadata: amount_low and amount_high must be set "
                "together, or both None."
            )
        if lo is not None and hi is not None:
            if lo > hi:
                raise ValueError(
                    f"FiscalMetadata: amount_low ({lo}) must be <= "
                    f"amount_high ({hi})."
                )
            if not (lo <= self.amount <= hi):
                raise ValueError(
                    f"FiscalMetadata: amount ({self.amount}) must lie "
                    f"within [amount_low={lo}, amount_high={hi}]."
                )
        return self


# ---------------------------------------------------------------------------
# BaseNode (SCHEMA-001)
# ---------------------------------------------------------------------------

class BaseNode(BaseModel):
    """
    SCHEMA-001: Single root class. Every entity is a subclass.
    The curator queue, CI validator, and MC engine operate against this.
    """
    id: str
    node_type: NodeType
    statement: str = Field(min_length=10)
    source_id: str | None = None
    source_loc: str | None = None
    confidence: ConfidenceLevel | None = None
    computed_confidence: ComputedConfidence | None = None
    domain: DomainEnum
    jurisdiction: list[JurisdictionEnum] | None = None
    verified: bool = False
    curator_approved: bool = False
    # SCHEMA-024: who flipped curator_approved + cumulative assurance level
    approved_by: ApprovedBy | None = None
    verification_level: VerificationLevel | None = None
    last_audited_by: ApprovedBy | None = None
    last_audited_at: datetime | None = None
    extraction_run_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def approval_requires_verification_level(self) -> "BaseNode":
        """SCHEMA-024 mirror of the SQL CHECK: if curator_approved is true,
        verification_level must say how it got there. Caller must set both
        atomically."""
        if self.curator_approved and self.verification_level is None:
            raise ValueError(
                "BaseNode: curator_approved=True requires verification_level "
                "to be set (SCHEMA-024)."
            )
        return self


# ---------------------------------------------------------------------------
# Evidence layer subclasses
# ---------------------------------------------------------------------------

class FactNode(BaseNode):
    """SCHEMA-013: Directly sourced. source_id mandatory."""
    node_type: Literal[NodeType.FACT] = NodeType.FACT
    source_id: str
    fiscal: FiscalMetadata | None = None
    extraction_notes: str | None = None

    @field_validator("source_id")
    @classmethod
    def source_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("FACT nodes require a non-empty source_id")
        return v


class AssumptionNode(BaseNode):
    """
    SCHEMA-013: Requires interpretation. Must list basis facts.
    SCHEMA-020: Capped in MC by contestability discount.
    """
    node_type: Literal[NodeType.ASSUMPTION] = NodeType.ASSUMPTION
    basis_fact_ids: list[str] = Field(min_length=1)
    falsification_condition: str = Field(min_length=10)
    fiscal: FiscalMetadata | None = None
    extraction_notes: str | None = None


class ClaimNode(BaseNode):
    """Interpretive statement supported by evidence edges."""
    node_type: Literal[NodeType.CLAIM] = NodeType.CLAIM
    fiscal: FiscalMetadata | None = None
    extraction_notes: str | None = None


class PolicyNode(BaseNode):
    """A policy position or proposal."""
    node_type: Literal[NodeType.POLICY] = NodeType.POLICY
    fiscal: FiscalMetadata | None = None
    party: str | None = None
    manifesto_year: int | None = None
    extraction_notes: str | None = None


class PositionNode(BaseNode):
    """A stated position by an actor."""
    node_type: Literal[NodeType.POSITION] = NodeType.POSITION
    actor: str
    actor_type: Literal[
        "minister", "mp", "party", "official",
        "expert", "body", "citizen"
    ] | None = None
    date: str | None = None
    extraction_notes: str | None = None


# ---------------------------------------------------------------------------
# Edge models (SCHEMA-015, SCHEMA-016, SCHEMA-017)
# ---------------------------------------------------------------------------

EXPLANATION_BLOCKLIST = [
    r"^supports?$",
    r"^related$",
    r"^depends on$",
    r"^see above$",
    r"^as noted$",
    r"^links? to$",
    r"^connected$",
]
_BLOCKLIST_PATTERN = re.compile(
    "|".join(EXPLANATION_BLOCKLIST), re.IGNORECASE
)


class EvidenceEdge(BaseModel):
    """
    SCHEMA-015: evidence_independent on SUPPORTS edges.
    SCHEMA-016: edge_type determines MC semantics.
    SCHEMA-017: explanation must say something.
    """
    id: str
    from_id: str
    to_id: str
    edge_type: EdgeType
    explanation: str = Field(min_length=10)
    strength: ConfidenceLevel | None = None
    evidence_independent: bool = True

    @field_validator("explanation")
    @classmethod
    def explanation_not_boilerplate(cls, v: str) -> str:
        if _BLOCKLIST_PATTERN.match(v.strip()):
            raise ValueError(
                f"Edge explanation is boilerplate: '{v}'. "
                "Must describe the specific relationship."
            )
        return v

    @model_validator(mode="after")
    def independence_only_on_supports(self) -> "EvidenceEdge":
        if self.edge_type != EdgeType.SUPPORTS and not self.evidence_independent:
            self.evidence_independent = True
        return self


class LegalEdge(BaseModel):
    """Edge between legal-layer nodes."""
    id: str
    from_id: str
    to_id: str
    edge_type: LegalEdgeType
    jurisdiction: list[JurisdictionEnum] | None = None
    explanation: str = Field(min_length=10)
    strength: ConfidenceLevel | None = None

    @field_validator("explanation")
    @classmethod
    def explanation_not_boilerplate(cls, v: str) -> str:
        if _BLOCKLIST_PATTERN.match(v.strip()):
            raise ValueError(f"Edge explanation is boilerplate: '{v}'.")
        return v


class CrossLayerEdge(BaseModel):
    """Edge connecting nodes across different layers."""
    id: str
    from_layer: Literal["evidence", "legal", "local", "action"]
    from_id: str
    to_layer: Literal["evidence", "legal", "local", "action"]
    to_id: str
    edge_type: CrossLayerEdgeType

    @model_validator(mode="after")
    def layers_differ(self) -> "CrossLayerEdge":
        if self.from_layer == self.to_layer:
            raise ValueError(
                "CrossLayerEdge must connect different layers."
            )
        return self


class CitationEdge(BaseModel):
    """
    SCHEMA-009: Tier lives on the citation edge, not the source.

    A source carries a `default_tier` as a global quality prior. The
    citation between a source and a node carries an optional
    `claim_tier_override` for cases where the source is being cited
    outside its primary domain of competence — with mandatory
    justification when set.

    The MC engine uses claim_tier_override if present, otherwise
    default_tier from the linked source.

    STRUCTURED_DATA uses provider_tier directly; override not permitted.
    STRUCTURAL / DERIVED / TESTIMONY: no tier. Override not applicable.
    """
    id: str
    source_id: str
    node_id: str
    citation_locator: str | None = None  # "p.14 para 3", "Table 2", etc.
    claim_tier_override: Literal["T1", "T2", "T3", "T4", "T5", "T6"] | None = None
    claim_tier_justification: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # curator id or extraction_run_id

    @model_validator(mode="after")
    def override_requires_justification(self) -> "CitationEdge":
        if self.claim_tier_override is not None:
            if not self.claim_tier_justification or len(
                self.claim_tier_justification.strip()
            ) < 10:
                raise ValueError(
                    "CitationEdge: claim_tier_override requires a "
                    "non-trivial claim_tier_justification (>= 10 chars)."
                )
        return self
