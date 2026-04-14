---
phase: 6
status: planned
source: BASIS_ROADMAP.md
---

### Phase 6: Outcome Intelligence

**Objective:** The graph learns from what works. Outcomes feed back into confidence scores; systemic failures surface to the right people.

**6.1 Outcome tracking and graph updates**

When a user records an outcome:
- `success` on a MECHANISM → success_rate increments, MECHANISM confidence edges strengthen
- `no_response` → response_rate decrements, may trigger escalation suggestion
- `escalated` → escalation edge strengthens
- `resolved_after_escalation` → first-level mechanism weakness flagged

Outcomes aggregate into mechanism-level stats:
```
ENV_HEALTH_COMPLAINT:
  attempts: 847
  resolved: 421 (49.7%)
  escalated: 312 (36.8%)
  no_response: 114 (13.5%)
  median_resolution_days: 34
  by_council: { Westminster: 61%, Slough: 31%, ... }
```

This data is uniquely valuable. No one else has it. It becomes: (a) a guide for citizens ("complaining to this council works less often — skip straight to ombudsman"), (b) a campaigning tool ("Slough council ignores 69% of housing complaints"), (c) an evidence base for systemic advocacy.

**6.2 Systemic signal surfacing**

- If ≥100 identical mechanism failures against same body in 6 months → flag as systemic failure pattern
- Generate evidence summary: dates, issue types, non-response rates
- Route to appropriate escalation: Housing Ombudsman systemic investigations, CQC thematic reviews, select committee evidence calls
- Auto-draft: systemic complaint letter to regulatory body, pre-populated with aggregate data

**6.3 Parliamentary and media bridge**

- Pattern detection → suggested parliamentary question (PQ) text
- Evidence package for select committee inquiry submissions
- Press release template for systemic findings
- FOI request batch: if pattern detected, auto-suggest coordinated FOI to surface hidden data
- Petition trigger: if issue is clearly systemic and widespread → petition text pre-drafted

**6.4 Policy feedback loop**

Outcomes connect back to the evidence layer:
- High resolution rate on a mechanism → SUPPORTS edge to relevant POLICY node
- Persistent failure rate → CONTRADICTS edge to policy claims about that body's effectiveness
- This is how the graph stays honest as the real world changes

---
