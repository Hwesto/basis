---
phase: audit
status: planned
source: BASIS_ROADMAP.md
---

### Legislation Accountability Audit (schedulable after Phase 2b)

**What it is:** A standalone deliverable — no new schema, no new pipeline — that answers the question nobody has answered systematically: did major legislation achieve what it said it would?

Explanatory notes in Lex Graph record what Parliament was told each Act would do. The evidence layer records what actually happened. The gap between the two is computable with existing infrastructure.

**Why it comes here:** It's the first real proof that the Lex integration works in practice before committing to the full Phase 4 build. It generates press and select committee attention before the local data layer exists. It demonstrates the platform's core claim — that policy assertions can be checked against evidence — in the most concrete form possible.

**Acts to start with (priority order):**

| Act | Year | What was promised | Outcome data available |
|---|---|---|---|
| Water Act | 1989 | Privatisation would drive investment and efficiency | Ofwat performance data, sewage spill records, price indices |
| NHS & Community Care Act | 1990 | Internal market would improve efficiency and patient choice | NHS waiting times, satisfaction data |
| Housing Act | 1988 | Deregulation would increase supply and improve conditions | DLUHC housing supply, EHS conditions data |
| Welfare Reform Act | 2012 | UC would simplify the system and increase work incentives | DWP UC data, employment outcomes, food bank data |
| Health and Social Care Act | 2012 | Clinical commissioning would improve outcomes and reduce costs | NHS outcomes data, administrative cost data |
| Housing and Planning Act | 2016 | Starter Homes and Right to Buy extension would increase ownership | DLUHC ownership data, Starter Homes delivery |
| Environment Act | 2021 | Legally binding targets would restore nature | ONS natural capital, EA water quality |

**What the output looks like:** For each Act, a structured comparison: stated predictions from the explanatory note, measured outcomes from the evidence layer, verdict (achieved / partially achieved / not achieved / too early to tell), confidence score on the verdict, and sources.

Presented on the platform as a dedicated section. Each Act generates a shareable card. The aggregate scorecard — "of the last 40 years of major legislation, here is how often Parliament's stated intentions were achieved" — is the headline.

**What it needs:** Lex API calls for explanatory notes (available now). Evidence nodes already in the graph for most domains. Gap-filling via targeted source fetch where outcome data is missing. Claude Code sessions for structured comparison. No new schema. No new tables. No new pipeline.

**Estimated effort:** 2–4 weeks depending on source gaps. Schedulable as soon as Phase 2b is deployed. Does not block Phase 3.

---
