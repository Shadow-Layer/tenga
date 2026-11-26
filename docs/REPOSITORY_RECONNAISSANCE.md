# Tenga Inventory POS — Repository Reconnaissance & Design Audit

**Inspection date:** 2026-11-07  
**Scope:** Current working tree, including source, configuration, deployment assets, existing documentation, and tests.  
**Important scope finding:** This repository is `tenga-inventory`, an inventory and point-of-sale (POS) application. It contains no portfolio site, portfolio project catalogue, case-study pages, or portfolio content model. This report documents the repository that is actually present; it is not a portfolio design audit.

## Current release-status note (2026-11-13)

This note supersedes dated test counts and completion labels below for current
readiness; those historical records are retained. The root
[`README.md`](../README.md) is now the concise release-facing overview.

- A clean Python 3.14 install from `requirements.txt` passed the full backend
  suite (379 passed, 14 skipped) against an isolated in-memory database.
  Frontend tests (18), type-checking, a Vite 7 production build, `npm audit`,
  and `pip-audit` passed with zero dependency advisories.
- The frontend on `127.0.0.1:80` was rebuilt from current source and verified
  in a browser. The sign-in screen has no shared demo account hints, the
  browser reported no console errors, and the manifest, service worker, and
  health endpoint were served successfully.
- A disposable Compose installation completed setup and a cash sale. After
  restarting only its API and PostgreSQL containers, the organization, users,
  products, sale, inventory movements, and till-session counts remained
  unchanged. The opt-in disposable-PostgreSQL backup/restore/migration test
  also passed after the latest migration.
- Production acceptance remains pending: native browser network-offline,
  reopen and inventory-sync/count-conflict scenarios; a representative
  populated-database upgrade; and live Paynow/FDMS/ZIMRA provider
  authentication, certification, and acknowledgements have not been verified.
- The existing `tenga-api` container still runs an image created on 2026-11-07.
  An unauthenticated organization-detail request returns 200 there, while the
  same request against the isolated current-source API returns 401; current
  source requires authentication. The old API also still runs PyJWT 2.8.0,
  python-jose 3.3.0 and ecdsa 0.19.2, which the dependency audit flags; current
  requirements remove python-jose and update the remaining vulnerable pins.
  The API is loopback-bound and was not restarted or replaced to preserve
  existing data and configuration. Do not expose it externally before a
  controlled redeploy.
- The existing host `tenga-postgres` container still publishes port 5432 on
  all interfaces. The repository Compose configuration binds PostgreSQL to
  loopback, but the existing container was not recreated; restrict its
  exposure before external use.
- The Compose API image runs `alembic upgrade head` before `uvicorn`; the
  migration script is an explicit wrapper for a running API/PostgreSQL stack.
  The current repository Compose configuration binds both API and PostgreSQL
  host ports to loopback. The existing PostgreSQL container still uses an
  older all-interface binding described above; updating that live container
  requires a controlled redeploy. Compose configuration is not production
  certification.
- `tests/test_production_scripts.py` uses mocked Docker/Compose commands for
  its normal script tests. A separate disposable-PostgreSQL path is opt-in.
  The latest disposable-PostgreSQL migration/backup/restore path passed; this
  does not establish a representative populated-database upgrade or production
  acceptance.
- The setup manual's Step 1 and product import descriptions differed from
  current source. The wizard uses a setup-import endpoint whose CSV contract
  differs from the newer catalog-import API; the discrepancy and evidence-
  backed corrections are recorded in
  [`INITIAL_SETUP_WIZARD.md`](INITIAL_SETUP_WIZARD.md).

## Evidence and confidence

- **High:** Directly established from current source, configuration, or tracked files.
- **Medium:** Supported by the implementation but dependent on runtime or deployment behavior not exercised during this inspection.
- **Low / unverified:** Appears in existing status/design documentation but was not revalidated.

The original 2026-11-07 reconnaissance was a static, read-only inspection; no
application code, dependencies, databases, or build outputs were changed during
that initial audit. The later verification and implementation work is
summarized in the current release-status note above. The local `.env` file was
not opened; do not treat this report as a review of its values.

## 01 — Executive Overview

Tenga Inventory POS is a mixed Python/TypeScript application. The backend is a FastAPI REST API backed by SQLAlchemy, SQLite for development by default, PostgreSQL support, and Alembic migration files. The frontend is a Vite-built React/TypeScript SPA styled primarily with Tailwind utilities. Docker Compose describes PostgreSQL, API, and Nginx-served frontend services.

The backend has domain models and service modules for organizations, users, locations, products, inventory movements, sales, till sessions, subscriptions, offline synchronization, and fiscal integration. The visible React application is much narrower: `src/App.tsx` provides login and a quick-start/testing dashboard. Other screens under `src/components/` are not mounted by the app entry point or routed to. Several use mock or hard-coded data. Therefore, a feature existing as a component, service, test, or design specification does not establish that it is part of an end-to-end user workflow.

**Maturity assessment (medium confidence):** Backend breadth is beyond a simple prototype, but frontend integration and API-contract alignment are incomplete, quality status is not current, and deployment documentation contains contradictions. Do not treat the repository as a finished POS product or a portfolio foundation without first confirming the intended target and resolving the high-priority issues in §11.

## 02 — Repository Map

| Path | Responsibility and observations |
|---|---|
| `src/main.tsx` | React DOM bootstrap; wraps `App` in `QueryClientProvider`. |
| `src/App.tsx` | The only top-level frontend screen: login, admin quick actions, or a non-admin quick-start dashboard. No router is configured. |
| `src/api.ts`, `src/stores.ts` | Axios API wrappers/types and Zustand auth, selection, and POS-cart stores. There are also direct `fetch` calls in `App.tsx` and `AdminQuickStart.tsx`. |
| `src/components/` | Inventory, product, checkout, tax, payment, receipt, customer, offline and other workflow components. Most are not mounted from `App.tsx`; inspect each for static data before treating it as production behavior. |
| `src/design/tokens.ts`, `src/index.css` | A token object and small global CSS base. The token object is not used as a shared component API in the inspected UI. |
| `src/main.py` | FastAPI application entry point (`uvicorn src.main:app`), middleware, health endpoints, router registration, and startup database initialization. |
| `src/routers/` | HTTP endpoints for authentication, organizations, users, products, locations, inventory, sales, tills, subscriptions, and sync. |
| `src/schemas/` | Pydantic request/response contracts. |
| `src/models/`, `src/database/` | SQLAlchemy entities, engine/session configuration, and database helpers. `Stock` is described as a cache; `InventoryMovement` is the signed movement ledger. |
| `src/services/` | Business logic for inventory, sales, tills, subscriptions, sync, adjustment reasons, and fiscal formatting/queue/client. |
| `src/security/` | JWT token handling, password handling, and authorization dependencies. |
| `src/client/` | A Python HTTP client, local-storage/offline management, connectivity and synchronization. It is not visibly wired into the React app. |
| `src/migrations/`, `alembic.ini`, `scripts/migrate.py` | Alembic configuration, two migration revisions, and migration helper. |
| `tests/` | Pytest backend tests and two TypeScript checkout tests. Existing documentation reports test failures, but those numbers were not rerun. |
| `docs/` | Existing requirements, design, implementation, deployment, and testing documentation. `docs/INDEX.md` is the navigation index. |
| `Dockerfile`, `Dockerfile.frontend`, `docker-compose.yml`, `nginx*.conf` | Container builds, service topology, reverse proxy and static SPA hosting. |
| `package.json`, `package-lock.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js` | Frontend dependencies and build/type-check configuration. |
| `requirements.txt`, `setup.py` | Python dependency and package metadata. |
| `index.html`, `vite.svg` | Minimal SPA shell and a generic Vite-derived favicon; no project/media asset library was found. |

The root `README.md` now provides a release-facing overview. No tracked CI workflow or frontend `assets/` or `public/` content collection was found in the inspected inventory. The documentation set is extensive but has conflicting age/status statements; see §§9 and 11 and the current release-status note above.

**Working-tree caveat:** At inspection time, the tree already contained modified/deleted files in `dist/`, a modified `tenga-test.db`, newly untracked built assets, and untracked checkout components (`src/components/CheckoutFiscalIntegration.tsx`, `CheckoutFulfillment.tsx`, `CheckoutVoidReturn.tsx`). These were pre-existing user changes and were not altered. Treat statements about the current tree as including those uncommitted changes; they are not established as part of the committed baseline.

## 03 — Operating Philosophy

### Documented principles

`docs/PHASE_4_DESIGN_SYSTEM.md` states these principles: progressive complexity, operational clarity, visible offline/sync state, inventory usefulness independent of POS, simple presentation with rigorous behavior, and predictable interaction. `docs/00-implementation-state-current.md` describes offline overselling as permitted and reconciled later, subscription grace/limited states, and optimistic use of cached subscription state.

### Observed behavior

- The authenticated UI distinguishes admin quick actions from a guided setup/testing flow in `src/App.tsx`.
- Inventory screens are designed around summary cards, search, status badges, and desktop table/mobile card variants (`src/components/InventoryOverview.tsx`).
- Checkout is split into cart, payment, and customer components, with online/offline indication (`src/components/Checkout.tsx`).
- The backend uses organization-scoped entities and an append-only inventory movement record (`src/models/entities.py`, `src/services/inventory_service.py`).
- The source does **not** implement the complete documented design system as a shared component library, and the isolated UI screens are not connected into a navigable product experience.

### Inference and recommendation

The intended product experience appears to prioritize operational workflows and recoverability over portfolio storytelling or public marketing. That inference is supported by the domain and design documents, not by an end-to-end production UI. Preserve clear transaction state, organization boundaries, auditability, and offline status when completing the product. Do not infer a public-facing portfolio purpose from this repository.

## 04 — Design System

### Visual identity in source

- **Color:** Neutral gray surfaces and text; blue/indigo primary actions; green success/available; yellow/amber caution/offline; red destructive/error. Current screens use Tailwind palette classes directly, including both `blue-*` and `indigo-*`.
- **Tokens:** `src/design/tokens.ts` defines a custom primary ramp (`#3e64ff` at 500), neutral/status colors, spacing, and sizing. `tailwind.config.js` defines another palette (`primary: #2563eb`, success/error/warning) and source components mostly use stock Tailwind colors instead. No token imports were found in UI components.
- **Typography:** Global system stack in `src/index.css`; no local web fonts, font files, or `@font-face` declarations were found. Tailwind utility classes supply weight and size hierarchy.
- **Surfaces:** White cards on light-gray or light blue/indigo backgrounds, thin gray borders, rounded corners, and occasional subtle shadows. No recurring glass, blur, or elaborate gradient system; the login/dashboard uses a blue-to-indigo background gradient.
- **Icons/media:** `lucide-react` icons plus occasional Unicode/emoji status marks. The only image-like brand asset found is the generic `vite.svg` T favicon. No product screenshots, gallery, or visual-content model exists.
- **Spacing/layout:** Tailwind spacing utilities, centered max-width containers (`max-w-6xl`, `max-w-4xl`, etc.), card padding, and responsive grids. Actual breakpoints differ between screens; there is no centralized layout primitive.

### Component and interaction standards

The table below distinguishes rules already evidenced in code from recommendations needed for consistency.

| Rule | Evidence / where it applies | Status |
|---|---|---|
| Use the system font stack; avoid adding a web font without a real product need. | `src/index.css`; all frontend screens. | Mandatory |
| Use light neutral surfaces and reserve semantic color for status/actions. | `src/components/InventoryOverview.tsx`, `AddProduct.tsx`, `Checkout.tsx`; `src/design/tokens.ts`. | Mandatory; consolidate actual blue/indigo choices before expanding |
| Compose layout with existing Tailwind utilities and responsive grids/cards. | `InventoryOverview.tsx`, `AddProduct.tsx`; `tailwind.config.js`. | Mandatory |
| Keep labels, validation, loading, empty and error states explicit. | Partially present in `AddProduct.tsx`, `InventoryOverview.tsx`; system-state expectations in `docs/PHASE_4_DESIGN_SYSTEM.md`. | Mandatory; current coverage is inconsistent |
| Every control must have a visible keyboard focus state and an accessible name; associate each input with a label. | Some `focus:ring-*` utilities and form labels exist; several inputs lack labels and icon-only buttons lack names. | Mandatory; current code has gaps |
| Preserve touch-sized controls and provide a narrow-screen layout for transactional flows. | Product screens use some `h-12`; `Checkout.tsx` uses a desktop flex layout and fixed `w-96` panel. | Mandatory |
| Use `lucide-react` or an existing semantic text/status pattern; do not add icon packages for one control. | Current UI dependencies and components. | Mandatory |
| Add a shared component or token abstraction only when multiple live screens need it. | Tokens and component specs currently exist without shared UI primitives. | Optional / evidence-driven |
| Use animation only to communicate state; respect reduced-motion preferences. | Existing code uses utility transitions/spinner, with no detected reduced-motion policy. | Recommended |

### Implemented vs specified

`docs/PHASE_4_DESIGN_SYSTEM.md` is a specification, not proof of implementation. It describes shared Buttons, Inputs, Tables, Modals, Toasts, status indicators, a token CSS layer, detailed accessibility standards, and breakpoints that are not present as a shared component system. Current UI is mostly screen-local JSX/Tailwind. The spec also disagrees with source palette values and some sizing assumptions. Use source behavior as the current implementation baseline, and use the spec only as a proposal to reconcile—not as evidence that those components already exist.

## 05 — Technical Architecture

### Runtime and data flow

1. `src/main.tsx` creates the React root, wraps the app in `React.StrictMode` and TanStack Query's provider, and imports `src/App.tsx`.
2. `App.tsx` owns login state locally and persists token/user values to `localStorage`; other modules offer Zustand stores for auth, selected organization/location/till, and cart state. These state paths are not consistently unified.
3. `src/api.ts` creates an Axios client, reads `VITE_API_URL` or defaults to `http://localhost:8000`, attaches persisted auth, and defines endpoint wrappers. `App.tsx` and `AdminQuickStart.tsx` also issue direct `fetch` calls.
4. The frontend talks to FastAPI routers registered from `src/main.py`; routers validate with Pydantic schemas and call SQLAlchemy models/services.
5. Backend persistence uses a configured SQLAlchemy engine and `get_db()` dependency. SQLite and PostgreSQL are supported in configuration.

### Frameworks and dependencies

- Frontend: React 19, TypeScript 5, Vite 5, Tailwind CSS 4/PostCSS, React Router DOM (installed but not used in the inspected source), TanStack React Query (provider installed, no query-hook usage found), Zustand, Axios, and Lucide React.
- Backend: FastAPI, SQLAlchemy, Pydantic, Alembic, PyJWT/python-jose, bcrypt, requests, pytest, and PostgreSQL driver. `requirements.txt` uses a mixture of exact and lower-bounded versions.
- No CMS, static-site framework, project-content generator, analytics integration, or payment gateway was identified.

### Architecture constraints and conventions

- Preserve the current layered backend: router → schema/service → model/database. Keep organization checks server-side and derive trusted actor/tenant identity from authenticated context.
- Backend uses snake_case modules/functions and SQLAlchemy/Pydantic classes; frontend uses PascalCase component files/exports, camelCase variables, and relative imports (with `@/` alias configured).
- There is no active frontend route hierarchy or shared app shell. A feature screen must be deliberately mounted/wired; creating a component alone does not make it reachable.
- `src/main.py` calls `init_db()` (`Base.metadata.create_all`) at startup even though Alembic migrations exist. `create_all` is not migration execution; production rollout must use the migration workflow explicitly.
- Build scripts are `npm run build` (`tsc && vite build`), `npm run type-check`, and `npm test` (`vitest`). Vite emits source maps to `dist/`. The frontend Docker build uses `npm install`; its shell line `npm run build && cp ... || true` can mask a failed frontend build.
- Docker Compose configures Postgres 16, FastAPI, and Nginx. Nginx proxies `/api/`, `/docs`, `/redoc`, and `/openapi.json`; its SPA fallback serves `index.html`.
- `scripts/verify-deployment.sh` is not a read-only check: it builds/starts Docker services, may initialize a database, runs tests, and writes artifacts. Do not use it as an inspection-only validation.

## 06 — Content and Data Architecture

There is no portfolio/project content source. Product data is database-backed, not a portfolio-style static project list or CMS.

The main persisted domain objects are in `src/models/entities.py`: `Organization`, `User`, `Location`, `Product`, `Till`, `Subscription`, `Stock`, `InventoryMovement`, `Sale`, `SaleItem`, and `TillSession`. `Product` includes organization, SKU, name, optional description/category/barcode, price/cost, and active state. `InventoryMovement` records signed quantity, reason, references, actor, and timestamps; current quantity is computed from movements, while `Stock` is also described as a derived cache. Product/order metadata is enforced partly through database constraints and partly through schema/service validation.

Listings are API-backed and paginated in backend contracts, but the frontend response assumptions do not consistently match backend schemas. For example, `productsAPI_v2.list` and `InventoryOverview` expect `response.data.data`, while `ProductListResponse` in the backend uses `items`. The current inventory screen also fabricates `stock`, `status`, and `lastUpdated` with `Math.random()` rather than using stock endpoints. Product detail/history and stock-adjustment screens contain hard-coded example records.

**External integrations:** PostgreSQL is supported; ZIMRA fiscal client, formatter, and queue modules exist (`src/services/zimra_client.py`, `fiscal_formatter.py`, `fiscal_queue.py`) with related tests. Their end-to-end connection to the sale workflow was not established from the inspected entry points. No customer API, live card processor, analytics service, or CMS was identified. Checkout customer/payment screens use mocked data/behavior.

## 07 — Contribution Standard

The original request's project-documentation fields (portfolio title, case study, screenshots, demo/repository URLs, project outcomes, and project ordering) are **not applicable** to this repository. Do not invent a project catalogue or achievements.

For future application features, record the following in the feature ticket/PR and directly related documentation:

**Required**
- User/business problem, actor/role, and intended workflow.
- Data ownership/organization scope and source of truth.
- API contract and validation/error behavior, if data crosses the backend boundary.
- Offline/online and retry/idempotency behavior, if the workflow can operate offline.
- Security and authorization rules.
- Responsive and keyboard-accessible states.
- Tests covering success, validation, failure, and tenant boundaries as relevant.

**Optional, when applicable**
- Screens/diagrams, migration or rollout notes, external integration details, metrics/telemetry, support and recovery behavior, known limitations, and follow-up work.

**Narrative structure:** Context → user workflow → data/API contract → implementation boundaries → failure/offline behavior → accessibility/responsive behavior → verification → rollout/limitations. This communicates engineering work without presenting unverified outcomes as facts.

## 08 — Extension Guide

### Add or change a backend capability

1. Confirm the domain behavior and relevant existing decisions in `docs/implementation-business-rules.md`, `docs/implementation-decisions-u006-u007-u008.md`, and `docs/00-implementation-state-current.md`; check source when documentation disagrees.
2. Define/update SQLAlchemy models in `src/models/` and Pydantic contracts in `src/schemas/`.
3. Put business rules in an existing or narrowly scoped service under `src/services/`; keep tenant/actor authorization in the route/dependency boundary.
4. Add or update a router under `src/routers/`, then register it in `src/main.py` if needed.
5. Add an Alembic revision in `src/migrations/versions/` and document rollout. Do not rely on startup `create_all()` to migrate an existing database.
6. Add pytest coverage, including authorization/organization isolation, invalid inputs, persistence, and idempotency where applicable.
7. Update `API_DOCS.md` and the relevant implementation docs only after verifying the actual contract.

### Add or connect a frontend screen

1. Trace the existing API and store patterns in `src/api.ts` and `src/stores.ts`; verify request paths, response shapes, units, and role expectations against the backend.
2. Implement screen states (loading/empty/error/success/offline), semantic labels, focus visibility, and responsive layouts using current Tailwind and Lucide dependencies.
3. Wire the screen from the actual application entry/navigation. React Router is present in dependencies but no routes are currently configured.
4. Avoid mock/hard-coded data in production flows. If mock data is intentionally used, label it clearly and isolate it from live API logic.
5. Exercise the appropriate type-check/build and targeted tests only after accounting for the existing modified build/database files; document what was and was not validated.

## 09 — Quality Baseline

### Confirmed from source

| Area | Finding | Confidence |
|---|---|---|
| Reachability | `src/App.tsx` imports only `AdminQuickStart`; no router is configured. Most screen components are not part of the reachable UI. | High |
| Data realism | Inventory status/quantity is random; product detail/history and stock adjustment values are hard-coded; customer lookup and payment are mocked. | High |
| API contracts | Product list envelope expected by frontend differs from backend `items` envelope. Several client wrappers omit `/api/v1` or use paths that do not match registered routes. | High |
| Inventory presentation | Inventory screen does not use a real stock query and labels random values as stock/status. | High |
| Amount units | Checkout display/payment code divides totals by 100, while backend product/sale schemas and database use currency-valued decimals. The contract is not explicitly reconciled. | High for mismatch; exact business impact needs runtime/owner confirmation |
| Tax | `Checkout.tsx` hard-codes 15% and itself labels it a placeholder. | High |
| Accessibility | Some form labels and focus rings exist, but many controls use placeholders without associated labels; icon-only actions lack accessible names; custom dialogs do not show focus trapping/Escape handling; no consistent live announcement pattern was found. | High |
| Responsive behavior | Inventory has table/card variants; checkout uses a fixed-width summary column with no narrow-screen stack in its wrapper. | High |
| Metadata/SEO | `index.html` has title and viewport but no description/social metadata; this is an operational app, not an SEO-oriented public site. | High |
| Assets/performance | No image gallery or local font assets; Vite source maps are enabled. Runtime bundle size/Core Web Vitals were not measured. | High / unmeasured |
| Build reliability | Frontend Docker command ends with `|| true`, which can conceal failure in the preceding build/copy chain. | High |
| Migrations | Alembic files exist but application startup calls `create_all()` rather than applying Alembic revisions. | High |

### Security and operational risks (static findings; no exploit testing)

- `src/routers/inventory.py`'s discrepancy endpoint has no authenticated-user dependency and accepts `organization_id` from the request; this conflicts with the otherwise tenant-scoped pattern and needs security review before exposure.
- Subscription and organization endpoints include operations without a current-user/role dependency. Confirm intended public bootstrap/admin policy and enforce it consistently.
- `src/routers/sales.py` accepts `cashier_id` and commit `user_id` from request data rather than deriving the actor from the authenticated user. Verify and correct the trust boundary before production use.
- `src/config.py` has a development JWT fallback and wildcard CORS default. Production checks reject the known default JWT value, but deployment configuration and allowed origins still require explicit review. Compose includes a fallback database password; production must override it.
- The frontend stores access tokens in `localStorage`; this increases exposure if a script-injection defect is introduced. No CSP was found in the inspected Nginx configuration. Do not treat transport/security headers as a substitute for application-level controls.
- Demo credentials are displayed directly in the login UI (`src/App.tsx`) and appear in setup documentation; confirm they are test-only and never seed a production deployment.

### Test status

Existing docs (`docs/testing-summary-status.md`, dated October 8, 2026) report **98 passed, 18 failed, 13 skipped**, but those values sum to 129 rather than the stated 173 total, and other docs report different totals. Treat all historic counts as stale/unverified. The two frontend tests import Testing Library/Jest APIs, while the package manifest declares Vitest and does not declare those test packages or a Vitest setup; the current frontend test command is therefore unverified and likely needs configuration/dependency reconciliation. No tests or builds were run in this audit.

## 10 — Development Guardrails

1. Inspect source and current working-tree state before changing files; preserve unrelated user changes.
2. Treat this as an inventory/POS app, not a portfolio. Do not add a portfolio catalogue or case studies unless product ownership explicitly changes scope.
3. Reuse the current React/TypeScript/Tailwind, Axios/Zustand, FastAPI/Pydantic/SQLAlchemy patterns. Avoid new dependencies and abstractions without a concrete need.
4. Keep business rules in backend services and trusted tenant/actor enforcement on the server. Never trust a client-supplied organization, cashier, or audit actor ID without authorization.
5. Align every frontend endpoint and response type with `src/main.py`, its router prefix, and the corresponding Pydantic schema. Do not copy stale API documentation blindly.
6. Keep financial units, tax behavior, and rounding explicit and consistent across UI, API, persistence, receipts, and fiscal submissions.
7. Do not present mock, random, or hard-coded data as real inventory, customers, payment outcomes, or audit history.
8. Wire new screens into the actual application flow; a component file by itself is not a shipped feature.
9. Preserve narrow-screen usability, visible focus, semantic labels, accessible names, keyboard-operable dialogs, and clear async/error states.
10. Use Alembic for schema evolution; document migration/rollback and do not assume `create_all()` upgrades existing production schemas.
11. Do not use the deployment verification script for read-only inspection. It changes container/database/build/test state.
12. Do not run broad tests/builds against this pre-existing dirty tree without understanding that test fixtures can drop and recreate `tenga-test.db` and Vite writes `dist/`.
13. Do not claim test, performance, accessibility, browser-compatibility, or deployment success without running the corresponding check and recording its exact scope.
14. Update the nearest API, business-rule, deployment, and testing documentation when a change alters those contracts.

## 11 — Technical Debt & Recommendations

**P0 — Confirm repository/scope.** The requested portfolio does not exist in this workspace. The report now covers the inventory/POS repository by explicit clarification; a portfolio audit requires the correct repository.

**P1 — Establish one trustworthy API contract.** Reconcile endpoint prefixes, route definitions, and response envelopes across `src/api.ts`, `src/routers/`, schemas, `AdminQuickStart`, `API_DOCS.md`, and `openapi.json`. Prioritize real inventory reads and product listing before treating the frontend as operational.

**P1 — Review authorization boundaries.** Secure discrepancy and subscription/organization operations as intended; derive sale/audit actors from authenticated identity; verify all organization-scoped reads/writes. Add regression tests before production use.

**P1 — Define money/tax behavior.** Agree on major-unit vs minor-unit representation, currency code, tax rules, precision, and fiscal receipt format. Remove placeholder tax and reconcile client/backend contracts before checkout is relied on.

**P1 — Make migrations authoritative.** Decide whether startup should migrate or deployments should run explicit Alembic commands; ensure startup never silently leaves an existing schema behind. Remove build-success masking from the frontend container build.

**P1 — Restore a verifiable quality baseline.** Fix stale test counts, make Vitest/testing-library configuration coherent, identify the actual failing tests, and add an automated CI check. Avoid claims based only on dated status documents.

**P2 — Connect or explicitly defer screens.** Decide which components are product scope, add navigation and real data adapters, and mark prototypes clearly. The current component directory is not a complete application experience.

**P2 — Reconcile visual guidance with implementation.** Choose one semantic palette/token source, either implement or retire the unused token/spec abstractions, and apply accessible patterns consistently. Do not add a component library solely to match the design document.

**P2 — Refresh developer documentation.** `API_DOCS.md`, `SETUP_GUIDE.md`, `docs/INDEX.md`, implementation reports, and deployment verification instructions have contradictory endpoint, test, and maturity claims. Prefer verified source/OpenAPI and current command output over old prose.

## 12 — Open Questions

1. Was a different repository intended for the original portfolio audit?
2. Which frontend screens are meant to be production workflows versus design prototypes?
3. What is the canonical API base path and list response envelope? Which checked-in `openapi.json` matches current routers?
4. Are monetary values stored/sent in major units or integer minor units, and which currency/tax policy is authoritative?
5. Should discrepancies, organization creation, and subscription operations be public, authenticated, or privileged?
6. Should the React app use client-side routes, or is the single-page login/quick-start the intended scope?
7. Are ZIMRA client/queue modules currently enabled in a real sale lifecycle? What is the required fiscal failure/offline policy?
8. Which migration/bootstrap procedure is authoritative for fresh and existing deployments?
9. What is the current supported test command/toolchain, and which historic failures remain reproducible?
10. Are the current untracked checkout components and modified build/database files intentional in-progress work?

## Confidence and Handoff

| Finding | Confidence |
|---|---|
| This workspace is an inventory/POS repository, not a portfolio. | High |
| FastAPI/SQLAlchemy backend and Vite/React frontend entry points and layering. | High |
| The main frontend exposes only login/quick-start; most workflow components are unwired. | High |
| Random/mock frontend data and API contract mismatches exist in source. | High |
| Historic test counts accurately represent the current tree. | Low |
| Runtime behavior, production deployment health, Core Web Vitals, and browser support. | Unverified |

**Handoff:** What is inherited is a broad inventory/POS backend, a small React login/setup UI, a collection of mostly disconnected workflow prototypes, Docker/Nginx deployment files, and extensive but inconsistent documentation. Its recorded product philosophy is operational clarity with progressive disclosure and offline tolerance; that philosophy is only partially realized in the current UI. New application work should preserve the neutral/blue-indigo semantic palette, Tailwind layout conventions, and explicit status/error states while closing accessibility gaps. There is no portfolio project representation or portfolio project-add procedure. Before extending the POS, first reconcile API contracts, authorization, money units, migrations, and test tooling. The repository is ready for carefully scoped engineering work only after those constraints are acknowledged; it is not ready for a portfolio extension.

## 13 — Verified Engineering Addendum (2026-11-07)

The inspection above records the initial source baseline. Work after that read-only inspection has changed the working tree; the following is a verified delta, not a rewrite of historical findings.

### Changes made

- Protected organization-scoped catalog, location, sales, subscription, till and sync operations with authenticated tenant context and role checks in the affected routes. Sale cashier and inventory actor attribution are taken from the authenticated user. Replaced ownerless public organization creation with fresh-install bootstrap in the follow-up addendum below.
- Made online sale ledger writes and stock projection updates part of the same transaction. Pending sale commits now lock and validate sale state. Sync rejects malformed batches and unsupported actions and scopes status/cache access to the authenticated organization.
- Added organization-scoped configurable tax rules, product tax assignment, and immutable sale-line tax snapshots. A product without an assigned tax rule intentionally receives no tax, per the clarified business decision. Tax is calculated and rounded per line using half-up to two decimals.
- Aligned checkout with major currency units, configurable tax, cash-only tendering, server-authoritative product prices, and explicit tender/change amounts. Card and mobile-money paths are not offered as successful payments. Till opening/closing balances now use major units.
- Connected the inventory overview to actual products, locations and ledger-derived stock; random stock/status/date values were removed from that screen. No low-stock threshold model exists, so no low-stock level is fabricated.
- Production startup no longer calls `create_all`; the API container runs Alembic migrations before starting. Production configuration rejects wildcard CORS and weak/default JWT secrets. The frontend Docker build no longer masks build/copy failures.

### Verification

- Full backend test suite: **262 passed, 13 skipped, 0 failed** using a disposable SQLite database at `/tmp/tenga-completion-final2-20261107.db`.
- `npm run type-check`: passed.
- `npm run build`: passed before the final startup/CORS-only edits; those later edits do not affect frontend source. The build writes to the user-modified `dist/` directory; see the preservation note below.
- Alembic `upgrade head → downgrade add_barcode_v001 → upgrade head`: passed against a disposable SQLite database. Production/PostgreSQL migration execution was not exercised.
- A focused concurrency test now uses a file-backed temporary SQLite database rather than sharing the repository's in-memory `StaticPool` connection between threads.

### Remaining production blockers

- The application entry screen is still the login/setup dashboard; product, inventory, and checkout components are not assembled into a complete navigable commercial workflow. Other prototypes, including product detail/history and stock adjustment, still contain hard-coded example data.
- Licensing remains unimplemented pending the separate central-platform SRS planned after POS completion. The newly added local bootstrap provisions an organization and first admin only; it does not activate or validate a license.
- Checkout does not yet require or attach an open till session. Cash tender/change are persisted on the sale, but there is no separate payment ledger, refund/void service, or completed return workflow.
- Offline queues exist in the Python client, but React checkout explicitly blocks completion when disconnected; cross-client retry/conflict recovery is not a verified end-to-end feature.
- Fiscal client/formatter/queue modules are not connected to sale finalization. No fiscal submission or regulatory compliance claim is supported.
- Currency code/identity, fiscal rules, multi-currency behavior, authentication token revocation/refresh, rate limiting, backup/restore, PostgreSQL runtime behavior, accessibility, browser runtime, and production deployment remain unverified.

### Preservation note

The repository was already dirty before implementation. The backend tests used temporary databases and did not intentionally operate on `tenga-test.db`. However, `npm run build` was run and rewrote `dist/`, which already contained user changes; the prior untracked assets referenced before the build are not recoverable from Git. The resulting build output is left in place rather than attempting a destructive restore. Treat all `dist/` changes as user-owned and review/recover them from an independent backup if needed.

## 14 — Local Installation Bootstrap (2026-11-07)

- Added `POST /api/v1/organizations/bootstrap`, gated by an operator-configured `INITIAL_SETUP_SECRET` of at least 32 characters. It creates one organization and its first local admin atomically; the admin password is bcrypt-hashed, and the submitted secret is never returned, logged by the application, or stored in the database.
- SQLite setup attempts were concurrency-tested. PostgreSQL uses a transaction-scoped exclusive table lock; an isolated PostgreSQL 16 test confirmed two separate application processes yield exactly one success and one replay rejection. A populated database is rejected without modifying its existing records.
- Disabled anonymous `POST /api/v1/organizations` with `410 Gone`; direct ownerless organization creation is no longer supported.
- Added `docs/INSTALLATION_BOOTSTRAP.md` with secret generation, operator-call, success verification, and failure/recovery instructions. Docker Compose passes the optional secret through; the example environment leaves it blank.
- A focused security audit identified that the original Compose API port was published on all interfaces and the public HTTP frontend proxied bootstrap requests. The source configuration now binds the API's published port to loopback and Nginx blocks the bootstrap path, including subpaths. These deployment changes have not been applied to the already-running containers; redeploy before using bootstrap.
- Existing databases are deliberately not migrated, merged, reassigned, or discarded by this feature. This bootstrap is only for a fresh database.
- Central registration, licensing, installation identity, offline validity, revocation, and recovery remain deferred until the future central-platform SRS. No license generation or validation is implemented locally.
- Verification after the security audit corrections: **271 passed, 13 skipped, 0 failed** on an isolated SQLite database; **50 focused authentication, authorization, bootstrap, and concurrency tests passed**; Compose configuration and `git diff --check` passed. On a disposable PostgreSQL 16 container, two separate application processes racing initialization produced one `201` and one `409`, a new process replay produced `409`, and persisted counts were exactly one organization and one owner. The populated shared PostgreSQL database was not modified.
