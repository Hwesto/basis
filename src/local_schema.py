"""
local_schema.py — Local data layer models for Phase 3.

AreaMetricNode is a BaseNode subclass. Each instance references a
StructuredDataSource. Provider tier drives the MC confidence prior.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from base_schema import BaseNode, DomainEnum, JurisdictionEnum, NodeType


class AreaMetricNode(BaseNode):
    """
    A local data point: one metric for one area at one time period.
    Links back to the evidence graph via node_ids on metric_definitions.
    """
    node_type: Literal[NodeType.AREA_METRIC] = NodeType.AREA_METRIC
    area_code: str        # ONS GSS code
    area_type: Literal["lsoa", "ward", "la", "constituency", "ics"]
    metric_id: str
    value: float | None = None
    unit: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    national_average: float | None = None
    percentile: int | None = Field(default=None, ge=0, le=100)


class GeographyResolution(BaseModel):
    """
    Postcode -> all geographic levels.
    Used at query time to route jurisdiction and filter metrics.
    """
    postcode: str
    lsoa_code: str | None = None
    lsoa_name: str | None = None
    ward_code: str | None = None
    ward_name: str | None = None
    la_code: str | None = None
    la_name: str | None = None
    constituency_code: str | None = None
    constituency_name: str | None = None
    ics_code: str | None = None
    ics_name: str | None = None
    country: Literal["england", "wales", "scotland", "ni"] | None = None
