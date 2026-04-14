"""
source_models.py — Five source types with type-specific provenance and MC priors.

The single most common architectural mistake in knowledge systems is treating all
sources as the same thing. They are not.

References:
    SCHEMA-008: Five source types
    SCHEMA-009: Tier on citation edge (migration pending)
    SCHEMA-010: STRUCTURAL alpha by registry
    SCHEMA-019: Alpha values (provisional)
    SCHEMA-020: Assumption contestability discount
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from base_schema import DomainEnum, JurisdictionEnum


# ---------------------------------------------------------------------------
# Source type enum
# ---------------------------------------------------------------------------

class SourceTypeEnum(str, Enum):
    """SCHEMA-008: Closed for now, explicitly extensible."""
    DOCUMENTARY = "DOCUMENTARY"
    STRUCTURED_DATA = "STRUCTURED_DATA"
    LEGISLATIVE_STRUCTURAL = "LEGISLATIVE_STRUCTURAL"
    DERIVED = "DERIVED"
    TESTIMONY = "TESTIMONY"
    # Future: INFERRED (Phase 5), CITIZEN_EVIDENCE (Phase 5 challenge system)


# ---------------------------------------------------------------------------
# Tier enums (separate per source type)
# ---------------------------------------------------------------------------

class DocumentaryTier(str, Enum):
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"
    T6 = "T6"


class ProviderTier(str, Enum):
    """STRUCTURED_DATA only. T4-T6 don't apply to datasets."""
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"


class TestimonyTier(str, Enum):
    """Testimony is never T1/T2. Hard ceiling at T3."""
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"


# ---------------------------------------------------------------------------
# BaseSource
# ---------------------------------------------------------------------------

class BaseSource(BaseModel):
    """Root source model. Discriminated by source_type."""
    source_id: str
    source_type: SourceTypeEnum
    domain: DomainEnum | None = None
    jurisdiction: list[JurisdictionEnum] | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# DOCUMENTARY (SCHEMA-008)
# ---------------------------------------------------------------------------

class DocumentarySource(BaseSource):
    """
    Human-authored documents: reports, papers, statutes, guidance, manifestos.
    Tier auto-assigned from signals at ingestion; human can override.
    """
    source_type: Literal[SourceTypeEnum.DOCUMENTARY] = SourceTypeEnum.DOCUMENTARY
    title: str
    author: str | None = None
    publisher: str
    published_date: str
    url: str | None = None
    doi: str | None = None
    tier: DocumentaryTier
    tier_justification: str = Field(min_length=5)
    full_text: str | None = None
    content_hash: str | None = None  # sha256; change = re-verify
    fetched_at: datetime | None = None
    # Academic quality from Semantic Scholar (free API, no key)
    citation_count: int | None = None
    influential_citation_count: int | None = None
    citation_velocity: float | None = None
    venue: str | None = None
    open_access: bool | None = None


# ---------------------------------------------------------------------------
# STRUCTURED_DATA (SCHEMA-008)
# ---------------------------------------------------------------------------

class StructuredDataSource(BaseSource):
    """
    Datasets and API responses: time-series, statistical releases, registers.
    Provider tier from whitelist. No full_text, no author, no T4-T6.
    """
    source_type: Literal[SourceTypeEnum.STRUCTURED_DATA] = SourceTypeEnum.STRUCTURED_DATA
    provider: str  # 'ONS', 'police.uk', 'land_registry'
    dataset_id: str
    metric_id: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    methodology_url: str | None = None
    provider_tier: ProviderTier
    api_endpoint: str | None = None
    last_refreshed: datetime | None = None


# ---------------------------------------------------------------------------
# LEGISLATIVE_STRUCTURAL (SCHEMA-008, SCHEMA-010)
# ---------------------------------------------------------------------------

class LegislativeStructuralSource(BaseSource):
    """
    Lex Graph edges and provision attributes.
    No tier. Structural sources have certainty, not tier.
    MC alpha = 1.0 on the structural fact itself (SCHEMA-010 nuances by registry).
    """
    source_type: Literal[SourceTypeEnum.LEGISLATIVE_STRUCTURAL] = (
        SourceTypeEnum.LEGISLATIVE_STRUCTURAL
    )
    lex_provision_id: str
    edge_type: Literal[
        "citation", "amendment", "cross_reference",
        "commencement", "repeal"
    ]
    related_provision_id: str | None = None
    recorded_date: date | None = None
    # No tier field. See SCHEMA-010.


# ---------------------------------------------------------------------------
# DERIVED (SCHEMA-008)
# ---------------------------------------------------------------------------

class DerivedSource(BaseSource):
    """
    Computations from other nodes: fiscal gap, MC scores, percentile ranks.
    No tier, no fetch, no author. Quality = quality of inputs via MC propagation.
    """
    source_type: Literal[SourceTypeEnum.DERIVED] = SourceTypeEnum.DERIVED
    computation_id: str  # 'FISCAL_GAP_V3', 'MC_CONF_RUN_42'
    algorithm_version: str
    input_node_ids: list[str]
    computed_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# TESTIMONY (SCHEMA-008)
# ---------------------------------------------------------------------------

class TestimonySource(BaseSource):
    """
    Stated positions and submissions: Hansard, FOI, ombudsman rulings.
    Tier ceiling T3. A minister's claim is T4. Citizen challenge is T5.
    """
    source_type: Literal[SourceTypeEnum.TESTIMONY] = SourceTypeEnum.TESTIMONY
    actor: str
    actor_type: Literal[
        "minister", "mp", "official", "expert",
        "citizen", "ombudsman", "court"
    ]
    date: date
    context: str  # 'hansard_debate', 'select_committee', 'foi_response', etc.
    verbatim_ref: str | None = None
    tier: TestimonyTier


# ---------------------------------------------------------------------------
# MC Alpha Tables (SCHEMA-019, SCHEMA-010, SCHEMA-020)
# All values are design choices, not measurements. Require calibration study.
# ---------------------------------------------------------------------------

# SCHEMA-019: Documentary alpha by tier, verification, citation count
# Key: (tier, verified, high_citation)
# high_citation = citation_count > 100 and influential_citation_count > 5
DOCUMENTARY_ALPHA: dict[tuple[str, bool, bool | None], float] = {
    ("T1", True, True):    0.95,  # T1, verified, well-cited
    ("T1", True, False):   0.75,  # T1, verified, low citations
    ("T1", False, None):   0.85,  # T1, unverified
    ("T2", True, None):    0.85,  # T2, verified
    ("T2", False, None):   0.70,  # T2, unverified
    ("T3", None, None):    0.70,
    ("T4", None, None):    0.55,
    ("T5", None, None):    0.45,
    ("T6", None, None):    0.40,
}

# SCHEMA-019: Structured data alpha by provider tier
STRUCTURED_DATA_ALPHA: dict[str, float] = {
    "T1": 0.92,  # ONS, NHS Digital, DWP Stat-Xplore
    "T2": 0.80,  # Police.uk, Land Registry
    "T3": 0.60,  # Council CSVs
}

# SCHEMA-010: Structural alpha by registry (not by category)
STRUCTURAL_ALPHA: dict[str, float] = {
    "lex_graph_commencement":    0.95,
    "lex_graph_amendment":       0.98,
    "ons_nspl_postcode":         0.99,
    "land_registry_title":       0.90,
    "companies_house_active":    0.85,
    "electoral_commission":      0.92,
    "ico_register":              0.93,
    "fca_register":              0.94,
    "charity_commission":        0.91,
}

# SCHEMA-019: Testimony alpha by tier
TESTIMONY_ALPHA: dict[str, float] = {
    "T3": 0.55,  # ombudsman, court
    "T4": 0.45,  # minister, official
    "T5": 0.35,  # citizen challenge
}

# SCHEMA-007: Verification multiplier
VERIFIED_MULTIPLIER: float = 1.5

# SCHEMA-020: Assumption contestability discount
# Even perfectly-supported assumptions cap out.
ASSUMPTION_DISCOUNT: dict[str, float] = {
    "HIGH":   0.85,
    "MEDIUM": 0.70,
    "LOW":    0.50,
}

# Provider tier whitelist for STRUCTURED_DATA
PROVIDER_TIER_WHITELIST: dict[str, str] = {
    "ONS":           "T1",
    "NHS Digital":   "T1",
    "DWP Stat-Xplore": "T1",
    "NHSE":          "T1",
    "Police.uk":     "T2",
    "Land Registry": "T2",
    "CQC":           "T2",
    "Ofsted":        "T2",
    "Environment Agency": "T2",
    "Companies House": "T2",
    "HMRC":          "T1",
    "DfE":           "T1",
    "DLUHC":         "T1",
    "TfL":           "T2",
    # Council CSVs default to T3 (not in whitelist)
}


def get_provider_tier(provider: str) -> str:
    """Look up provider tier from whitelist. Default T3 for unknown providers."""
    return PROVIDER_TIER_WHITELIST.get(provider, "T3")


def get_documentary_alpha(
    tier: str,
    verified: bool = False,
    citation_count: int | None = None,
    influential_citation_count: int | None = None,
) -> float:
    """
    Resolve MC alpha for a DocumentarySource.
    SCHEMA-019: These are provisional priors.
    """
    high_citation = (
        citation_count is not None
        and influential_citation_count is not None
        and citation_count > 100
        and influential_citation_count > 5
    )

    # Try exact match first (table already factors in verification status)
    key = (tier, verified, high_citation if tier == "T1" and verified else None)
    if key in DOCUMENTARY_ALPHA:
        return DOCUMENTARY_ALPHA[key]

    # Fallback: try verified-agnostic lookup
    fallback = (tier, None, None)
    alpha = DOCUMENTARY_ALPHA.get(fallback, 0.40)

    # SCHEMA-007: verification multiplier only when table didn't already handle it
    # The table has separate entries for verified/unverified at T1/T2.
    # This fallback path is for T3-T6 where verified isn't in the key.
    if verified and tier not in ("T1", "T2"):
        alpha = min(alpha * VERIFIED_MULTIPLIER, 1.0)

    return alpha


def get_structured_data_alpha(provider_tier: str) -> float:
    """Resolve MC alpha for a StructuredDataSource."""
    return STRUCTURED_DATA_ALPHA.get(provider_tier, 0.60)


def get_structural_alpha(registry: str) -> float:
    """
    SCHEMA-010: Alpha by registry, not by category.
    Default 0.90 for unknown registries (conservative).
    """
    return STRUCTURAL_ALPHA.get(registry, 0.90)


def get_testimony_alpha(tier: str) -> float:
    """Resolve MC alpha for a TestimonySource."""
    return TESTIMONY_ALPHA.get(tier, 0.35)


def get_assumption_cap(extraction_confidence: str) -> float:
    """
    SCHEMA-020: Assumption ceiling by extraction-time confidence.
    Even perfectly-supported assumptions cannot reach certainty.
    """
    return ASSUMPTION_DISCOUNT.get(extraction_confidence, 0.50)
