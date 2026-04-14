# Blueberry / foreign-fruit supply tracking — current vs. industry practice

Reference note for a UK importer/trader of foreign fruit (blueberries and
similar), selling to a mix of UK multiples (EDI), wholesale markets, and
foodservice/processors. Currently Excel-based with QuickBooks only at the
accounting end.

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

**TODO to confirm:**
- "Wally payment" — Asda/Walmart settlement terms, or grower final
  settlement on consignment close-out? The doc below assumes the latter
  where it matters; correct me if wrong.
- "Hold up" — retailer short-pay/deduction, or port demurrage/cold-store?
  Treated as landed-cost adjustment below.
- Early-assignment sheet: forecast only, firm allocation to customer POs,
  or programme baseline with weekly flex? Treated as programme + weekly
  flex below (most common pattern for imported soft fruit).

---

## 2. Industry-standard flow for a foreign-fruit importer/trader

The reference data model the trade uses, roughly upstream to downstream:

### 2.1 Commercial layer

| Entity | Purpose | Key fields |
|---|---|---|
| Grower / supplier | Master record | GGN, BRC/GlobalGAP status, payment terms, incoterms, currency |
| Programme / contract | Seasonal commitment with grower and (mirrored) with retailer | Variety, class, pack spec, weeks, weekly volume, price basis (fixed / MGP / consignment) |
| Customer | Master record | Retailer depot codes, GLN, EDI scheme (Tradacoms / EANCOM / GS1), pack code mapping |

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

### 2.5 Grower settlement (consignment or MGP)

For consignment growers the final payment isn't known until sale:

```
Gross sales proceeds
− Freight, duty, port, haulage (landed costs)
− Agreed commission %
− Repack / QC write-off (if for grower account)
= Net remittance to grower (self-billing invoice)
```

This is typically what "negotiate price for settlement" means in a foreign
fruit business — it isn't really a negotiation, it's a reconciliation the
grower can query. The honesty of the numbers matters; this is where
importers get a reputation.

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
   to keep buying from them next season.
8. **"Hold up" and short-pays reconciled manually.** Retailers deduct (price
   query, wastage, late delivery, spec fail); without a deductions log you
   lose track of recoverable vs. final.

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
| `costs` | one cost line (freight, duty, port, haulage, demurrage, repack) keyed by consignment |
| `sales_invoices` | one invoice line out |
| `grower_settlements` | one self-bill line in |
| `deductions` | one retailer deduction, status open/recovered/written-off |

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

### 4.5 EDI for the retailers that require it

For the UK multiples portion: you almost certainly need ORDERS-in and
INVOIC-out via a bureau (e.g. TrueCommerce, OpenText, Data Interchange).
Most multiples will charge deductions for non-EDI invoices. Keep wholesale
and foodservice on email/phone — fine as is.

### 4.6 The three numbers that should exist live

1. **Net missing by week × variety** — what you already track, formalised:
   `programme_target − confirmed_pack − in-transit − landed`.
2. **Landed cost per kg per consignment** — available the day haulage docket
   lands, not weeks later.
3. **Margin per customer PO** — sales line minus allocated landed cost
   minus known deductions. Provisional until deductions close.

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

- Confirm "wally payment" definition (see §1 TODO).
- Confirm "hold up" definition (see §1 TODO).
- Confirm early-assignment commitment level (see §1 TODO).
- Volumes: consignments per week, growers, customers on EDI — determines
  whether §5 trigger is already hit.
- Incoterms used with growers (FOB / CFR / CIF / DAP) — determines which
  cost lines are yours vs. theirs.
- Currency mix and who carries FX risk.
