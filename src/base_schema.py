"""
base_schema.py — The contract everything is built against.

Implements schema_decisions.md v0.2. Every node in BASIS is a BaseNode subclass.
The curator queue, CI validator, and MC engine operate against BaseNode only.
Domain-specific fields belong on subclasses, never on the base.

References:
    SCHEMA-001 through SCHEMA-017, SCHEMA-023
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
    """SCHEMA-002: Typed, extensible. New domains require a code change."""
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
    """
    amount: float
    unit: Literal["bn_gbp", "m_gbp", "pct_gdp"]
    gap_role: GapRole
    direction: Literal["spending", "revenue", "net"]
    horizon_years: int | None = None
    year: int | None = None
    notes: str | None = None


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
    extraction_run_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


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
