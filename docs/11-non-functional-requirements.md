# Tenga Inventory — Non-functional Requirements (NFR)

## Purpose
This document captures qualities the system must have: performance, reliability, availability, security, usability, maintainability, portability, and offline considerations. Each entry indicates priority: Required Now, Required Later, Desired, Unknown.

---

## Performance
- NFR-PERF-001 (Required Now): UI response for primary screens (Products list, Product detail, Receive form) should be < 1.5s for working datasets up to 10k SKUs and typical movement rates for a single site. Pagination and server-side filtering supported.
- NFR-PERF-002 (Required Later): Support multi-site aggregated queries with latencies under 2s for aggregated dashboards at up to 50k SKUs.

Rationale: Pilot grocery shops may have thousands of SKUs; perceived slowness kills adoption.

---

## Reliability & Durability
- NFR-REL-001 (Required Now): All stock-changing operations (StockMovement creation + StockBalance update) must be atomic. Either the movement and balance update succeed, or both fail and roll back.
- NFR-REL-002 (Required Now): Daily automated backups with retention policy (configurable, default 30 days). Manual export available to Admin.
- NFR-REL-003 (Required Later): Support point-in-time restore for audited incidents (post-MVP).

Rationale: Auditability and pilot trust require no partial writes and recoverable data.

---

## Consistency & Concurrency
- NFR-CON-001 (Required Now): Strong consistency for StockBalance: after a confirmed movement, queries must reflect new balances. Use database transactions and pessimistic/optimistic locking as appropriate.
- NFR-CON-002 (Required Now): Detect and prevent lost updates (e.g., two concurrent transfers from same source) via transactional constraints and appropriate conflict handling.

Rationale: Stock integrity is critical; concurrent operations must not silently corrupt balances.

---

## Offline & Sync
- NFR-OFF-001 (Unknown/Deferred): MVP is online-first. Offline operation is out-of-scope for MVP; clarify connectivity expectations with pilots before committing.
- NFR-OFF-002 (Required Later): If offline support is prioritized by pilots, design must include conflict resolution rules, causal ordering for movements, and explicit sync/reconciliation UX.

Rationale: Offline capability substantially increases complexity and must be validated.

---

## Security
- NFR-SEC-001 (Required Now): User authentication (password-based at MVP; consider 2FA later). Secure password storage (bcrypt or equivalent).
- NFR-SEC-002 (Required Now): Role-based authorization enforcing three roles (Owner/Admin, Manager, Staff) across all UI and APIs.
- NFR-SEC-003 (Required Now): Data-in-transit encrypted (TLS). Sensitive data stored encrypted where applicable.
- NFR-SEC-004 (Required Later): Audit logging and access logs with retention policy.

Rationale: Organizations must trust the system with operational critical data.

---

## Usability & Accessibility
- NFR-UX-001 (Required Now): Core flows (Receive, Issue, Transfer, Count) should be completable with minimal fields and with inline validation messages.
- NFR-UX-002 (Required Now): Accessibility baseline: keyboard navigation and semantic labels; color contrast meets WCAG AA minimum.
- NFR-UX-003 (Desired): Localized UI (i18n) and simple language support.

Rationale: Adoption depends on usability for non-technical staff.

---

## Maintainability & Observability
- NFR-MNT-001 (Required Now): Modular architecture with clear domain boundaries (Products, Locations, Movements, Counts, Users) to ease future extensions.
- NFR-MNT-002 (Desired): Metrics and basic dashboards for system health (errors, failed transactions, queue lengths).

Rationale: Iterative development and pilot feedback require rapid change and safe operation.

---

## Portability & Deployment
- NFR-DEP-001 (Required Now): Platform should deploy as a web application (hosted SaaS or self-hosted). Provide database export for on-premise pilots.
- NFR-DEP-002 (Desired): Containerized deployment (Docker) for predictable environments.

---

## Scalability
- NFR-SCL-001 (Required Later): Design for horizontal scaling of read queries (caching, read replicas). Writes must remain strongly consistent for movements.

---

## Observability of Business Properties (Domain-level NFRs)
- NFR-DOM-001 (Required Now): Movement history must be immutable and fully queryable by product, location, date, type, and user.
- NFR-DOM-002 (Required Now): Valuation computation must be deterministic and reproducible from stored movement costs.

---

## Acceptance of NFRs
- Each NFR should be validated during acceptance testing with concrete scenarios and load tests where applicable. NFRs marked "Required Now" must be satisfied before pilot deployment.

