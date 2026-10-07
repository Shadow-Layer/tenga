# Tenga Inventory — UX & Interaction Requirements

## Purpose

This document defines interaction principles and how users experience Tenga Inventory. It balances simplicity for first-time users with depth for experienced users through progressive disclosure.

---

## Core UX Principles

### Principle 1: Minimal Cognitive Load

**Definition:** Every screen shows only what's necessary for the current task. Advanced options are hidden by default.

**Example:** Receive Stock form shows:
- **Required fields:** Product, Location, Quantity
- **Visible optional fields:** Cost, Reason, Reference
- **Hidden advanced fields (collapsible):** None (keep it simple)

**Consequence:** New users can complete core workflows without being overwhelmed.

---

### Principle 2: Obvious Primary Actions

**Definition:** The next logical action is always prominent and easy to find.

**Example:** Product detail page shows:
- **Primary action at top:** "Receive Stock" button (bright, large)
- **Secondary actions:** "Issue Stock", "Transfer", "Count"
- **Tertiary:** "Edit Product", "View History"

**Consequence:** Users instinctively know how to proceed.

---

### Principle 3: Progressive Disclosure

**Definition:** Advanced features, filters, and explanations are revealed only when needed or requested.

**Example:** Valuation section on Product detail:
- **Basic view:** "Inventory Value: $500" (single line)
- **On click "Why?":** Modal explains weighted average
- **On drill-down:** See cost history by receipt

**Consequence:** Simple for most; detailed for those who need it.

---

### Principle 4: Sensible Defaults

**Definition:** Forms pre-fill with reasonable defaults; users rarely need to enter the same data twice.

**Example:** Receive Stock form:
- **Date field:** Pre-filled with today's date (editable if receipt is backdated)
- **User field:** Auto-filled with current logged-in user (not editable)
- **Location field:** Pre-filled with last-used location (editable)

**Consequence:** Fast data entry; fewer keystrokes.

---

### Principle 5: Clear Feedback

**Definition:** Every action produces immediate, unambiguous feedback.

**Example:** User submits a receipt:
- ✓ Success message: "Received 50 units of 'Coca-Cola 500ml' at 'Shop Floor'. New balance: 150 units."
- Error message: "SKU 'X' not found. Did you mean 'X2'?" (with autocomplete)

**Consequence:** Users know their action succeeded.

---

### Principle 6: Recoverable Mistakes

**Definition:** Actions are undoable (where possible) or correctable via explicit corrective workflows.

**Example:**
- Accidental receipt? Issue it back out with "Correction" reason.
- Accidental count? Reject the pending count and redo it.
- Wrong location? Create a transfer to move it.

**Consequence:** Users feel safe experimenting.

---

### Principle 7: Understandable Terminology

**Definition:** Language matches user mental models; POS/accounting jargon avoided.

**Example:**
- Use "Issue" not "Outbound Transfer" or "Sale"
- Use "Damage" not "Shrinkage"
- Use "Count" not "Inventory Reconciliation" or "Stock Take"

**Consequence:** Non-technical users understand the system.

---

### Principle 8: Visible Consequences

**Definition:** Users can see the result of their actions immediately.

**Example:** After transferring 10 units from Storeroom to Shop Floor:
- Storeroom balance: 50 → 40 (visible change)
- Shop Floor balance: 20 → 30 (visible change)
- Movement appears in history (with both locations)

**Consequence:** Users trust they didn't break anything.

---

### Principle 9: Contextual Advanced Functionality

**Definition:** Power-user features are available without cluttering the interface.

**Example:** Movement History view has filters (hidden by default):
- **Visible:** List of recent movements
- **On "Filter":** Options appear: Movement Type, Product, Location, Date Range

**Consequence:** Casual users see a simple list; power users can drill down.

---

## UX Progression: Three Complexity Levels

### Level 1: Basic (Default)

**Audience:** First-time users, frequent operational staff

**Workflows:**
- Create product (name, SKU, unit, category only)
- Receive stock (product, location, quantity)
- Issue stock (product, location, quantity, reason)
- View inventory (total quantity, per location)
- View low-stock alerts

**Design:**
- One primary screen per task
- Four fields maximum on forms
- No jargon
- Colorful, simple icons
- "Help" tooltips inline

**Example Screen: Receive Stock (Level 1)**

```
┌─────────────────────────────────────┐
│ Receive Stock                       │
├─────────────────────────────────────┤
│                                     │
│ Product *        [Coca-Cola 500ml]  │ ← Search dropdown
│ Location *       [Shop Floor] ▼     │ ← Dropdown
│ Quantity *       [___]               │ ← Number input
│                                     │
│         [Cancel]    [Receive]       │
│                                     │
└─────────────────────────────────────┘

Success: "Received 50 units. New balance: 150"
```

---

### Level 2: Intermediate (Optional Fields)

**Audience:** Managers, supervisors, regular users after first month

**Additional workflows:**
- Add cost to receipt (optional)
- Adjust stock with reason
- Transfer between locations
- View movement history with date filters
- Run basic reports (low stock, stock by location)

**Design:**
- Forms show optional fields (Cost, Reason, Reference)
- Dropdown to "Show Advanced" for more options
- Links to drill down (e.g., "See cost history")
- Filters appear on request

**Example Screen: Receive Stock (Level 2)**

```
┌─────────────────────────────────────────────┐
│ Receive Stock                               │
├─────────────────────────────────────────────┤
│ Product *          [Coca-Cola 500ml]        │
│ Location *         [Shop Floor] ▼           │
│ Quantity *         [___]                    │
│                                             │
│ Cost (optional)    [___] per unit           │
│ Reason             [Supplier delivery] ▼    │
│ Reference          [Invoice INV-123]       │
│ Date               [2024-01-15] (editable)  │
│                                             │
│ ▶ Show Advanced Options                     │
│                                             │
│         [Cancel]    [Receive]               │
│                                             │
└─────────────────────────────────────────────┘
```

---

### Level 3: Advanced (Power User)

**Audience:** Admins, auditors, data analysts

**Additional workflows:**
- Batch import/export (CSV)
- Detailed movement history with full filters (type, user, timestamp range)
- Cost history and valuation drill-down
- Audit trail (who did what)
- Raw data export for external analysis
- User management and permissions

**Design:**
- All fields visible
- Multiple filter/sort options
- Advanced metrics (cost trends, inventory turnover)
- API access (future)

**Example Screen: Movement History (Level 3)**

```
┌────────────────────────────────────────────────┐
│ Movement History                               │
├────────────────────────────────────────────────┤
│                                                │
│ Filters:                                       │
│ Product [Coca-Cola] | Location [All] ▼        │
│ Type [All] ▼ | Date Range [Jan 1–31] ▼        │
│ User [All] ▼ | [Apply]                        │
│                                                │
│ ┌──────────────────────────────────────────┐  │
│ │ Date   Type       Product Qty  User      │  │
│ ├──────────────────────────────────────────┤  │
│ │ Jan 31 Receipt    Coca-Cola  +50  Sarah │  │
│ │ Jan 30 Issue      Coca-Cola  -10  Mike  │  │
│ │ Jan 29 Count Corr Coca-Cola  +2   Bob   │  │
│ │ ...                                      │  │
│ └──────────────────────────────────────────┘  │
│                                                │
│ [Export CSV]                                   │
│                                                │
└────────────────────────────────────────────────┘
```

---

## Onboarding Paths

### Path A: Single-Owner Shop

**Scenario:** One person (owner) runs the entire inventory.

**Onboarding:**
1. Create organization and initial admin user (owner).
2. **Quick start:** "Set up your first product."
   - Form: Name, SKU, Unit, Category.
   - Auto-suggests location "Main Store".
   - Option: "Add opening stock?" → Receive form opens.
3. After first 3 products: "You're ready! Here are the next steps."
   - Receive stock
   - View low-stock list
   - Count inventory

**Initial UI:**
- Dashboard shows: "3 products | 250 units | $500 value"
- Four big buttons: "Receive", "Issue", "Count", "View Inventory"
- No mention of roles, users, or permissions.

---

### Path B: Institutional (Multi-Department)

**Scenario:** University with departments, manager coordination needed.

**Onboarding:**
1. Admin creates organization and roles.
2. Admin creates locations: "ICT Department", "Finance Department", "HR Department".
3. Admin creates products and imports opening balances (CSV).
4. Admin creates users: Department Managers (role=Manager), Staff (role=Staff).
5. Dashboard shows per-department status.

**Initial UI:**
- Dashboard shows: "3 departments | 500 items | Who has what?"
- Tab per department with department-specific inventory.
- Manager sees own department; Admin sees all.

---

## Navigation and Information Architecture

### Main Navigation (Post-Login)

```
Dashboard (default)
│
├─ Inventory
│  ├─ Products
│  ├─ Stock Movements
│  │  ├─ Receive
│  │  ├─ Issue
│  │  ├─ Transfer
│  │  └─ Adjust
│  └─ Counts
│     ├─ Start Count
│     ├─ Pending Counts
│     └─ Reconcile
│
├─ Locations
│  └─ (Create / Edit)
│
├─ Reports
│  ├─ Low Stock
│  ├─ Stock by Location
│  ├─ Recent Movements
│  └─ Inventory Value
│
├─ Settings (Admin only)
│  ├─ Users
│  ├─ Organization Info
│  └─ Data (Export/Backup)
│
└─ Logout
```

---

## Error Handling and Validation

### Validation Philosophy

**Fail early, fail clearly, suggest recovery.**

**Example: Duplicate SKU**

```
❌ "SKU 'LT-001' already exists."

Did you mean one of these?
• Laptop (LT-001) — created Jan 5
• Laptop 2023 (LT-001-2023) — created Jan 10

[Edit SKU] [Use Existing]
```

**Example: Insufficient Stock**

```
⚠️ "Quantity 160 exceeds available balance (150)."

Current balance:    150
Requested issue:    160
Shortfall:          10 units

[Adjust quantity] [Continue anyway] [Cancel]

← "Why would you issue more than available?"
   (Linked to help article)
```

---

## Feedback and Notifications

### Success Feedback

**Format:** Confirmation modal or toast message (toast preferred for speed).

```
✓ "Received 50 units of 'Coca-Cola 500ml' at 'Shop Floor'.
   New balance: 150 units."
```

**Stays visible for:** 4 seconds, then auto-dismiss. User can click to keep longer.

---

### Error Feedback

**Format:** Inline form error or modal for critical errors.

**Inline (field-level):**

```
Product *    [________] ← Required
             ↑ This field is required.
```

**Modal (critical):**

```
❌ Error Saving Receipt

Database connection lost. Your data was not saved.

[Retry]  [Save offline (future)]  [Cancel]
```

---

### Warnings

**Format:** Yellow banner or highlighted section.

```
⚠️ "Negative balance detected: -5 units. Please review."
```

---

## Accessibility Baseline (MVP)

### Keyboard Navigation
- All major actions accessible via keyboard (Tab, Enter, Esc).
- No mouse-only interactions.

### Color Contrast
- Text meets WCAG AA standards (4.5:1 contrast ratio).
- Color not the only differentiator (use icons + color).

### Screen Readers
- Form labels associated with inputs (`<label for="...">`)
- Major sections marked with semantic headings

### Future (Post-MVP)
- Full WCAG AA compliance
- Dark mode
- High-contrast mode
- Keyboard shortcuts documentation

---

## Empty States

**When inventory is empty:**

```
┌──────────────────────────────────────────┐
│ 📦 No products yet.                      │
│                                          │
│ Get started by creating your first       │
│ product.                                 │
│                                          │
│ [Create First Product]  [Import CSV]    │
│                                          │
│ Learn more: Tenga Guides (link)         │
└──────────────────────────────────────────┘
```

---

## Confirmation Workflows

### Destructive or Irreversible Actions

**Pattern:** Three-step confirmation for high-risk actions.

1. **User initiates:** "I want to reject this count."
2. **Confirmation modal:** "This will discard all observations. Confirm?"
3. **If confirmed:** Action happens; undo is not available (count is gone).
4. **Feedback:** "Count rejected. Start a new count if needed."

**Example: Reject Count**

```
⚠️ Confirm Rejection

This will discard all observations for this count.
You will need to start a new count.

[Cancel]  [Yes, Reject]
```

---

## Loading and Latency Handling

### Initial Page Load
- Show skeleton screen or spinner for 2+ seconds.
- Skeleton shows the general layout (e.g., table with placeholder rows).

### Data Refresh
- Optimistic updates: balance shows immediately; server confirms in background.
- If server rejects: show undo option.

### Network Failures
- Graceful degradation: cached data shown with a "Offline" badge.
- Sync button: "Tap to sync when online."
- Queued actions: "3 actions queued. Will sync when online."

---

## Mobile Considerations (Future; Not MVP)

### MVP: Web Desktop
- Designed for desktop/tablet browsers.
- Responsive (works on mobile but not optimized).

### Future: Mobile-First
- Touch-friendly buttons (48px minimum).
- Vertical form layouts (no side-by-side fields).
- Barcode scanner integration (future).

---

## Summary: UX Goals by Audience

| Audience | Goal | Primary Actions |
|----------|------|-----------------|
| Single owner | Fast solo operation | Receive, Issue, View Inventory |
| Institutional manager | Coordination & accountability | Receive, Count, Transfer, View by Dept |
| Staff member | Record observations | Receive, Issue, Count |
| Admin | System health & audit | User management, Exports, Backup |

All audiences share: Minimal cognitive load, clear feedback, recoverable mistakes.

---

## Accessibility and Inclusivity

### Language
- Use simple, clear language (avoid jargon).
- Support multiple languages (future; MVP: English).

### Cognitive Load
- Break complex tasks into smaller steps.
- Provide context and explanations inline.
- Offer templates and suggested workflows.

### Visual Clarity
- Large text and icons.
- High-contrast mode support (future).
- Color-blind friendly palette (test with tools).

---

## Success Metrics for UX

**MVP validation in pilots:**
- Time to complete "Receive Stock" for first-time user: < 2 minutes
- Accuracy of counted items: > 95% match without re-counts
- User confidence in navigation: "I know where to find things" > 80%
- Support requests related to UI: < 10% of pilot user base

---

## Summary

Tenga Inventory UX is **simple by default, deep when demanded**. Every screen prioritizes clarity and action. Three levels of complexity (Basic, Intermediate, Advanced) support users from onboarding to expertise. Mistakes are recoverable; feedback is clear. The system helps users do their job faster and with confidence.
