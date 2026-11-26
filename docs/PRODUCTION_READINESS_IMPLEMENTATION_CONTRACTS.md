# Production Readiness Implementation Contracts

**Status:** Approved for implementation
**Approved:** 2026-11-11
**Scope:** Workstream A (operational readiness), B (independent inventory MVP), C (POS readiness)

This contract adds to the historical requirements and decisions. It does not rewrite them. The worktree was already dirty before this effort; preserve unrelated existing changes and data. Use disposable databases for tests.

## Product decisions

- Inventory must operate without sales. Implement the approved inventory loop: products and locations; opening stock, receipts, issues, adjustments, transfers, counts/reconciliation, immutable movement history, weighted-average valuation, low-stock and location reporting.
- D010a is approved and governs offline inventory operations over the earlier medium-confidence D011 online-first default. Support durable local events for sales, receipts, transfers, counts and adjustments. The server ledger is authoritative; device balances are provisional; sync is idempotent and conflicts remain visible for reconciliation.
- **Current-release scope clarification (2026-11-11):** Returns are out of scope for this release. Do not implement customer or supplier return workflows or queue return operations offline. Keep returns explicitly unsupported; this clarification supersedes the earlier D010a return capability for the current release.
- D014 is approved: Zimbabwe deployments require fiscalization through the separate TengaVFD boundary. Sale/payment/inventory status and fiscal status are independent. ZIMRA/device approval and production VFD connectivity must be verified before claiming compliance.
- New organizations default to USD and have one configurable currency. Lock the currency after the first stock movement or sale; do not convert or reinterpret history. Existing organizations with unknown currency require explicit confirmation before monetary operations.
- Employee is a distinct organization-scoped record, optionally linked one-to-one to a login User. User identity remains the authenticated security/audit actor; retain employee attribution separately. Deactivate/archive rather than deleting history.
- Paynow Zimbabwe supports hosted web redirect and mobile-money push. Credentials remain server-side. Redirects and notifications are untrusted until server-side payment verification.
- A Paynow sale stays pending and has no stock movement until the payment is verified. Then complete payment, sale and inventory movements atomically. An uncertain result remains pending and retryable. Till close is blocked while a session has unresolved Paynow attempts.
- Preserve D010a/U006 oversell behavior: warn and record/reconcile; do not reject a sale solely because the latest stock balance is insufficient.

## Shared architecture and API rules

- Retain FastAPI, SQLAlchemy, Pydantic, React/Vite, and Alembic. Domain rules belong in services; UI restrictions never replace backend authorization.
- Derive organization and authenticated actor from the current user. Scope every query and mutation to the tenant. Validate location, till, employee, session and product relationships server-side.
- New organizations receive a currency; legacy currencyless organizations cannot perform monetary operations until explicitly configured. Persist currency snapshots on financial records. Do not silently convert.
- Employee may exist without a login. Enforce at most one employee per user and same-organization linkage. Only an active, assigned authenticated user may operate a till.
- InventoryMovement is the append-only source of truth. Every movement records organization, product, signed quantity, movement type, location(s), authenticated actor, timestamp, reason/reference, and device/local identity when synced. A transfer has stable identity and atomically posts its source and destination effects. Count observations do not mutate stock until explicit reconciliation posts corrections.
- Offline events are persisted locally before the UI says “recorded.” Use durable browser IndexedDB/PWA storage, stable device/local IDs, explicit pending/synced/failed/reconciliation states, idempotent server application, and per-event acknowledgements. Never discard failed events or call provisional balances authoritative.
- Cash checkout validates an active till session and assignment; server-calculates prices/tax; atomically records sale, payment, stock movements and session cash effect. Idempotent retries do not duplicate records.
- Paynow initiation records a pending payment attempt and sale. Only server verification of provider reference, amount, currency and terminal status can settle it and post stock. Duplicate/late callbacks are safe; timeout/unknown status is not success.
- Define a versioned POS-to-TengaVFD HTTP contract. Fiscal numbers/status may only come from VFD. No mock success in product workflows. Local contract tests are allowed; live compliance remains blocked until the external service and deployment requirements are verified.
- Preserve the existing HTTP error envelope (`detail`, `status_code`, `type`); new endpoints use explicit errors: 401 unauthenticated, 403 forbidden, tenant-safe 404, 409 conflict/replay/state, 422 invalid input, 503 provider unavailable/uncertain.

## Data and migration constraints

Required domain additions/constraints include organization currency and regional settings; Employee and optional User link; product unit/category/minimum; receipt cost; count and transfer identity; offline device/local id and reconciliation state; session-linked sale; payment attempts and currency snapshots; receipt/reprint audit data; and independent fiscal state.

Lead owns shared model registration and the Alembic chain. Contributors submit schema proposals; migrations are integrated sequentially into one head. Never use `create_all()` as a production upgrade. Preserve existing rows. A migration must not assign USD to historical monetary records without operator confirmation. Test fresh install and upgrade on isolated SQLite and PostgreSQL before release. Back up before production migration; never downgrade away live payment, fiscal, inventory or audit history.

## Dependency graph and ownership

1. Approved contract and baseline.
2. Lead integrates shared models/contracts and a single ordered migration chain; Infrastructure independently repairs installation/migration/backup scripts in its owned files.
3. Parallel domain slices: administration/employees; products/import/export; inventory/count/valuation/offline reconciliation; tills/sessions; checkout/Paynow/VFD.
4. Frontend integrates only tested API contracts and adds reachable workflows/PWA state.
5. Independent QA verifies permissions, tenant isolation, migrations, concurrency, retries, persistence and recovery.
6. Documentation/release updates follow verified behavior.

| Owner | Exclusive implementation boundary |
|---|---|
| Lead/integration | Shared model registration, Alembic history, `src/main.py` router registration, common error/authorization contracts, integration and decisions |
| Infrastructure | Docker/Compose, deployment/migration/backup/health scripts, installation tests/docs; no domain model/router edits |
| Administration | New employee/settings modules and isolated admin UI; shared models/migrations requested from Lead |
| Product/import | Product/category/unit/import/export services, schemas, routes and tests; no central registration edits |
| Inventory | Inventory operations/count/transfer/valuation/report modules and tests; no central registration edits |
| Till/session | Till/session service/API modules and tests; shared schema changes requested from Lead |
| POS/payment/fiscal | Payment/Paynow/VFD adapters and isolated routes/schemas/checkout modules/tests; shared sale/session schema changes requested from Lead |
| Frontend/PWA | Navigation, page composition, IndexedDB/service worker and component tests; cannot change backend contracts unilaterally |
| QA/security | Isolated integration/E2E/security/concurrency tests only; defects are handed back to owning agent |
| Documentation | README, operator manuals, API/test/release docs; no source edits |

Agents must not modify files owned by another workstream. Lead alone serializes migrations and central registration. If work requires shared-file edits, submit a focused integration handoff rather than editing concurrently.

## Minimum integration acceptance

- Fresh and upgrade installs reach one Alembic head; health/readiness pass; restart preserves records; PostgreSQL backup restores into an isolated database with verified representative data.
- Admin configures an organization, currency, employees, roles, locations and tills; inactive accounts lose access and cross-tenant operations fail.
- CSV templates, preview, row errors, atomic product/opening-stock import, import history and product/inventory export work without partial commits.
- Without any sale, a user can receive, issue, adjust, transfer, count/reconcile, inspect balances/history, weighted-average value and low-stock/location reports.
- Offline event survives browser/device restart, is visibly provisional, syncs idempotently, and reaches explicit reconciliation state without lost or duplicated movements.
- Till sessions record opening/expected/actual cash and variance; a sale cannot be detached from a valid session; unresolved Paynow blocks close.
- Cash sale completes once. Paynow hosted and push flows remain pending until verified, then settle and deduct stock once. Receipt/reprint/void/refund are audited.
- Fiscal state remains separate; no fake acknowledgement/number. Test-double contract passes; Zimbabwe production readiness is explicitly gated on real VFD and regulatory verification.
- Backend, frontend (including all discovered tests), PostgreSQL integration and end-to-end scenarios run in CI with failures reported, not suppressed.
