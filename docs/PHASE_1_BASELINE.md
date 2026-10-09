# Tenga Inventory POS — Phase 1 Baseline (Current State)

**Prepared**: October 9, 2026  
**Status**: Complete backend implementation, minimal frontend  
**Scope**: Inventory management, POS, subscription, offline-first architecture

---

## Document Purpose

This baseline document establishes the existing state of Tenga Inventory POS before Phase 4 (Design System) begins. It consolidates:

1. **What has been built**: Core backend services, database schema, API layer
2. **What the product must support**: Business requirements, user roles, workflows
3. **What remains open**: Unresolved decisions affecting UX design
4. **What the frontend currently is**: Minimal (1 React component, API-driven)

This baseline is the reference point for all Phase 4 design decisions.

---

## Part 1: Existing Implementation Status

### Backend (Complete ✅)

**Language & Framework**: Python 3.14+ with FastAPI

**Database**: SQLAlchemy 2.1.5
- SQLite (development)
- PostgreSQL 13+ (production)
- Alembic migrations
- 10 core domain entities

**Core Services** (5 stateless modules):
1. **SubscriptionService** — State machine (ACTIVE → GRACE → LIMITED), grace periods (7d monthly, 30d annual)
2. **InventoryService** — Immutable append-only ledger, stock computation, discrepancy detection
3. **SaleService** — Online/offline sales, queueing, idempotent commitment
4. **TillService** — Session lifecycle, LIMITED mode enforcement
5. **SyncService** — Batch processing, idempotency, state synchronization

**API Layer**: FastAPI with Swagger documentation
- Authentication: JWT-based
- Authorization: Role-based (Owner/Admin, Manager, Staff)
- Endpoints documented in `/openapi.json`

**Testing**: 44 tests passing (36 unit + 8 E2E)
- All 3 critical business decisions (U006, U007, U008) implemented and verified
- Test coverage: Subscription state machine, inventory movements, offline conflicts

---

### Frontend (Minimal)

**Current State**:
- 1 React component: `AdminQuickStart.tsx` (272 lines)
- Purpose: Serves API documentation on home page
- Not a functional inventory or POS interface

**Technology Stack**:
- React 19.3.0
- TypeScript 5.3.0
- Vite 5.0 (build tool)
- Tailwind CSS 4.3.0 (styling)
- zustand 5.0 (state management)
- axios (HTTP client)
- react-router-dom 7.18.4 (navigation)
- react-query 5.104.1 (data fetching)

**Styling Foundation**:
- Tailwind CSS with basic theme (primary, success, error, warning colors)
- System font stack
- 23-line index.css (Tailwind import only)

**Deployment**:
- Vite-based build
- React Router configured but no routes defined
- API calls ready (axios configured)

---

## Part 2: Business Requirements & Constraints

### Business Model

**Product**: Cloud-based inventory and POS system for small businesses (focus: Zimbabwean market)

**Business Decisions** (Approved, D001–D010):

| Decision | Status | Implication for Design |
|----------|--------|------------------------|
| **D001**: Inventory-first | ✅ Approved | Inventory is independently useful without POS. POS is optional workflow. |
| **D002**: Pilot segments (Arrupe + small grocery) | ✅ Approved | Product must support both accountability-heavy (charity) and high-SKU (retail) operations. |
| **D003**: MVP bundle | ✅ Approved | Inventory, locations, movements, counts, basic reports. POS added beyond MVP. |
| **D004**: Weighted-average valuation | ✅ Approved | Cost tracked per receipt; valuation computed deterministically. |
| **D005**: Three-role RBAC | ✅ Approved | Owner/Admin, Manager, Staff. No granular permissions in MVP. |
| **D006**: Location-specific stock | ✅ Approved | Stock identity is (Product, Location). Tills are per-location. |
| **D007**: Semantic movement types | ✅ Approved | Movements typed: OpeningBalance, Receipt, Issue, Transfer, Adjustment, CountCorrection. |
| **D008**: Atomic transfers | ✅ Approved | Transfer affects source and destination in one event. |
| **D009**: Locked receipt cost | ✅ Approved | Cost immutable at receipt; corrections via new movements. |
| **D010**: Valuation drill-down | ✅ Approved | Show headline + drill to movement-level receipts. |

### Critical Architectural Decisions (U006, U007, U008)

These decisions are **already implemented** in backend code and are **constraints for UI design**:

#### U006: Permit & Reconcile Afterward (Oversell Policy)

**Decision**: Sales do not validate stock at point of sale. Tills can oversell. Discrepancies detected on sync via physical count.

**Implementation**:
- No stock validation in `SaleService.create_sale()`
- Sales recorded with status: COMPLETED (online) or PENDING (offline)
- On sync, PENDING sales committed as InventoryMovement
- `InventoryService.detect_discrepancy()` identifies shortage/surplus
- Caller records ADJUSTMENT movement to reconcile

**Test Status**: ✅ Verified
- `test_create_sale_within_stock` — Sale decreases stock
- `test_can_oversell_in_offline_mode` — Oversell allowed, negative stock permitted
- `test_multi_till_offline_conflict_scenario` — Multi-till sales both committed, shortage detected
- `test_detect_discrepancy_shortage` — Shortage detected
- `test_detect_discrepancy_surplus` — Surplus detected

**UI Implications**:
- Checkout should NOT show stock warnings or reject sales
- After checkout, should NOT promise "saved to inventory" until confirmed
- Offline sales must retain identity across retries (prevent duplicate sales)
- On sync, UI must communicate: "Sale recorded. Stock now at -5. Physical count required."
- Reconciliation flow: Show discrepancy, allow adjustment, confirm correction

**Not a Design Decision**: The oversell behavior is **backend-enforced**. UI cannot override it.

#### U007: Tiered Grace Periods (Subscription Policy)

**Decision**: On subscription expiry:
- Monthly subscriptions: 7-day grace period
- Annual subscriptions: 30-day grace period
- After grace: organization enters LIMITED mode (tills cannot open new operations)

**Implementation**:
- `SubscriptionService.compute_current_state()` returns ACTIVE, GRACE, or LIMITED
- Grace duration configurable per subscription term
- `TillService` enforces LIMITED mode: new sales blocked, existing tills can sync and reconcile only

**Test Status**: ✅ Verified
- State transitions tested
- Grace period computation tested
- LIMITED mode blocking tested

**UI Implications**:
- Should display subscription status (Active, 5 days in grace, Limited mode)
- If in LIMITED mode: "Your subscription has expired. Please renew to record new sales. You can still sync existing offline transactions."
- Do NOT silently hide POS or show confusing expiry warnings
- If in GRACE: Show notice but allow operations (no blocking)

**Not a Design Decision**: Grace period duration is **business policy**, not negotiable in UI.

#### U008: Offline-First Optimistic Caching

**Decision**: Tills cache subscription state locally. Device operates optimistically offline. Server validates state on reconnect.

**Implementation**:
- `CachedSubscriptionState` model persists local copy
- Till checks cache first; uses cache if offline
- On sync, server returns authoritative state
- If cache diverged: server state wins, local operations may need reversal or adjustment

**Test Status**: ✅ Verified (cache logic passing; sync manager integration ⚠️ in progress)
- Cache stores/retrieves subscription state
- Offline operation with cache
- Server validation on reconnect

**UI Implications**:
- Should NOT show "You are offline" as a permanent failure
- Should show "Working offline. Local changes will sync when connected."
- On reconnect: "Syncing... Please wait." (not instant)
- If server state differs: "Sync complete. Server has newer information. [View Details]"
- Inventory changes during offline must show: "Recorded locally. Pending sync."

**Not a Design Decision**: Offline caching mechanism is **backend architecture**. UI reflects backend behavior.

---

## Part 3: Domain Model & Data Rules

### Core Entities (10)

| Entity | Purpose | Key Attributes | Created By |
|--------|---------|-----------------|------------|
| **Organization** | Business entity | id, name, code | Admin on signup |
| **Location** | Physical store/site | id, org_id, name, code | Admin/Owner |
| **Product** | Inventory item | id, location_id, name, sku, unit_price, cost_price | Manager/Admin |
| **Stock** (computed) | Current balance | product_id, location_id, quantity_on_hand | Computed from movements |
| **Till** | Checkout device | id, location_id, name, device_id | Admin/Owner |
| **User** | Staff member | id, org_id, username, role | Admin/Owner |
| **Subscription** | Billing record | id, org_id, status, billing_term, expires_at | System |
| **Sale** | Transaction record | id, till_id, status (PENDING/COMPLETED), total | Cashier |
| **SaleItem** | Line item | sale_id, product_id, quantity, unit_price | Cashier |
| **InventoryMovement** (Append-only) | Stock change ledger | id, product_id, location_id, type (Opening, Receipt, Sale, Transfer, Adjustment, Count), quantity, cost | Service |

### Critical Invariants (Enforced in Backend)

1. **Stock is location-specific**: All balances stored per (product, location)
2. **Movement ledger is immutable**: InventoryMovement records never modified or deleted
3. **Sale produces movement**: Every completed sale creates corresponding InventoryMovement (negative quantity)
4. **Cost locked at receipt**: Movement cost immutable; corrections via new movements
5. **Transfer is atomic**: One movement affects both source and destination
6. **Stock can go negative**: Oversale allowed; reconciliation detects and corrects
7. **Idempotent sync**: Same sale sync'd twice creates one movement
8. **Permissions enforced at API**: UI hiding does not enforce authorization

### No UX Shortcuts

- UI must not imply stock is exclusive or reserved
- UI must not claim a sale is "complete" before backend confirms commitment
- UI must not hide that offline operations are provisional
- UI must not fabricate synchronization certainty
- UI must not silently choose reconciliation policy

---

## Part 4: Users & Workflows

### User Roles (3-tier RBAC)

| Role | Permissions | Primary Workflow | Workspace |
|------|-------------|------------------|-----------|
| **Owner/Admin** | Create org, users, locations, tills; view all data; manage subscription | Setup, reporting, user management | Admin console |
| **Manager** | Create products, manage inventory, view reports | Daily operations: stock in/out, counts, reconciliation | Main app |
| **Staff/Cashier** | Record sales, view products | Focused checkout only | Simplified checkout UI |

**Design Implication**: Owner and Manager should have access to full inventory interface. Staff should have focused checkout, not full product catalogue.

---

## Part 5: Core Workflows (User Journeys)

### Workflow 1: New Business Setup

**User**: Shop owner  
**Goal**: Get to first sale in <10 minutes

**Journey**:
1. Sign up → Create organization
2. Create first location (store name, location code)
3. Create first product (name, SKU, unit price)
4. Record opening stock (quantity on hand)
5. Create till (register name, device ID)
6. Record first sale
7. See updated inventory

**Design Principle**: Minimize mandatory fields. Defer optional setup.

### Workflow 2: Daily Inventory Check

**User**: Manager  
**Goal**: Find a product, check stock, record a movement

**Journey**:
1. Open Inventory view
2. Search/filter for product
3. See current stock at location(s)
4. See stock history (receipts, sales, adjustments, counts)
5. Record adjustment (e.g., "Shelf count shows 3, ledger says 5, adjust to 3")
6. See movement appear in ledger

**Design Principle**: Product detail should show stock, history, and actions in one place.

### Workflow 3: Checkout (Fast Path)

**User**: Cashier  
**Goal**: Record a sale in <2 minutes

**Journey**:
1. Start new sale on till
2. Scan barcode or search product
3. Product appears in cart with quantity 1
4. Adjust quantity if needed
5. Add payment method
6. Confirm sale
7. Print receipt (or skip if printer unavailable)

**Design Principle**: One obvious action per screen. No unnecessary fields.

### Workflow 4: Stock Reconciliation (After Physical Count)

**User**: Manager  
**Goal**: Resolve a discrepancy between physical count and ledger

**Journey**:
1. Record physical count (e.g., "Counted 5 units of Item X")
2. System shows: Ledger says 8, you counted 5, difference is -3
3. Manager reviews: Any recent movements? Any missing receipts?
4. Confirm adjustment: "Record as adjustment: -3, reason: Physical count"
5. Ledger updated; movement recorded with reason
6. Stock now shows 5; discrepancy closed

**Design Principle**: Show the discrepancy clearly. Require confirmation before adjustment.

### Workflow 5: Offline Sale & Sync

**User**: Cashier  
**Goal**: Record sale when internet is down; sync when connection returns

**Journey**:
1. Till shows "Offline" indicator (not a blocker)
2. Scan products and record sale normally
3. Sale shows: "Recorded locally. Will sync when connected."
4. Internet returns
5. Till syncs automatically (or "Sync" button available)
6. Sale now shows "Synced" with server timestamp
7. Inventory updated

**Design Principle**: Offline is a normal state, not an error. Sync completion is confirmable.

### Workflow 6: Offline Multi-Till Conflict

**Scenario**: Two tills offline, both sell from limited stock (e.g., 5 units). Till A sells 4, Till B sells 3.

**Journey**:
1. Till A offline: Sells 4 units of Item X. Shows "Recorded locally."
2. Till B offline: Sells 3 units of Item X. Shows "Recorded locally."
3. Till A reconnects, syncs: Sale of 4 committed. Stock now -4.
4. Till B reconnects, syncs: Sale of 3 committed. Stock now -7.
5. System detects shortage of 7 units.
6. Manager is notified: "Stock discrepancy detected: Item X at Location Y is short 7 units. Physical count required."
7. Manager counts stock, records adjustment: "Adjust by +7, reason: Physical count reconciliation"
8. Stock now correct.

**Design Principle**: Do not hide the conflict. Show exact discrepancy and required action.

---

## Part 6: Technical Constraints for UI Design

### API-Driven Architecture
- Frontend communicates exclusively via REST API (`/api/v1/...`)
- No direct database access
- Authentication via JWT (Authorization header)
- API responses define available data for UI

### Offline Operation
- Must persist local state to browser storage (or SQLite if Electron/PWA)
- Sync manager handles retry logic and conflict resolution
- UI must distinguish: "Local (pending)", "Synced", "Conflict", "Failed"

### Database Constraints
- Stock quantities can be negative (oversale allowed by design)
- InventoryMovement records immutable (no edit/delete, only view)
- One sale = one movement entry per line item

### Subscription & Permissions
- Subscription state determines allowed operations (LIMITED mode blocks new sales)
- Permissions enforced at API layer (not just UI hiding)
- UI should show why an action is unavailable (permission, subscription, connection, etc.)

---

## Part 7: Unresolved Design Decisions

### D010a: Offline Stock Policy (Unresolved)

**Question**: When a till is offline and the user tries to record a sale, what should happen?

**Current Backend Behavior**: Sale is allowed regardless of stock. No validation.

**Available Options**:

| Option | Behavior | Pros | Cons |
|--------|----------|------|------|
| **A: Permit Always** | Offline till records sale without checking stock | Simple, no coordination needed | Oversell possible; requires reconciliation |
| **B: Cache & Optimistic** | Offline till uses last-known stock, shows warning if insufficient | Better UX, limits obvious errors | Cache can become stale; still requires reconciliation |
| **C: Block & Require Sync** | Offline till cannot start sale until sync | No oversell risk | Blocks workflow when internet is intermittent |

**Consequences**:
- **Option A** (Current): UI must show "Sale recorded. Stock impact TBD pending sync."
- **Option B**: UI must cache stock, show warning if sale exceeds cache, allow sale anyway, warn on reconciliation
- **Option C**: UI must block checkout UI, show "Sync required" modal

**Design Implication**: Choice affects whether checkout screen shows stock warnings, allows sale despite low/negative stock, and how reconciliation is presented.

**Status**: ⚠️ **Unresolved** — Awaits product decision. Design will mark this as provisional and test both approaches.

### D014: Fiscal Integration (Unresolved)

**Question**: Is receipt printing a functional requirement for sale completion, or can a sale be completed without a receipt?

**Current Backend Behavior**: Sale status is COMPLETED immediately. Receipt printing is separate.

**Available Options**:

| Aspect | Regulatory | Operational |
|--------|-----------|--------------|
| **Fiscal Requirement** | In some jurisdictions, sales require fiscal/tax compliance before sale is final | May require third-party integration (e.g., fiscal server) |
| **Zimbabwe Context** | Unknown — requires research with local authorities and existing POS products | Affects receipt generation and audit trail |
| **Tenga Scope** | Not yet determined | Post-MVP likely, but may affect UI design now |

**Consequences**:
- If fiscal integration required: Sale cannot be final until fiscal server confirms (adds latency, requires fallback)
- If not required: Receipt printing is operational convenience, not transaction-critical
- If required but deferred: Offline sales must queue for fiscal verification on reconnect

**Design Implication**: UI must distinguish whether "sale complete" means "recorded locally" vs. "fiscally certified" vs. "receipt printed".

**Status**: ⚠️ **Unresolved** — Awaits product decision and local regulatory research. Design will mark this as TBD and escalate to product owner.

---

## Part 8: Design System Baseline (Minimal)

### Current Styling (Tailwind CSS)

**Colors**:
- Primary: `#2563eb` (blue)
- Success: `#16a34a` (green)
- Error: `#dc2626` (red)
- Warning: `#ea580c` (orange)

**Typography**: System font stack (system-ui, -apple-system, sans-serif)

**Spacing**: Tailwind defaults (no custom scale defined)

**Components**: None. Tailwind utility classes only.

### Phase 4 Design System to Build

Will define:
- Complete color token system
- Typography scale (sizes, weights, line heights)
- Spacing scale
- Component library (buttons, inputs, tables, modals, etc.)
- State indicators (online, offline, syncing, error)
- Responsive breakpoints and behavior
- Accessibility standards

---

## Part 9: Navigation Model (Proposed, To Be Designed)

**Principle**: Organize around user intent, not technical modules.

**Proposed Tab/Navigation Structure**:

```
┌─────────────────────────────────────────┐
│ Tenga Inventory                    🔔 ⚙️ │
├─────────────────────────────────────────┤
│ 📦 Inventory | 💳 Checkout | ⚙️ Admin  │
├─────────────────────────────────────────┤
│                                         │
│  [Primary Content Area]                │
│                                         │
│  [Offline/Sync Status - if needed]     │
│                                         │
└─────────────────────────────────────────┘
```

**Inventory Tab**: Product list, stock, movements, counts  
**Checkout Tab**: Focused till/cashier workflow  
**Admin Tab**: Users, locations, tills, reports (Owner/Manager only)

**Note**: This is proposed for review. Checkout may be modal overlay instead of tab.

---

## Part 10: Acceptance Criteria for Phase 4

Phase 4 is ready for review when:

1. ✅ **Design system defined** — Tokens, components, states documented
2. ✅ **Inventory screens designed** — At least 6 screens: overview, list, create, detail, count, reconciliation
3. ✅ **Wireframes created** — HTML/CSS mockups, interactive, responsive
4. ✅ **Unresolved decisions documented** — D010a and D014 marked clearly; no silent assumptions
5. ✅ **Traceability preserved** — Design choices linked to requirements or flagged as proposals
6. ✅ **Offline/error states included** — All major screens have online, offline, loading, error, empty variants
7. ✅ **Mobile/tablet behavior defined** — Responsive rules for supported screen sizes
8. ✅ **Accessibility checklist** — Text sizes, contrast, keyboard nav, focus indicators documented
9. ✅ **Evidence-based** — Design patterns sourced from competitor research or Tenga requirements, not invention

---

## References

### Existing Documentation
- `/docs/01-project-charter.md` — Original mission and constraints
- `/docs/05-requirements-specification.md` — Complete requirements
- `/docs/implementation-decisions-u006-u007-u008.md` — Backend architecture (U006, U007, U008)
- `/docs/00-implementation-state-current.md` — Implementation details
- `/docs/implementation-business-rules.md` — 20 enforced business rules

### Code References
- `/src/services/` — Business logic (backend)
- `/src/models/` — Domain entities
- `/src/routers/` — API endpoints
- `/src/components/AdminQuickStart.tsx` — Minimal existing frontend
- `/tailwind.config.js` — Current theme
- `/src/index.css` — Current styles

---

**Status**: ✅ Complete  
**Prepared for**: Phase 4 Design System  
**Next Step**: Proceed to competitor research synthesis and design system definition
