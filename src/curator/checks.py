"""
checks.py — individual Tier 1 check functions.

Each check returns either None (pass) or a `CheckFailure` (fail with
reason). Pure: no side effects, no I/O. Run by run_tier1_checks() in
order; first failure short-circuits.

Adding a new check:
- Implement a function with the signature `(node, source) -> CheckFailure | None`
- Append to CHECK_PIPELINE in run_tier1_checks
- Add a fixture to tests/curator/test_routing.py
- Note the addition in SCHEMA-024 + status.md
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Iterable

# Reuse the existing boilerplate detector from base_schema rather than
# duplicating it. The blocklist lives there because the EvidenceEdge
# Pydantic validator already uses it; we want one source of truth.
from base_schema import _BLOCKLIST_PATTERN  # type: ignore[attr-defined]


@dataclass
class CheckFailure:
    """A specific Tier 1 gate said no, with a reason for the audit log."""
    check_name: str
    reason: str


# ---------------------------------------------------------------------------
# Adversarial pattern detection
# ---------------------------------------------------------------------------
# Conservative initial set per SCHEMA-024 §"Tier 1 hard-fail patterns".
# False positives are Tier 3 escalations, not data loss — we'd rather
# escalate a paper that quotes a prompt template than auto-approve a
# poisoned source. Extend when real adversarial samples surface.

ADVERSARIAL_PATTERNS: list[str] = [
    r"<\s*system\s*>",
    r"<\s*/\s*system\s*>",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"ignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions?",
    r"disregard\s+(?:all\s+|any\s+)?(?:the\s+)?above",
    r"^\s*system\s*:",
]
_ADVERSARIAL_RE = re.compile(
    "|".join(ADVERSARIAL_PATTERNS), re.IGNORECASE | re.MULTILINE
)

# Bidi / zero-width unicode tricks — anything containing these in the
# extraction content is suspicious enough to escalate.
_ZW_RE = re.compile(r"[\u200b\u200c\u200d\u200e\u200f\u202a-\u202e\u2066-\u2069]")


def check_adversarial_patterns(node: dict, source: dict) -> CheckFailure | None:
    """SCHEMA-024 Tier 1 — prompt-injection / unicode-trick detection.

    Checks the source full_text and any node free-text fields. Operates
    only on text we actually fed to the LLM, so a malicious source
    quoted by accident in a citation_locator wouldn't trip it.
    """
    haystacks: list[tuple[str, str]] = []
    if isinstance(source, dict):
        if source.get("full_text"):
            haystacks.append(("source.full_text", source["full_text"]))
    for field in ("statement", "extraction_notes", "falsification_condition"):
        v = node.get(field)
        if isinstance(v, str):
            haystacks.append((f"node.{field}", v))

    for label, text in haystacks:
        if _ADVERSARIAL_RE.search(text):
            return CheckFailure(
                check_name="adversarial_pattern",
                reason=(
                    f"Adversarial-pattern regex matched in {label}. "
                    "Source or extraction may be attempting prompt injection."
                ),
            )
        # Only flag unicode tricks in source text (legitimate quotes in
        # node fields are rare and routinely use bidi marks).
        if label.startswith("source.") and _ZW_RE.search(text):
            return CheckFailure(
                check_name="adversarial_pattern",
                reason=(
                    f"Suspicious zero-width / bidi unicode in {label}. "
                    "Could be a homoglyph attack — escalate."
                ),
            )
    return None


# ---------------------------------------------------------------------------
# Boilerplate detection
# ---------------------------------------------------------------------------

def check_boilerplate_explanation(node: dict, source: dict) -> CheckFailure | None:
    """SCHEMA-017 — explanation / falsification text not boilerplate.

    Reuses the existing EXPLANATION_BLOCKLIST from base_schema.py.
    Applied to: edge `explanation` (if this is an edge payload) and
    `falsification_condition` on ASSUMPTION nodes (SCHEMA-013).
    """
    candidates: list[tuple[str, str]] = []
    for field in ("explanation", "falsification_condition"):
        v = node.get(field)
        if isinstance(v, str) and v.strip():
            candidates.append((field, v.strip()))

    for field, text in candidates:
        if _BLOCKLIST_PATTERN.match(text):
            return CheckFailure(
                check_name="boilerplate_explanation",
                reason=(
                    f"Field {field!r} is boilerplate ({text!r}). "
                    "Per SCHEMA-017 it must describe the specific relationship."
                ),
            )
    return None


# ---------------------------------------------------------------------------
# Source quality floor
# ---------------------------------------------------------------------------

def check_source_quality_floor(node: dict, source: dict) -> CheckFailure | None:
    """SCHEMA-024 Tier 1 — source quality floor.

    Cases that always escalate to Tier 3 because Claude shouldn't
    auto-approve from low-provenance material:
      - TESTIMONY source with tier T5 (citizen-level, no corroboration)
      - DERIVED source with any input_node_id that isn't itself
        curator_approved (tracked via the source's own state; if the
        flag isn't on the source we conservatively escalate)
    """
    if not isinstance(source, dict):
        return None

    source_type = source.get("source_type")

    if source_type == "TESTIMONY":
        tier = source.get("tier") or source.get("default_tier")
        if tier == "T5":
            return CheckFailure(
                check_name="source_quality_floor",
                reason="TESTIMONY T5 (citizen) cannot auto-approve.",
            )

    if source_type == "DERIVED":
        # The DerivedSource model lists input_node_ids; if any of them
        # is unknown (no inputs_curator_approved flag set true) we
        # escalate. The check is conservative — present a positive
        # signal or escalate.
        if not source.get("inputs_curator_approved", False):
            return CheckFailure(
                check_name="source_quality_floor",
                reason=(
                    "DERIVED source must have all input_node_ids "
                    "curator-approved (inputs_curator_approved=true)."
                ),
            )

    return None


# ---------------------------------------------------------------------------
# Required-field presence (SCHEMA-013)
# ---------------------------------------------------------------------------

def check_fact_has_source(node: dict, source: dict) -> CheckFailure | None:
    """FACT nodes must have a source_id (SCHEMA-013)."""
    if node.get("node_type") == "FACT" and not node.get("source_id"):
        return CheckFailure(
            check_name="fact_has_source",
            reason="FACT node requires a source_id (SCHEMA-013).",
        )
    return None


# ---------------------------------------------------------------------------
# Flash cross-check result handling
# ---------------------------------------------------------------------------

def check_flash_cross_check(node: dict, source: dict) -> CheckFailure | None:
    """SCHEMA-024 Tier 1 — Flash cross-check result.

    Reads the `flash_check_result` field (set by the extraction
    pipeline). 'fail' → escalate as model_disagreement. Other values
    pass at this stage.
    """
    result = node.get("flash_check_result")
    if result == "fail":
        return CheckFailure(
            check_name="flash_cross_check",
            reason=(
                f"Gemini Flash cross-check failed: "
                f"{node.get('flash_check_note', '(no note)')}"
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

CHECK_PIPELINE: list[Callable[[dict, dict], CheckFailure | None]] = [
    check_fact_has_source,
    check_boilerplate_explanation,
    check_adversarial_patterns,
    check_source_quality_floor,
    check_flash_cross_check,
]


def run_tier1_checks(
    node: dict,
    source: dict,
    pipeline: Iterable[Callable[[dict, dict], CheckFailure | None]] = (),
) -> CheckFailure | None:
    """Run Tier 1 checks in order. Return first failure, or None on full pass.

    `pipeline` arg lets tests inject a subset; defaults to CHECK_PIPELINE.
    """
    checks = list(pipeline) if pipeline else CHECK_PIPELINE
    for check in checks:
        failure = check(node, source)
        if failure is not None:
            return failure
    return None
