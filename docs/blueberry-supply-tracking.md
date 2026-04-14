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

## 4. What "should" be happening — minimum viable fix, still in Excel

Not proposing a system change. Proposing the smallest discipline shift that
closes the biggest holes while leaving the workflow familiar.

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

## 5. When to leave Excel

Excel + QuickBooks is genuinely fine up to roughly: <50 consignments/week,
<5 retailer customers on EDI, one-season programmes. Past that, the
industry moves to dedicated fresh-produce ERPs (Prophet, Linkfresh on D365,
Produce Pro, Silver Bullet, Aptean Produce). The trigger is usually the
first season where a retailer deduction gets missed and costs more than a
year of licence.

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
