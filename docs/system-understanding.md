# Tenga Inventory — System Understanding Summary

A plain-language explanation of what Tenga Inventory is, why it exists, and how it works.

---

## What is Tenga Inventory?

Tenga Inventory is a lightweight, focused inventory management system. It answers three core questions:

1. **What do we have?** — Product names, quantities, and types.
2. **Where is it?** — Physical locations (shelves, departments, storerooms).
3. **What happened to it?** — Complete audit trail of every change.

That's it. No sales, no invoices, no accounting. Just inventory.

---

## Why does it exist?

Most inventory systems force you to adopt an entire suite: POS system, accounting software, CRM, supply chain management. Small businesses and institutions don't need all that. They need to know what they have **now**, and why it's different from yesterday.

Tenga Inventory starts with the smallest useful capability: inventory. Nothing more, nothing less. It can grow later (add POS, add accounting), but it stands alone today.

---

## Who is it for?

**Two types of organizations:**

1. **Small grocery shops and retail** — Manage high SKU volume, track replenishment needs, see what's selling or sitting.
2. **Institutions (universities, nonprofits, departments)** — Track who has custody of what equipment, hold departments accountable for assets, know where things are.

Both types need inventory **independent of sales**. Tenga gives them that.

---

## How does it work? (The Core Loop)

### Step 1: Create Your Products

You enter each product once:
- **Name:** "Coca-Cola 500ml"
- **SKU:** "CC-500" (unique identifier)
- **Unit:** "bottle" (what you're counting)
- **Category:** "Beverages" (for grouping)
- **Cost (optional):** $0.75 (for valuation)

Done. Now the system knows about this product.

---

### Step 2: Place Stock Somewhere

Stock must be in a location. First time, you set opening balances:

| Product | Location | Quantity |
|---------|----------|----------|
| Coca-Cola 500ml | Shop Floor | 150 |
| Coca-Cola 500ml | Storeroom | 300 |
| Laptop | ICT Department | 14 |
| Laptop | Finance Department | 6 |

The system now knows:
- **"How many Coca-Colas do we have?"** → 450 (150 + 300)
- **"Where are the laptops?"** → ICT: 14, Finance: 6

---

### Step 3: Move Stock Around

Stock changes for four reasons:

**Receive:** New stock arrives (from supplier, donation).
- Quantity: +50 Coca-Colas to Shop Floor
- Cost: $0.75 each (used for valuation)
- Reason: "Supplier delivery"

**Issue:** Stock leaves (used, damaged, sold, disposed).
- Quantity: -10 Coca-Colas from Shop Floor
- Reason: "Damaged in transit"

**Transfer:** Move between locations (replenishment, relocation).
- Quantity: Move 100 Coca-Colas from Storeroom to Shop Floor
- Recorded as one event (both locations affected)

**Adjust:** Fix discrepancies (count differences, inventory loss).
- Quantity: -5 Coca-Colas from Shop Floor
- Reason: "Count correction" (we counted 145, system said 150)

Every change is recorded with:
- **What changed:** Product, quantity
- **Where:** Location
- **When:** Date and time
- **Who:** User who did it
- **Why:** Reason (damage, loss, delivery, etc.)

**This is the audit trail.** It never changes. Mistakes are corrected by recording a new change, not by erasing the old one.

---

### Step 4: Count to Verify

Periodically, you count the physical stock:

1. **Start count:** "I'm counting the Shop Floor today."
2. **Record observations:** For each product, note how many you physically see.
3. **System compares:** Expected (from our records) vs Actual (what you counted).
4. **Review differences:** "We thought we had 50 but counted 48. Why?"

---

### Step 5: Reconcile Differences

For each discrepancy, you decide:

| Product | Expected | Actual | Difference | Action |
|---------|----------|--------|-----------|--------|
| Coca-Cola | 150 | 148 | -2 | Create correction: "Count discrepancy, likely evaporation or spillage" |
| Laptop | 14 | 14 | 0 | No action needed |

The system automatically records these corrections as movements, updating balances to match reality.

---

### Step 6: View History

At any time, you can ask:

**"What happened to the Coca-Colas in the Shop Floor?"**

```
Jan 15 — Receipt: +50 units @ $0.75 each [Supplier delivery]
Jan 12 — Transfer: +100 units from Storeroom [Replenishment]
Jan 10 — Issue: -10 units [Damaged]
Jan 5  — Count Correction: -2 units [Count discrepancy]
Jan 1  — Opening Balance: +150 units [System start]

Current: 288 units
Average cost: $0.75/unit
Total value: $216
```

Every entry shows who did it, when, and why. The ledger is immutable—you can't erase history, only add to it.

---

## Key Design Decisions

### Stock is Location-Specific (Not Global)

**The wrong way (global stock):**
- "We have 100 Coca-Colas"
- "Where?" (need to check allocation list separately)

**The right way (location-first):**
- "Coca-Colas: Shop Floor 50, Storeroom 50"
- Total is obvious (50 + 50 = 100)

Where stock physically is matters. We start with that.

---

### Movements are Semantic

When you see a movement, you immediately know what happened:

- **Receipt** → Stock came in
- **Issue** → Stock went out (used, damaged, lost)
- **Transfer** → Stock moved between locations
- **Adjustment** → Quantity changed to fix discrepancy
- **Count Correction** → Physical count was different from records

No confusion. No "Transaction Type 7"—just clear language.

---

### Transfers are Atomic

A transfer from Department A to Department B is **one event**, not two:

Good: "Transferred 5 laptops from ICT to Finance"
- One movement, one timestamp, one audit entry
- Both locations updated together

Bad: "Issued 5 from ICT, Received 5 in Finance"
- Two separate movements
- Auditor has to manually match them to figure out what happened

We chose the good way.

---

### Cost is Locked at Receipt

When you receive stock with a cost ($0.75/bottle), that cost is immutable:

**Why?** Prevents accidental (or intentional) revaluation. If the invoice arrives later with a corrected price, you create a new adjustment movement with the difference. Full audit trail.

**Consequence:** Historical valuations are always reproducible. You can verify the math.

---

### Valuation is Simple + Deep

**Simple headline:** "Inventory value: $10,000"

**Drill down:** See the math:
- 100 units @ $5/unit = $500 (received Jan 1)
- 200 units @ $6/unit = $1,200 (received Jan 15)
- Average: $5.67/unit
- Current: 300 units × $5.67 = $1,700

Simple enough for quick glances. Deep enough for auditors.

---

### No POS, No Accounting, No Integrations (Yet)

Tenga Inventory is **standalone**. 

You can run it forever without ever using a POS system. It's not a "module" of a larger system. It's complete.

Later, if you add a POS:
- POS records sales
- Sales become "Issue" movements
- Tenga automatically updates stock

But Tenga doesn't require that. Ever.

---

## How Arrupe (Institutional) Uses It

**Scenario:** A university with multiple departments, each with equipment and supplies.

1. **Locations = Departments**
   - ICT Department, Finance Department, HR Department, etc.
   - Stock belongs to departments (custody, accountability)

2. **Create Products**
   - Laptops, Desktops, Printers, Office Chairs, Pens, etc.

3. **Opening Balance**
   - Admin records existing equipment by department

4. **Receive**
   - New equipment arrives: "20 Laptops received for ICT Department"

5. **Transfer**
   - Reassignment: "5 Laptops moved from ICT to Finance (new hire)"

6. **Adjust**
   - Damage found: "2 Laptops adjusted out (broken, not replaceable)"

7. **Count**
   - Quarterly verification: "Count all laptops in each department"
   - Discrepancies trigger investigation

8. **View History**
   - Auditor asks: "What happened to the laptop that Finance reported missing?"
   - System shows: Received (ICT), Transferred (ICT→Finance), Adjusted (broken)

**Benefit:** Clear accountability. If a department can't account for an asset, the history shows where it went.

---

## How a Grocery Shop Uses It

**Scenario:** Small shop, one owner, daily replenishment.

1. **Locations = Store Areas**
   - Shop Floor (customer-facing), Storeroom (back), Cold Room

2. **Products = Stock Items**
   - Coca-Cola 500ml, Bread (daily), Milk, Eggs, etc.
   - Simple categories: Beverages, Dairy, Bakery, Produce

3. **Daily Operations**
   - Morning: Receive delivery → 50 Coca-Colas to Storeroom
   - Midday: Transfer → Move 20 from Storeroom to Shop Floor (replenish)
   - Evening: Count Shop Floor → Check if low-stock items need reordering

4. **Weekly**
   - Full count of everything
   - See what's selling (moving fast) vs sitting

5. **Why This Helps**
   - Know when to reorder (low-stock list)
   - See shrinkage (spoilage, theft, waste)
   - Know inventory value (for insurance, tax)

**Benefit:** Reduce stockouts (lost sales), reduce waste (spoilage), know exactly what you have.

---

## What Tenga Does NOT Do (And Why)

❌ **Take payments** — That's POS. Tenga just tracks stock.

❌ **Invoice customers** — That's sales/invoicing. Tenga doesn't know about customers.

❌ **Pay suppliers** — That's accounting. Tenga doesn't track payables.

❌ **Track serial numbers or batch expiry** — That's batch tracking. Deferred to future.

❌ **Forecast demand** — That's AI/analytics. Future feature.

❌ **Optimize locations** — That's logistics. Not our job.

---

## MVP vs Future (What's Next)

### MVP (Shipping Now)

✓ Products & locations
✓ Receive, issue, transfer, adjust
✓ Stock counts & reconciliation
✓ Movement history (audit trail)
✓ Valuation (weighted average)
✓ User roles & permissions
✓ Reports (low-stock, stock by location, inventory value)

### Phase 2 (Post-MVP, if Pilots Ask)

? CSV import/export (speed up data loading)
? Barcode scanning (speed up data entry)
? Batch/lot tracking (for food/pharma with expiry)
? Email alerts (low-stock notifications)
? FIFO/LIFO costing (if weighted average isn't enough)
? POS integration (when they add sales)

None of these are required for MVP success. Tenga works perfectly without them.

---

## The Workflow, Step by Step

```
Day 1: Set Up
  Create 3 products (Coca-Cola, Milk, Bread)
  Create 2 locations (Shop Floor, Storeroom)
  Record opening balances
  Create 1 user (yourself)

Day 2: Daily Use
  Receive delivery → +50 Coca-Colas to Storeroom
  Transfer to floor → +20 Coca-Colas to Shop Floor
  See low-stock alert → "Milk: 5 left, minimum is 10"
  Issue for display → Manually adjust Bread count

Day 3: Weekly
  Count everything
  See discrepancies (3 less Coca-Colas than expected)
  Adjust for difference (recorded as "Count correction")

Day 30: Report
  View: "Inventory value: $2,345"
  View: "Coca-Cola moving fastest; Milk slowest"
  View: "Milk shrinkage: 5 units last month (spoilage?)"
  View: "Complete history of every movement & who did it"
```

---

## Success Looks Like

For Arrupe:
- Department managers can answer: "What equipment do we have?"
- Auditor can verify: "Where did that laptop go?" (full history)
- No more mysteries about missing assets

For Grocery:
- Owner knows: "When should I reorder?"
- Owner sees: "What's expiring or not selling?"
- Owner understands: "Actual inventory value for taxes"

---

## The Philosophy

**Tenga Inventory is inventory-first and operations-focused.**

It exists to answer one question: **"Do I know what I have, where it is, and what happened to it?"**

If the answer is yes, Tenga is doing its job. Everything else is optional.

---

## Diagram: The System at a Glance

```
┌─────────────────────────────────────────────────────┐
│                    Tenga Inventory                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Products (Name, SKU, Unit, Category, Cost)         │
│       │                                             │
│       └──→  Stock Movements (Receipt, Issue,        │
│              Transfer, Adjust, Count Correction)   │
│              [Recorded at Locations]                │
│              [Immutable, Audit Trail]               │
│       │                                             │
│       └──→  Stock Balance (Current Qty per Location)│
│             [Derived from Movements]                │
│       │                                             │
│       └──→  Valuation (Weighted Average Cost)       │
│             [From Receipt Costs]                    │
│                                                     │
│  Users & Roles (Owner, Manager, Staff)              │
│  [Every action recorded with user/timestamp/reason] │
│                                                     │
│  Reports (Low-Stock, Stock by Location, Value)      │
│                                                     │
└─────────────────────────────────────────────────────┘

Input: Movement (Receipt, Issue, Transfer, Adjust, Count)
       ↓
Processing: Validate, record, update balances
       ↓
Output: Current stock, history, valuation, reports
```

---

## In Three Sentences

**Tenga Inventory is a lightweight system that records every change to stock (receiving, issuing, transferring, adjusting) and displays the current state and full history. It works standalone without sales, accounting, or POS. It gives small businesses and institutions complete visibility: what you have, where it is, and what happened to it.**

