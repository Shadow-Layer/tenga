# Tenga Inventory — Acceptance Criteria (Consolidated)

This document consolidates observable acceptance criteria for the core MVP features. Each criterion is phrased as an observable result (Given/When/Then where helpful).

---

## AC-001 — Create Product
- Given a logged-in Owner/Admin, when they submit a valid Create Product form (name, SKU, unit, category), then the product is created and appears in search within 5s.
- Given the same SKU already exists in the organization, when creating a product with that SKU, then creation is rejected with a clear error.

## AC-002 — Receive Stock
- Given an existing product and location, when a user submits a Receipt with positive quantity, then a StockMovement of type Receipt is created and StockBalance at that (product,location) increases by that quantity.
- Given cost was provided, when receipt is submitted, then movement stores the cost immutably and average cost is recomputed accordingly.

## AC-003 — Issue Stock
- Given a product with available quantity, when user issues quantity <= available, then the StockMovement of type Issue is created and StockBalance decreases by that quantity.
- Given user attempts to issue more than available, system warns and allows override only after explicit confirmation. If overridden, StockBalance may become negative and movement is recorded.

## AC-004 — Transfer Stock (Atomic)
- Given product at source location with sufficient quantity, when user submits a Transfer, then a single movement of type Transfer is created, source balance decreases and destination increases atomically; movement history shows both locations and the single transfer event.

## AC-005 — Adjustment
- Given a user submits an Adjustment with non-zero quantity and reason, then a StockMovement of type Adjustment is created and the StockBalance is updated by that delta.

## AC-006 — Start Count & Save Pending
- Given a user starts a count for a location, when they save observations, then a Count record with status Pending and CountLineItems (expected and observed) is created.

## AC-007 — Reconcile Count
- Given an Approved Count with differences, when reconciled, then CountCorrection movements are created for each differing line and StockBalances are updated to match observed quantities; Count status becomes Reconciled.

## AC-008 — Movement History Immutability
- Given any movement exists, when viewed in UI, then no edit/delete affordance is present; corrections require new movements and all movements are shown in reverse chronological order.

## AC-009 — Valuation
- Given receipts with costs exist for a product, when valuation is requested, then weighted-average cost is computed deterministically from receipts and shown alongside product quantity and total value. Drill-down shows receipt-level cost lines.

## AC-010 — Users & Roles
- Given an Owner/Admin creates a Manager or Staff user, when new user logs in, then they can perform actions allowed by their role and are restricted from forbidden actions (e.g., Staff cannot manage users).

## AC-011 — Backup
- Given the system is running, then automated daily backups occur and an Admin can trigger a manual export. Backup artifacts can be validated by restoring to a test environment.

## AC-012 — Atomicity & Consistency
- Given concurrent operations on the same StockBalance, when operations occur concurrently, then balances remain consistent after operations finish (no lost updates), and conflicts are surfaced and resolvable.

## AC-013 — Error Handling
- Given network or server error during movement submission, when the operation fails, then user receives a clear error and state remains consistent (no partial movement applied).

## AC-014 — Reports
- Given inventory data exists, when viewing Low-Stock or Stock-by-Location report, then data matches computed StockBalance and valuation and filters work as specified.

---

## How to test
- Use a sandbox org with seeded products and locations.
- Execute scripted scenarios (Receive, Transfer, Issue, Count, Reconcile) and assert movement creation and balances.
- Include concurrency tests to validate AC-012.

---

Notes: Where "within 5s" or similar timing is used, adjust targets during technical design based on realistic infrastructure.
