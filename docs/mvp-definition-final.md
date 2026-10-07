# Tenga Inventory — Final MVP Definition

## Purpose
A concise, defensible definition of what belongs in the MVP, why each item is included, and what is explicitly deferred.

---

## MVP: Included Capabilities (with justification)

1. Products (Create/Search/View)
   - Why: Foundational. Inventory cannot exist without items.
   - Deferred: Images, attributes beyond basic are post-MVP.

2. Locations (Create/List/Hierarchy)
   - Why: Stock is location-specific; required for custody/accountability.
   - Deferred: Location capacity rules, geolocation.

3. Stock Movements: Receipt, Issue, Transfer (atomic), Adjustment, CountCorrection
   - Why: Core operational loop; audit trail requirement.
   - Deferred: Partial receipts workflow, transit/dispatch states.

4. Stock Counts & Reconciliation
   - Why: Ensures recorded vs physical stock aligns; central to inventory operations.
   - Deferred: Offline counting app, barcode scanning to speed counts.

5. Movement History (Append-only) & Audit Trail
   - Why: Accountability and traceability for pilots.
   - Deferred: Advanced audit reports.

6. Valuation (Weighted Average) with drill-down
   - Why: Practical costing for pilots; preserves per-receipt cost.
   - Deferred: FIFO/LIFO and batch valuation methods.

7. User Management & Three-role RBAC
   - Why: Accountability and role separation required for institutions.
   - Deferred: Per-resource granular permissions.

8. Basic Reporting: Low-stock, Stock by Location, Inventory Value
   - Why: Operational needs for pilots.
   - Deferred: Scheduled alerts, complex dashboards.

9. Organization/Tenancy support
   - Why: Multi-tenant or multi-org pilots; data isolation required.

10. Data Durability: Backups and transactional integrity
   - Why: Prevent data loss and ensure correctness.

---

## MVP: Explicitly Deferred
- Offline operation & sync (unless pilot demands)
- Barcode scanning / mobile-first features
- Batch/lot/serial tracking
- Supplier/purchase order flows
- Accounting/fiscal integrations (exports only)
- Complex role/permission granularity
- Predictive analytics / forecasting

---

## MVP Acceptance Gate
- Pilot scoping confirms offline and import needs or the MVP scope is adjusted.
- Core ACs (see acceptance-criteria.md) pass in a staging environment with pilot-like data.
- Performance checks with representative datasets (or validated pilot estimates) are passed.

