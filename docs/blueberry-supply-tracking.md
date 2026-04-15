# Blueberry / foreign-fruit supply tracking — current vs. industry practice

Reference note for a UK importer/trader of foreign fruit (blueberries and
similar, sourced from Chile / South America), with a sister repacker
company that uses third-party pack houses. Sells to a mix of UK multiples
(Lidl via EDI — **configured but not in active use**), bulk sell-off
trade, wholesale, and foodservice. Currently Excel-based with QuickBooks
only at the accounting end.

---

## 1. Current state (as described)

- **Supplier lines sheet** — one row per grower line, target weight available.
  Comments hold the shipping number and a "present position by weight".
- **Weight → crate lookup** — conversion to haulier crate counts.
- **Net-missing calculation** — supplier weights vs. target, residual still
  to source.
- **Packing-document sheet** — per-PO supplier amounts, shipping details,
  port landing date. Populated from the packing list when the shipment is
  despatched.
- **Invoice** — linked to the PO via shipping number; carries all financial
  data. POs are internal-only (not sent to grower).
- **Price negotiation** — finalised post-shipment for settlement
  ("wally payment"; see TODO below).
- **Haulier and port fees** — held separately, plus an additional "hold up"
  line (see TODO below).
- **Consolidated sheet** — one big workbook stitching financial + PO +
  shipping detail together.
- **Mechanics** — copy-paste between tabs; one tab per PO; QuickBooks only
  receives the final financial summary.

**Confirmed definitions:**
- **"Wally payment"** — advance / early cash payment to the grower.
  Chilean and South American growers typically want cash up front, so
  the business pays early on agreed terms. The *final* price is
  renegotiated post-shipment once actual landed costs (including any
  port hold-up) are known. This is **not** consignment close-out and
  **not** Asda settlement; it is a prepaid-with-true-up arrangement.
- **"Hold up"** — consignment held up in port (lost orders, admin/system
  issues, clearance delays) causing additional freight, demurrage, or
  cold-store cost that arrives *after* the initial grower price has been
  agreed. These post-hoc costs feed back into the price renegotiation
  with the grower.
- **Early-assignment sheet** — programme baseline with rough amounts.
  On the retailer side the actuals flex (demand changes). On the grower
  side the constraint is supply: "max they can give" from what they can
  gather that week. Net-missing is therefore usually a *supply* gap, not
  a demand gap.
- **Sister repacker** — related-party business that repacks through
  third-party pack houses. Creates an intercompany cost/revenue layer
  that currently has to be reconciled by hand.
- **Lidl EDI** — the connection exists but isn't used; staff work from
  Excel orders received by email. See §3.
- **"PO" terminology** — internally called a PO, but functionally it's an
  **RFQ**: a provisional commitment to a grower whose price only firms up
  at post-shipment settlement (§2.5). Grower-side "POs" therefore carry a
  `pricing_status` of `provisional` until renegotiation closes it to
  `agreed`. Customer-side POs are firm. The doc uses "PO/RFQ" where the
  distinction matters.
- **Scale** — around 10–15 active growers. Small enough that every
  grower's data format can be solved individually rather than generally.

---

## 2. Industry-standard flow for a foreign-fruit importer/trader

The reference data model the trade uses, roughly upstream to downstream:

### 2.1 Commercial layer

| Entity | Purpose | Key fields |
|---|---|---|
| Grower / supplier | Master record | GGN, BRC/GlobalGAP status, payment terms, incoterms, currency |
| Programme / contract | Seasonal commitment with grower and (mirrored) with retailer | Variety, class, pack spec, weeks, weekly volume, price basis (fixed / MGP / consignment) |
| Customer | Master record | Retailer depot codes, GLN, EDI scheme (Tradacoms / EANCOM / GS1), pack code mapping |
| Sister repacker (intercompany) | Related party, books its own P&L | Intercompany transfer price, margin share policy, pack-house subcontract rates |
| Third-party pack house | Subcontractor to sister repacker | Site code, pack rates per variety/pack size, minimum charges |

### 2.2 Flow of a single shipment

```
Programme ──► Weekly early-assign ──► Pack declaration ──► Shipping docs
                                                              │
                                           ┌──────────────────┤
                                           ▼                  ▼
                                    Vessel / airfreight   Phyto + docs
                                           │                  │
                                           ▼                  │
                                    Port arrival ◄────────────┘
                                           │
                                           ▼
                                Customs clearance + duty
                                           │
                                           ▼
                                Haulier to depot / QC
                                           │
                                           ▼
                              Goods-in to retailer / wholesale / FS
                                           │
                                           ▼
                                 Sales invoice out (to customer)
                                           │
                                           ▼
                                 Grower settlement (self-billing)
```

### 2.3 The documents and the join keys

| Document | Source | Primary key | Links to |
|---|---|---|---|
| Programme line | Internal | programme_id + week + variety | Grower, customer |
| Early-assign (weekly plan) | Internal | programme_id + week | Programme |
| Packing list | Grower | consignment_no | Container / AWB |
| Commercial invoice (grower) | Grower | invoice_no | consignment_no, internal PO |
| Bill of lading / AWB | Shipping line / airline | B/L or AWB no | consignment_no |
| Phyto certificate | Origin authority | phyto_no | consignment_no |
| Customs entry | Clearing agent | MRN / entry no | B/L or AWB |
| Haulier docket | Haulier | job_no | B/L + delivery depot |
| QC report | Internal | consignment_no + batch | consignment_no |
| Sales order | Customer (EDI ORDERS or email) | customer_po | customer, delivery date |
| Despatch advice | Internal (EDI DESADV) | SSCC / ASN | sales_order |
| Sales invoice | Internal (EDI INVOIC) | invoice_no | sales_order, goods-in |
| Self-bill to grower | Internal | settlement_no | consignment_no, programme |

**The critical join keys that must never live only in a free-text comment:**
`consignment_no`, internal `PO_no`, grower `invoice_no`, `B/L` / `AWB`,
`customer_po`, `settlement_no`. Shipping number is typically `B/L` or `AWB`,
which in your current process is doing the job of all of these at once — fine
while volumes are small, breaks as soon as one consignment splits across
multiple customer POs, or one customer PO pulls from two consignments.

### 2.4 Landed-cost build-up (what the "big sheet" should compute per consignment)

```
Grower invoice value (FOB/CFR/CIF per incoterm)
+ Freight (if FOB)
+ Insurance (if FOB/CFR)
+ Duty + VAT (VAT usually reclaimable, held separately)
+ Port / THC / handling
+ Phyto inspection fee
+ Customs clearance fee
+ Demurrage / cold-store if delayed       ◄── "hold up"?
+ Haulage to depot
+ Repack labour + materials (if repacked)
+ QC / rejection write-off
= Landed cost per kg / per punnet
```

Margin per customer PO is then:
`sales_price_per_unit − (landed_cost_per_unit + customer-specific costs)`
where customer-specific costs include pallet fees, depot levies, promotional
funding, wastage, short-pay deductions.

### 2.5 Grower settlement — advance with post-shipment true-up

The pattern here is not consignment and not fixed-price. It's an advance
payment followed by renegotiation once actual costs are known:

```
Step 1 — At/before shipment:
    Advance payment to grower  (the "wally payment")
    Booked as: prepayment / grower advance (balance sheet)

Step 2 — Once consignment is landed and costs are in:
    Provisional landed cost per kg calculated per §2.4
    (includes any port hold-up costs that arrived after Step 1)

Step 3 — Price renegotiation with grower:
    Target margin vs. actual landed cost → agreed final grower price
    Final grower price × confirmed net weight = final grower value

Step 4 — Settlement:
    Final grower value
  − Advance already paid (from Step 1)
  = Top-up to grower   (or clawback / credit note if negative)
```

**Implications the current process doesn't handle well:**

- **Working capital.** Advances are a cash outflow before any customer
  invoice is raised. Need visibility of outstanding advances per grower
  at all times, not just at period end.
- **FX exposure.** Chilean / SA growers are typically USD-denominated.
  Advance paid at one FX rate, final settled at another. The FX gain/
  loss needs to land somewhere explicit, not hide inside "price
  negotiation".
- **Hold-up costs must be attributable.** If port demurrage on
  consignment X is used to justify a lower final grower price on
  consignment X, that cost-to-consignment link must be provable, not
  just an aggregate "extra freight this month" number. Otherwise the
  grower has a legitimate query.
- **Renegotiation audit trail.** The agreed final price, who signed it
  off, and on what landed-cost figure, needs to be recorded against the
  consignment — not just updated in place in a cell.

---

## 3. Where the current process breaks down

1. **Shipping number as universal join key.** Works for 1 consignment = 1
   PO = 1 invoice. Falls apart on splits/merges, mixed-grower containers,
   and part-deliveries.
2. **"Present position" and shipping number living in cell comments.**
   Comments are invisible to filters, pivots, lookups, and QuickBooks.
   Everything useful has to be promoted to a column.
3. **One tab per PO.** Non-scalable, no cross-PO analysis (week view,
   grower view, variety view all require re-copying). Any formula pointing
   into "the PO tab" is fragile.
4. **Copy-paste between sheets.** The single biggest source of reconciliation
   errors in produce businesses. Every copy-paste is a place the grower
   self-bill or retailer invoice can go wrong.
5. **No structured landed-cost build.** Haulier and port fees "held
   separately" means margin per PO is computed by eye or not at all.
6. **QuickBooks only at the end.** Fine for statutory accounts but means no
   running P&L per consignment, per grower, or per customer. In fruit, you
   want daily P&L because prices move daily.
7. **No link from early-assign forecast to actuals.** You can't see forecast
   accuracy per grower per week, which is the number that tells you whether
   to keep buying from them next season. The forecast-vs-actual gap is
   mostly a grower *supply* signal ("max they could gather"), not a demand
   signal — and that information is commercially valuable for next
   season's programme.
8. **Advance payments not tracked against consignments.** Wally/early
   payments are a working-capital item that should sit as an open
   balance per grower per consignment until settlement. Currently there
   is no per-consignment advance ledger, so exposure is not visible in
   real time and the true-up at renegotiation is done by memory.
9. **Hold-up costs not attributable.** Port delays hit after the initial
   grower price is agreed, and the additional freight/demurrage is used
   to justify a lower final price. Without a cost → consignment link,
   the grower cannot audit this and the business cannot defend it.
10. **FX exposure on grower advances is implicit.** USD advance paid at
    one rate, GBP settlement computed at another. The gain/loss hides
    inside "price negotiation" instead of being booked as FX.
11. **Lidl EDI configured but unused.** Orders come in by email and are
    worked off in Excel even though the EDI channel exists. This is a
    silent cost: UK multiples charge deductions for non-compliant
    invoicing, mis-keyed prices get short-paid, and ASN failures cause
    fine-lines. Either switch on the EDI that's already paid for, or
    decommission it and stop paying for it — but running both is the
    worst case.
12. **Intercompany with sister repacker.** Movements to/from the
    repacker and its third-party pack houses are part of the cost
    stack and need transfer-pricing discipline. Reconciled by hand,
    this is where HMRC and audit problems start.
13. **Retailer short-pays reconciled manually.** Retailers deduct (price
    query, wastage, late delivery, spec fail); without a deductions log
    you lose track of recoverable vs. final written-off.

---

## 4. Tactical fix — harden the current Excel (stepping stone)

Before proposing a system change. If a subscription tool is off the table
or the business wants to close gaps before switching, this is the minimum
discipline shift that closes the biggest holes while leaving the workflow
familiar. **This is not the ideal end-state (see §5) — it's the fallback
and the stepping stone.**

### 4.1 Flatten the data: rows, not tabs

Replace the per-PO tabs with a small number of long tables. Everything else
becomes pivots/filters on top.

| Table | Grain (one row = ) |
|---|---|
| `consignments` | one consignment (shipment) |
| `consignment_lines` | one grower line within a consignment (variety, class, pack, weight) |
| `customer_pos` | one line on one customer PO |
| `allocations` | one link from `consignment_lines` to `customer_pos` (many-to-many) |
| `costs` | one cost line (freight, duty, port, haulage, demurrage, repack) keyed by consignment; flag `timing = pre-negotiation` or `post-negotiation (hold-up)` |
| `sales_invoices` | one invoice line out |
| `grower_advances` | one wally/early payment, keyed by grower + consignment, with currency + FX rate at payment date; status open/settled |
| `grower_settlements` | one final settlement line — references `grower_advances` and computes top-up or clawback |
| `deductions` | one retailer deduction, status open/recovered/written-off |
| `intercompany` | one movement to/from sister repacker, with transfer-price basis |

The "big consolidated sheet" then becomes a pivot off these tables, not a
copy-paste artefact.

### 4.2 Promote comments to columns

Anything currently in a cell comment — shipping number, present position,
ETA, phyto status — is a column. Comments are for human notes only.

### 4.3 Landed-cost template, one per consignment

Fixed structure per the build-up in §2.4. Totals flow to the consolidated
sheet by `consignment_no`. No free-form cost lines.

### 4.4 Weekly close ritual

- Monday: grower self-bills for last week's closed consignments.
- Tuesday: reconcile customer remittances vs. invoices; log deductions.
- Wednesday: post week's landed costs + sales + settlements to QuickBooks
  via journal (or CSV import). One journal per week, not per PO.

### 4.5 EDI — decide, don't drift

The Lidl EDI channel exists but staff work off email/Excel. Pick one:

- **Switch it on properly.** Work out whether the gap is scope (EDI
  provider doesn't cover the specific document set Lidl sends), training
  (staff never learned the flow), or trust (past data errors made people
  revert to email). Fix the specific cause. Map Lidl's pack codes to
  internal SKUs once, not per order. ORDERS-in + DESADV-out + INVOIC-out
  is the standard triplet; make sure all three work.
- **Switch it off.** If the bureau contract is still being paid and the
  channel isn't used, cancel the contract. Don't run a dead channel.

Any other UK multiple added later will require EDI from day one — most
won't accept email orders at all and will charge deductions for non-EDI
invoices. Wholesale and foodservice on email is fine.

### 4.6 Intercompany with the sister repacker

Treat the repacker as an arm's-length customer/supplier for data
purposes, even though ownership is shared:

- Transfer price per pack operation, set once per season, not argued
  per consignment.
- Pack-house subcontract costs flow through the repacker's P&L, not
  back into the importer's cost stack directly.
- Monthly intercompany reconciliation — matched pairs of invoices with
  zero residual — before month-end close.
- For HMRC: transfer-pricing documentation if group turnover crosses
  the SME threshold (currently £50m group / 250 employees). Below that,
  arm's-length still applies but documentation burden is lighter.

### 4.7 Grower advance ledger + FX

Every wally/early payment:

- Booked as an asset (grower advance) against the specific consignment
  at the payment-date FX rate.
- Cleared to cost of sales at final settlement, with the FX difference
  booked to FX gain/loss — not absorbed into the negotiated price.
- Age report weekly: advances open > 60 days are a commercial and
  working-capital red flag.

### 4.8 The numbers that should exist live

1. **Net missing by week × variety** — formalised:
   `programme_target − confirmed_pack − in-transit − landed`.
   Flag whether the gap is supply (grower couldn't gather) or demand
   (retailer flexed down) — different commercial response.
2. **Landed cost per kg per consignment** — available the day haulage
   docket lands, split into pre-negotiation and post-negotiation
   (hold-up) so the grower renegotiation basis is auditable.
3. **Margin per customer PO** — sales line minus allocated landed cost
   minus known deductions. Provisional until deductions close.
4. **Open grower advances** — per grower, per consignment, per currency,
   aged. This is the working-capital number that's currently invisible.
5. **Retailer deductions log** — open vs. recovered vs. written-off, by
   reason code. Tells you whether to invest in fixing the root cause
   (e.g. ASN accuracy) or accept the cost.

---

## 5. The ideal system — simple, staff-editable, not Excel and not ERP

The honest answer to "what should it be" is: a **no-code relational
database with a spreadsheet-style UI**. Category examples: **Airtable,
SeaTable, Smartsheet, Stackby, NocoDB**. The specific tool matters less
than the category — pick one the business is comfortable paying for and
stick with it.

- **Recommended default: Airtable.** Strongest views, interfaces, and
  automations for this scale. Paid per user, reasonable at <20 seats.
- **If subscription is a hard no:** SeaTable or NocoDB, self-hosted.
  Same shape, more ops overhead.
- **Not recommended:** Notion databases (too weak on numeric rollups
  and relational enforcement), Google Sheets alone (the problem you
  already have), full fresh-produce ERP (too heavy — see §6).

### 5.1 Why this category

| Capability | Current Excel | No-code relational | Fresh-produce ERP |
|---|---|---|---|
| Staff edit by typing | ✅ | ✅ | ⚠ forms only |
| Real foreign keys / no stale copies | ❌ | ✅ | ✅ |
| Concurrent multi-user edit | ❌ | ✅ | ✅ |
| Audit trail / revision history | ❌ | ✅ | ✅ |
| One dataset, many views | ⚠ by tab | ✅ | ✅ |
| Automations (alerts, status flow) | ⚠ macros | ✅ | ✅ |
| Integrations (EDI, QB, FX) | ⚠ manual | ✅ via API | ✅ built-in |
| Time to first value | n/a | 4–8 weeks | 3–9 months |
| Annual cost (10 users) | "free" | £2–5k | £30k+ plus implementation |
| Staff training | familiar | hours | weeks |

### 5.2 The base — 12 tables, each with one job

Same structure as §4.1, now as a real relational base. Stable auto-IDs
behind the scenes; human-readable numbers (consignment_no, PO_no,
invoice_no) as regular fields.

| # | Table | Grain |
|---|---|---|
| 1 | `growers` | one grower; country, currency, incoterm, payment terms, cert status |
| 2 | `customers` | one customer; type, EDI scheme, GLN, depot codes, pack-code map |
| 3 | `programmes` | grower × variety × season; weekly target, price basis, pack spec |
| 4 | `purchase_orders` | grower-side PO/RFQ; programme link, expected qty, `pricing_status = provisional / agreed`, provisional price |
| 5 | `consignments` | one shipment; B/L, ETD, ETA, status, port (a PO can ship on 1–N consignments) |
| 6 | `consignment_lines` | one grower line within consignment; PO link, variety, class, pack, net kg |
| 7 | `customer_pos` | one customer PO line; channel (EDI / email), delivery date, status |
| 8 | `allocations` | link consignment_line → customer_po; qty, agreed price |
| 9 | `costs` | one cost line; type, amount, currency, **timing = pre- or post-negotiation (hold-up)** |
| 10 | `grower_advances` | one wally payment; currency, FX rate at date, status open/settled |
| 11 | `grower_settlements` | final price agreed; approver, linked advances, top-up/clawback, FX |
| 12 | `deductions` | one retailer deduction; reason code, status, age |
| 13 | `intercompany` | repacker / pack-house movement; transfer-price basis, reconciled |
| 14 | `intake_queue` | one pending item from any inbound stream; status open/posted/rejected |

"Simple" doesn't mean "few tables" — it means each table has one clear
job. Fourteen flat tables is much simpler than one workbook with 40 tabs.

### 5.3 Views — what each role opens in the morning

Same base, different lenses. No copy-paste between them.

- **Buyer** — programmes with net-missing by week × variety, flagged
  as supply (grower can't gather) or demand (retailer flexed).
- **Ops / shipping** — consignments in transit with ETA, doc status,
  hold-ups, customs.
- **Sales** — open customer POs, allocation coverage, shortfalls.
- **Finance (daily)** — open grower advances aged by currency;
  landed-cost-to-date per consignment; provisional margin per PO.
- **Finance (monthly)** — deductions pipeline, intercompany
  reconciliation, FX P&L, month-end journal draft.
- **Director dashboard** — programme vs. actual, advance exposure,
  margin by customer, deductions, FX position — one screen.

### 5.4 Interfaces — the actions that replace copy-paste

These are the **only** data-entry routes. No raw typing into base tables.

1. **New consignment** — picks grower + programme; auto-fills defaults.
2. **Load packing list** — paste or upload CSV from pack house;
   validates against the programme; creates consignment_lines rows.
3. **Log grower advance** — currency, amount, date; today's FX stamped.
4. **Add landed-cost line** — required fields include the
   pre-/post-negotiation flag.
5. **Renegotiate & settle grower** — screen shows landed cost, hold-up
   adjustments, advance balance; you set the final price; system posts
   top-up/clawback and FX gain/loss.
6. **Log retailer deduction** — invoice, reason, amount, status; stays
   open until recovered or written off.
7. **Intercompany movement** — to/from sister repacker with basis.
8. **Close month** — generates the QuickBooks journal CSV from costs,
   settlements, invoices, deductions, FX. Finance reviews before import.

### 5.5 Automations — the alerts that stop things slipping

- Advance open > 60 days → alert commercial lead.
- Hold-up cost added after grower price agreed → flag for price review.
- Customer PO on EDI-enabled customer entered via email route → warn.
- Landed cost updated → provisional margin recomputes automatically.
- Consignment status → `landed` → creates landed-cost review task.
- Deduction open > 30 days → escalate to finance.
- Programme week closes → auto-generate grower self-bill draft.

### 5.6 Integrations — deliberately thin

- **Email ingestion** for bulk-sell-off orders: inbox rule → parsed
  into a pre-filled customer-PO form for confirmation (don't auto-post).
- **Lidl EDI** — per §4.5, decide switch-on or decommission. If
  switch-on: ORDERS-in creates customer_pos rows; INVOIC-out fires
  from sales invoices.
- **QuickBooks Online** — one direction, not live. Monthly CSV journal
  reviewed then imported. Live sync with QBO almost always backfires
  for fruit businesses because of the post-shipment renegotiation loop.
- **FX rates** — daily pull from a public feed, stamped automatically
  on advance/settlement entries.
- **Explicitly out of scope**: payroll, HR, CRM/marketing, procurement
  catalogues, WMS. Keep the system small.

### 5.7 What the ideal system deliberately does NOT do

To stay simple:

- No forecasting beyond current programme + 4 weeks.
- No lot-level traceability below consignment (GGN recorded, not
  enforced per carton).
- No live accounting sync.
- No automated grower pricing — renegotiation is always human-approved.
- No customer portal, no grower portal — email is fine at this scale.
- No mobile app — spreadsheet-style UI is desktop-first.

### 5.8 Rollout — 6–8 weeks, parallel-run, not big-bang

1. **Week 1** — stand up the base with current growers, customers,
   programmes migrated by hand. Excel continues in parallel.
2. **Weeks 2–3** — all *new* consignments enter the system; old ones
   close out in Excel.
3. **Week 4** — advance ledger goes live; first post-shipment
   renegotiation runs through the system.
4. **Week 5** — deductions log replaces email threads and memory.
5. **Week 6** — first monthly close journal to QuickBooks generated
   from the system.
6. **Weeks 7–8** — retire the Excel big-sheet. Keep one read-only
   archive copy; don't keep editing it.

If any week the system isn't ready for a decision, fall back to Excel
for that decision only. Don't let partial parallel-run block the
switchover.

### 5.9 The ease-of-use test

If a new member of ops or sales cannot fill in "new consignment" and
read the net-missing view within 30 minutes of sitting down with no
training, the forms are too complex and need simplifying. The audience
is the person currently doing the copy-paste — if it's harder for them
than Excel, they will revert.

### 5.10 What this will cost roughly

- Airtable Team plan: ~£20/user/month × 10 users ≈ £2.5k/year.
- One-off build: 6–8 weeks of part-time attention from someone who
  knows the business, or 3–4 weeks of an external consultant day-rate.
  Deliberately avoid a heavy implementation project.
- Ongoing: finance or ops lead owns the base; small tweaks in-house,
  not via consultant.

Compare: ERP licence £15–30k/year + implementation £50–150k + 6 months
where nobody trusts the numbers. That's why the no-code step exists.

### 5.11 The inbound pipeline — how data actually gets into the base

Four streams arrive; all land in a single **intake queue** first, finance
reviews, then posts to base tables. Nothing affects landed cost, margin,
or the QuickBooks journal until it's been posted from the queue.

```
┌─────────────────────────┐       ┌──────────────┐      ┌─────────────┐
│ Grower packing list     │──────►│              │      │             │
│ (CSV / Excel by email)  │       │              │      │             │
├─────────────────────────┤       │              │      │             │
│ Grower invoice          │──────►│  INTAKE      │─────►│  BASE       │
│ (PDF by email)          │       │  QUEUE       │      │  TABLES     │
├─────────────────────────┤       │  (§5.2 #14)  │      │  (§5.2)     │
│ Customer order — EDI    │──────►│              │      │             │
│ (Lidl, if switched on)  │       │              │      │             │
├─────────────────────────┤       │              │      │             │
│ Customer order — CSV    │──────►│              │      │             │
│ (email from others)     │       │              │      │             │
└─────────────────────────┘       └──────────────┘      └─────────────┘
                                        ▲
                                        │
                                  Finance review:
                                  match to PO/RFQ,
                                  confirm, post
```

### 5.12 Stream by stream — 15 growers makes this tractable

With ~15 growers the effort of wiring each stream is bounded. You're not
solving a general problem, you're solving fifteen specific ones.

**Stream 1 — Grower packing list (easy, do this first)**

- Arrives as CSV or XLSX attached to an email, one per consignment.
- Most growers settle into one format once asked; ask them.
- Intake: Airtable email-to-record, or Make / Zapier / n8n watching a
  shared inbox, parsing the attachment into `intake_queue` rows.
- Match key: PO/RFQ number printed by the grower, or B/L / consignment
  reference. If no reference, match by grower + week + variety and let
  finance confirm.
- Review screen: *"GROW-07 packed 1,240 kg Duke against PO/RFQ
  RFQ-2024-103 — confirm and post?"* One click creates the
  `consignment_lines` rows.

**Stream 2 — Grower invoice (hard — de-scope honestly)**

Full invoice automation for 15 suppliers in 15 PDF formats isn't worth
building. Two honest options:

- **Human-assisted (recommended).** Finance opens the PDF, keys four
  fields into the intake form (grower, invoice_no, amount, currency),
  attaches the PDF. Airtable stores it, searchable. ~5 minutes per
  invoice; at 15 growers × a handful of shipments/week, tractable.
- **Per-grower parser, only where volume justifies it.** If one grower
  sends dozens of invoices a week, build a parser *just for them* with
  Parseur / Docparser / Nanonets (~£30–£100/month per grower). Don't
  try to cover all 15 with one generic parser.

**Critical point that makes invoices less scary here:** because the
final grower price is renegotiated at settlement (§2.5), the grower's
invoice is a **reference document, not the source of truth for cost.**
The source of truth is the final settlement agreed in Airtable. You
don't need invoice parsing to be perfect — just filed, searchable, and
matchable to the PO/RFQ.

**Stream 3 — Customer order, EDI (Lidl)**

- If EDI is switched on (§4.5 decision): bureau receives ORDERS, posts
  to Airtable via webhook, creates `intake_queue` row → one-click
  creates `customer_pos`.
- If decommissioned: treat Lidl orders like Stream 4.

**Stream 4 — Customer order, CSV by email (bulk sell-offs, wholesale, FS)**

- Mailbox watcher parses the CSV into `intake_queue`.
- For repeat customers, build a tiny per-customer column template
  (customer X's CSV has columns A–G in this order); once set, parsing
  is automatic.
- Review screen: *"CUST-W4 ordered 500 kg for Thursday — confirm
  customer, allocate to consignment, post?"*

### 5.13 The PO/RFQ as the link — packing ↔ PO ↔ customer order

This is the join the user called out: grower packing data links to the
original PO/RFQ, which then links to customer orders via allocations.

```
Programme
    │
    ▼
Purchase order / RFQ  (provisional price)  ◄── grower advance paid here
    │
    ├──► Consignment ──► Consignment lines  ◄── packing CSV posts here
    │                         │
    │                         ▼
    │                    Allocations ──────► Customer PO  ◄── EDI / CSV posts here
    │
    └──► Grower settlement (agreed price)  ──► closes the PO/RFQ

Finance review at every ◄── arrow.
```

Every row in `consignment_lines`, `customer_pos`, `costs`,
`grower_advances`, and `grower_settlements` carries the PO/RFQ reference.
That single field is the human-readable thread through the whole
record, replacing the shipping-number-in-a-comment approach.

### 5.14 The finance review queue — the single biggest control

One screen, one daily ritual. Probably the most important part of the
whole system because it's where discipline lives.

```
Intake queue — today
────────────────────────────────────────────────────────────────
 Type           │ From     │ Links to          │ Action
────────────────────────────────────────────────────────────────
 Packing list   │ GROW-07  │ PO/RFQ 2024-103   │ [Match & post]
 Grower invoice │ GROW-02  │ PO/RFQ 2024-098   │ [File]
 Customer PO    │ CUST-M1  │ EDI 445213        │ [Confirm & post]
 Customer PO    │ CUST-W4  │ email CSV 18 Apr  │ [Confirm & post]
 Packing list   │ GROW-11  │ (no match)        │ [Investigate]
```

Properties:

- Until actioned, items don't update landed cost, margin, or the QB
  journal. This is what replaces the copy-paste discipline — posting
  is no more effort than copy-paste was.
- "No match" cases go in the same queue, flagged — they're the signal
  that a grower referenced a PO/RFQ that doesn't exist yet (wrong
  number, or they've shipped off-programme).
- Audit trail is automatic: Airtable records who posted which row
  when, and the original intake row is preserved.
- Finance owns the queue, but the UI is simple enough that ops can
  pre-match ("this packing list is for PO RFQ-2024-103"), leaving
  finance to just confirm and post.

### 5.15 What to build in week 1

Given the small supplier base, the fastest useful version is:

1. `growers`, `customers`, `programmes`, `purchase_orders` — manual
   entry, one-time, ~half a day.
2. **Stream 1 pipeline** (packing lists) + intake queue + "match & post"
   interface. This alone replaces most of the copy-paste.
3. A `landed_cost` view per PO/RFQ computed from `costs` (manual entry
   at first) + a provisional margin field.
4. `grower_advances` + "renegotiate & settle" interface — so the true-up
   loop closes inside the system from day one.

Streams 2–4 (invoice filing, EDI, customer CSV parsing) can follow in
weeks 2–4. Don't block the week-1 launch on them.

---

## 6. When even this isn't enough

Excel + QuickBooks is fine up to roughly <10 consignments/week and no
EDI. The no-code relational system in §5 comfortably handles roughly
50 consignments/week, 5–10 retailer customers, one or two seasons'
programmes, <20 users. Past that, the industry moves to dedicated
fresh-produce ERPs (Prophet, Linkfresh on D365, Produce Pro, Silver
Bullet, Aptean Produce). The usual trigger is the first season where a
retailer deduction gets missed and the cost exceeds a year of licence
— or when a new retailer requires full EDI + traceability that
Airtable-style tools can't deliver without duct tape.

---

## Open questions to resolve before this note is final

- Volumes: consignments per week, growers, customers on EDI — determines
  whether §5 trigger is already hit.
- Incoterms used with growers (FOB / CFR / CIF / DAP) — determines which
  cost lines are yours vs. theirs.
- Grower currency mix (USD for Chilean / SA assumed) and whether the
  business hedges FX or takes the spot risk.
- Why Lidl EDI isn't in use: missing document coverage, staff training,
  or historical data-quality problems. Determines fix vs. decommission.
- Sister repacker — shared ownership vs. contractual related-party.
  Determines transfer-pricing regime.
- Typical size of the post-negotiation adjustment (hold-up costs as %
  of grower price). If material and recurring, there's a hedging /
  cost-smoothing conversation to have with growers.
