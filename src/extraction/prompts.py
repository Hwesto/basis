"""
prompts.py — Prompt templates for the extraction pipeline.

Gemma 4 26B MoE: Pydantic-constrained extraction (response_schema = LegalNode)
Gemini Flash: Cross-check (~$0.001/check)
Haiku: Explanatory note validation (~1p/check)
"""

# ---------------------------------------------------------------------------
# Gemma: Legal node extraction
# ---------------------------------------------------------------------------

GEMMA_LEGAL_EXTRACTION = """You are extracting structured legal information from UK legislation.

Given a provision from a UK statute, extract all legal positions (rights, duties, powers, liabilities, privileges, immunities) that the provision creates.

For each legal position, provide:
- node_type: one of RIGHT, DUTY, POWER, LIABILITY, PRIVILEGE, IMMUNITY, MECHANISM, EVIDENCE_REQUIREMENT, ESCALATION_PATH
- statement: plain English description of what this provision does, in one sentence
- applies_to: who benefits from or is subject to this (e.g. ['tenant', 'homeowner', 'local_authority'])
- duty_holder: who bears the obligation (if applicable)
- duty_holder_type: one of local_authority, private_landlord, public_body, employer, individual
- deontic_strength: ABSOLUTE (must), QUALIFIED (must unless), CONDITIONAL (must if), DIRECTORY (should), ASPIRATIONAL (aim to)
- confidence: HIGH if the provision clearly creates this position, MEDIUM if interpretation required, LOW if uncertain

IMPORTANT:
- Extract what the provision ACTUALLY says, not what you think it should say
- A POWER is different from a DUTY: "may" creates a power, "must" creates a duty
- If the provision creates both a right and its correlative duty, extract both
- Note enforcement gaps: if a duty has no mechanism, say so in extraction_notes

PROVISION TEXT:
{provision_text}

EXPLANATORY NOTE (if available):
{explanatory_note}

PROVISION ID: {lex_provision_id}
DOMAIN: {domain}
JURISDICTION: {jurisdiction}
"""

# ---------------------------------------------------------------------------
# Gemini Flash: Cross-check
# ---------------------------------------------------------------------------

FLASH_CROSS_CHECK = """You are verifying an automated extraction against its source text.

PROVISION TEXT:
{provision_text}

EXPLANATORY NOTE:
{explanatory_note}

EXTRACTED DATA:
{extracted_json}

Does this extraction accurately represent what the provision says?

Check:
1. Is the node_type correct? (e.g. "may" = POWER not DUTY)
2. Does the statement accurately describe the provision's effect?
3. Are applies_to and duty_holder correct?
4. Is the deontic_strength appropriate?

Respond with EXACTLY one of:
PASS - extraction is accurate
FAIL: [specific reason why it's wrong]
"""

# ---------------------------------------------------------------------------
# Haiku: Explanatory note validation (1p/check)
# ---------------------------------------------------------------------------

HAIKU_NOTE_VALIDATION = """Compare this extraction against the explanatory note for the provision.

EXPLANATORY NOTE:
{explanatory_note}

EXTRACTION:
{extracted_json}

Does the extraction match what the explanatory note says the provision does?

Respond PASS or FAIL: [reason].
"""

# ---------------------------------------------------------------------------
# Gemma: Evidence node extraction (Phase 1/2 pattern)
# ---------------------------------------------------------------------------

GEMMA_EVIDENCE_EXTRACTION = """You are extracting structured evidence from a document about UK public policy.

Given a passage from a document, extract factual claims and assumptions.

FACT: A statement directly supported by data or observation in the source.
- Must include the specific figure, date, or observation
- source_loc must identify where in the document this comes from

ASSUMPTION: An interpretive or causal claim that goes beyond what the data directly shows.
- Must list which facts it rests on (basis_fact_ids)
- Must include a falsification_condition: what would disprove this

For fiscal claims, include:
- amount (numeric)
- unit: bn_gbp, m_gbp, or pct_gdp
- gap_role: additional_need, baseline, position_only, summary, uplift, or target_total
- direction: spending, revenue, or net

SOURCE DOCUMENT:
Title: {title}
Tier: {tier}
Publisher: {publisher}

PASSAGE:
{passage}

DOMAIN: {domain}
"""

# ---------------------------------------------------------------------------
# Node type classification (Haiku, cheap)
# ---------------------------------------------------------------------------

HAIKU_CLASSIFY_NODE_TYPE = """Given this source, what types of BaseNode subclasses should be extracted?

Source type: {source_type}
Title/description: {title}
Domain: {domain}

Respond with a JSON list of node types to extract. Options:
FACT, ASSUMPTION, CLAIM, POLICY, POSITION, RIGHT, DUTY, POWER, LIABILITY,
PRIVILEGE, IMMUNITY, MECHANISM, EVIDENCE_REQUIREMENT, ESCALATION_PATH, PRECEDENT

Example: ["FACT", "ASSUMPTION", "CLAIM"]
"""
