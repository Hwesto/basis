"""
agents.py — Agent definitions for continuous extraction (Phase 8).

Four extraction agents on schedule:
  1. Legal Extraction Agent (daily, Gemma + Flash)
  2. Structural Signals Agent (daily, no LLM, pure graph traversal)
  3. Legal Validation Agent (on-demand, Claude via Supabase MCP + Lex MCP)
  4. Evidence Agent (per-release, Gemma + Flash)
  5. Parliamentary Agent (daily, parliament-mcp)
  6. Local Data Agent (per-source cadence)

Each agent run is logged to extraction_runs table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentType(str, Enum):
    LEGAL_EXTRACTION = "legal_extraction"
    STRUCTURAL_SIGNALS = "structural_signals"
    LEGAL_VALIDATION = "legal_validation"
    EVIDENCE = "evidence"
    PARLIAMENTARY = "parliamentary"
    LOCAL_DATA = "local_data"


@dataclass
class AgentConfig:
    """Configuration for an extraction agent."""
    agent_type: AgentType
    schedule: str  # cron expression or 'on_demand'
    model: str | None  # 'gemma_4_26b', 'gemini_flash', 'claude', None
    description: str
    enabled: bool = True
    max_items_per_run: int = 100
    retry_on_failure: bool = True
    max_retries: int = 3


@dataclass
class AgentRun:
    """A single agent execution, logged to agent_log table."""
    agent_type: str
    run_id: str
    started_at: str = ""
    completed_at: str | None = None
    input_count: int = 0
    output_count: int = 0
    error_count: int = 0
    model_version: str | None = None
    input_hashes: list[str] = field(default_factory=list)
    notes: str | None = None

    def start(self):
        self.started_at = datetime.now(timezone.utc).isoformat()

    def complete(self, output_count: int, error_count: int = 0):
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.output_count = output_count
        self.error_count = error_count

    def to_dict(self) -> dict:
        return {
            "agent_type": self.agent_type,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "error_count": self.error_count,
            "model_version": self.model_version,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Agent configurations
# ---------------------------------------------------------------------------

AGENTS: dict[str, AgentConfig] = {
    "legal_extraction": AgentConfig(
        agent_type=AgentType.LEGAL_EXTRACTION,
        schedule="0 4 * * *",  # daily 04:00 UTC
        model="gemma_4_26b",
        description=(
            "Watches lex_provisions for content_hash changes. "
            "Extracts legal nodes via Gemma with Pydantic schema constraint. "
            "Cross-checks via Gemini Flash. "
            "Commencement gate blocks not_commenced/repealed. "
            "Output: curator_queue rows."
        ),
        max_items_per_run=50,  # within Gemma free tier (1K req/day)
    ),

    "structural_signals": AgentConfig(
        agent_type=AgentType.STRUCTURAL_SIGNALS,
        schedule="0 3 * * *",  # daily 03:00 UTC, before legal extraction
        model=None,  # no LLM, pure graph traversal
        description=(
            "Refreshes in_degree, amendment_count, commencement_status, "
            "structural_stability on watched provisions. "
            "Triggers re-extraction if stability drops. "
            "No LLM cost."
        ),
        max_items_per_run=500,
    ),

    "legal_validation": AgentConfig(
        agent_type=AgentType.LEGAL_VALIDATION,
        schedule="on_demand",  # triggered by curator queue backlog
        model="claude",
        description=(
            "Claude Code session via Supabase MCP + Lex MCP. "
            "Reads curator_queue batch, pulls original provision text, "
            "judges: approve / reject / escalate. "
            "Sampled review: flagged items + random 20% of passed items. "
            "Cost: existing Max plan."
        ),
        max_items_per_run=30,  # per Claude Code session
    ),

    "evidence": AgentConfig(
        agent_type=AgentType.EVIDENCE,
        schedule="0 5 * * 1",  # weekly Monday 05:00 UTC
        model="gemma_4_26b",
        description=(
            "Monitors ONS/DWP/NHS release calendars. "
            "Extracts FACT/ASSUMPTION nodes from new statistical releases. "
            "Creates StructuredDataSource and DocumentarySource records. "
            "Triggers MC re-propagation."
        ),
        max_items_per_run=100,
    ),

    "parliamentary": AgentConfig(
        agent_type=AgentType.PARLIAMENTARY,
        schedule="0 6 * * *",  # daily 06:00 UTC
        model=None,  # uses parliament-mcp directly
        description=(
            "Monitors parliament-mcp (i.AI) for: "
            "new bills, Hansard POSITION nodes, committee reports. "
            "Creates TestimonySource records. "
            "Bill tracking for amendment-watch provisions."
        ),
        max_items_per_run=200,
    ),

    "local_data": AgentConfig(
        agent_type=AgentType.LOCAL_DATA,
        schedule="0 2 * * *",  # daily 02:00 UTC
        model=None,
        description=(
            "Per-source cadence refresh of area_metrics. "
            "Incremental upsert (new period rows, no history overwrite). "
            "Change detection: >10% movement flagged for review. "
            "Percentile recomputation on each refresh."
        ),
        max_items_per_run=1000,
    ),
}


# ---------------------------------------------------------------------------
# Agent SQL for logging
# ---------------------------------------------------------------------------

AGENT_LOG_SQL = """
CREATE TABLE IF NOT EXISTS agent_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_type TEXT NOT NULL,
    run_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    input_count INTEGER DEFAULT 0,
    output_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    model_version TEXT,
    input_hashes TEXT[],
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_agent_log_type ON agent_log (agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_log_started ON agent_log (started_at DESC);
"""
