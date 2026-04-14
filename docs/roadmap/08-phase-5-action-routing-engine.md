---
phase: 5
status: planned
source: BASIS_ROADMAP.md
---

### Phase 5: Action Routing Engine

**Objective:** For any issue a citizen identifies, route them through the correct escalation pathway with pre-populated templates.

**Curator routing for action-layer nodes (per SCHEMA-024):**

- **TEMPLATE nodes are solicitor-only.** Templates are the documents
  citizens send to councils, ombudsmen, courts. Wrong wording can
  damage a real case. They never reach `verification_level=human_curated`
  without `solicitor_signed_off=true` (already on the schema at
  `src/action_schema.py:62`). This is a stricter form of Tier 3 — a
  generic human approval is not enough.
- **MECHANISM nodes** route through normal three-tier flow.
- **OUTCOME nodes** from citizen submissions (Phase 6) are
  user-submitted and route to Tier 3 by default — they can't be
  trusted at face value because the submitter has an incentive to
  report a particular result.
- **SUBMISSION nodes** are operational records, not knowledge — they
  bypass the curator queue entirely and write directly to
  `citizen_actions`.

The solicitor-sign-off rate is the rate-limiter on this phase. Plan
the template authoring pipeline (council, MP, ombudsman, FOI, EIR,
pre-action protocol, tribunal applications) around realistic legal
review throughput — likely 5–10 templates per week, not per day.

**5.1 Routing logic**

The escalation tree is itself part of the knowledge graph. A MECHANISM node carries:

```json
{
  "mechanism_id": "ENV_HEALTH_COMPLAINT",
  "name": "Environmental Health complaint to council",
  "applicable_issues": ["housing_disrepair", "mould", "pests", "noise"],
  "applicable_to": ["tenant", "homeowner"],
  "jurisdiction": ["england", "wales"],
  "prerequisite_ids": [],
  "statutory_response_window_days": 21,
  "template_id": "TPL-ENV-HEALTH-001",
  "evidence_required": ["photographs", "correspondence_log", "dates_reported"],
  "success_rate": null,             -- populated from outcomes
  "escalates_to": ["HOUSING_OMBUDSMAN", "DISREPAIR_CLAIM"],
  "escalation_trigger": "no_response_21_days | unsatisfactory_response"
}
```

Routing algorithm:
1. User describes issue (free text + structured questions)
2. Issue classifier → domain + issue_type + tenure_type + jurisdiction
3. Graph traversal from issue_type → applicable RIGHT nodes → available MECHANISMs
4. Filter by jurisdiction, tenure, prerequisites met
5. Rank mechanisms by: success_rate (if known) → statutory strength → effort level
6. Present ordered pathway to user with explanation of each step

**5.2 Template engine**

Templates are structured documents with named slots. Slots are populated from:
- User's personal data (name, address — stored locally, never on server unless consented)
- Local data layer (postcode → council name, MP name, relevant local metric)
- Legal layer (relevant statute, section reference, regulatory body name)
- Evidence layer (confidence-weighted supporting facts)

Template types:
- Council complaint letter (HTML → PDF)
- MP constituency letter
- Ombudsman complaint form (pre-fills where possible)
- FOI request letter
- EIR request letter
- Pre-action protocol letter (housing disrepair)
- Letter Before Action (general)
- Tribunal application grounds
- Public inquiry submission
- Parliamentary petition text

**5.3 Contact resolution**

- MP lookup: postcode → constituency (ONS) → TheyWorkForYou API → email + surgery times
- Council lookup: postcode → LA (ONS) → council website scrape → complaint portal URL
- Regulatory body lookup: issue_type → REGULATORY_BODY node → contact details
- Legal aid: postcode → Civil Legal Advice regional directory

**5.4 Action tracking**

```sql
CREATE TABLE citizen_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  issue_type TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,
  mechanism_id TEXT NOT NULL,
  template_id TEXT,
  submitted_at TIMESTAMPTZ,
  response_deadline TIMESTAMPTZ,
  outcome TEXT CHECK (outcome IN ('resolved', 'escalated', 'withdrawn', 'pending', 'no_response')),
  outcome_recorded_at TIMESTAMPTZ,
  escalated_to TEXT,                -- mechanism_id of next step if escalated
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

User-facing: a simple "my actions" timeline showing what was sent, when a response is due, and what to do next if nothing happens.

**5.5 Collective action detection**

- Daily aggregation: group actions by (mechanism_id, area_code, issue_type)
- If ≥10 people in same ward with same issue in 30 days → "You're not alone" notification
- If ≥50 → suggest coordinated response (joint letter, group FOI, collective legal action)
- Aggregate data (never individual) shared as public stats: "237 housing complaints in [council] in the last 6 months"
- Group action routing: CrowdJustice referral, CLAiT collective legal action, media briefing pack

**Success metrics:** ≥10 escalation trees built and tested, ≥3 template types live, contact resolution working for all 650 constituencies.

---
