# Tenga Inventory — Feasibility Study

## Executive summary
Tenga Inventory's intent (inventory-first, progressive complexity) is technically and operationally feasible for an MVP that supports institutional and small grocery pilots. Key technical choices (record movement costs; compute weighted average valuation; append-only movement history) are feasible without introducing enterprise complexity. Economic and operational assumptions require pilot validation.

## Technical feasibility
- Core model: movement-based history plus derived current balances. This allows traceability and future valuation methods. (Recommended: preserve movement records; compute current quantity from movements or maintain derived balances with movement audit.)
- Costing: store per-receipt movement cost; compute weighted-average valuation for UI and basic reports (Decision D004).
- Scale: MVP must handle many SKUs (grocery) and frequent movements; performance testing required during implementation.
- Offline: MVP will assume online operation; offline sync is a medium-term enhancement (Unknown — see register).
- Data durability: append-only movements, transactionally consistent updates, and backup/export/import facilities are required for pilot confidence.
- Integrations: postpone POS/accounting integrations; design clear data contracts to allow future decoupled integrations.

## Economic feasibility
- Potential customers: small shops and institutions. Revenue model to be validated (subscription for small shops; institutional pricing for universities).
- Value proposition: reduces time spent reconciling stock, prevents stockouts, improves accountability — measurable in reduced losses and labor time.
- Competitors: spreadsheet-based workflows, POS systems with inventory (square, Vend, Loyverse), basic inventory apps. Tenga differentiates by focusing on inventory-first simplicity and progressive complexity.

## Operational feasibility
- Pilots: one institutional and 2–5 grocery shops provide diverse operational learning.
- Onboarding: must be lightweight — importing opening balances should be supported via CSV but can be manual initially.
- Support: initial hand-holding for pilot sites; iterative UX refinement.

## Market feasibility
- There is appetite for simpler inventory tools among small businesses and non-sales organizations. The pilot combination validates cross-market product-market fit.

## Risks and mitigations
- Risk: pilot sites do not adopt the workflow. Mitigate with close onboarding and rapid iterations.
- Risk: weighted average valuation not accepted by some users. Mitigate by exposing clear explanation and making cost optional.
- Risk: performance at scale. Mitigate with benchmarks and optimized data structures.

## Conclusion
Proceed with MVP development, validating technical performance and economic viability during pilot phase. Reserve offline sync, complex roles, and accounting integration for post-MVP work unless pilots demonstrate urgent need.
