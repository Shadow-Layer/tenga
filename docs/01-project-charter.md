# Tenga Inventory — Project Charter

## Purpose
Tenga Inventory exists to provide an inventory-first product that is operationally useful without requiring sales, POS, accounting, or ERP. It enables businesses and institutions to reliably know what they have, where it is, and what has happened to it, while revealing complexity only as users need it.

## Vision
A lightweight, trustworthy inventory system that supports the core inventory loop (Create item → place stock → move stock → count → reconcile → history) and grows with user needs while avoiding forced adoption of unrelated business systems.

## Target users (MVP pilots)
- university (institutional inventory: departments, equipment, accountability)
- Small grocery shops (commercial inventory: high SKU volume, frequent replenishment)

## Core principles
- Inventory-first: useful without sales or accounting (Decision D001).
- Progressive complexity: start minimal, reveal features when justified.
- Auditor-friendly: append-only movement history and explicit corrective movements.
- Practical costing: record movement costs; MVP valuation uses weighted average (D004).

## Scope (MVP)
Required: items/products (name, SKU, optional barcode, unit, category, cost optional, reorder level), locations (store/department/storeroom/shelf), stock quantities (current/available/minimum), stock movements (receive/issue/transfer/adjust + history), stock counts (start/record/compare/reconcile), basic users & accountability (Owner/Admin, Manager, Staff), basic search & reporting, basic valuation (weighted average), audit trail,POS.

Out of scope (MVP): customers, invoices, supplier management, purchasing workflows, accounting integration, complex dashboards, granular RBAC, AI features.

## Success criteria (first 6 months)
- Institutional pilot (Arrupe) successfully records and tracks at least 80% of department-issued items with clear accountability.
- 2–5 grocery pilots report daily operational value: accurate on-hand visibility and usable low-stock alerts.
- Core loop (create → place → move → count → reconcile → history) is usable without training by primary users in both pilots.

## Stakeholders
- Product owner: user / project sponsor
- Pilot partners:  selected grocery shop owners
- Development and design team

## Risks
- Insufficient fidelity for commercial SKU volumes — mitigate by performance validation during feasibility.
- Misunderstanding RBAC needs — mitigate by simple three-role model (D005).

## Timeline (suggested)
- 0–3 weeks: iterate on MVP UX, finalize PRD
- 3–10 weeks: build MVP and run pilot onboarding
- 10–20 weeks: pilot validation and iterate

---
(Decision references: D001, D002, D003, D004, D005)
