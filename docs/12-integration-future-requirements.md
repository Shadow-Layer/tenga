# Tenga Inventory — Integration & Future Requirements

## Purpose
Define clean boundaries for future integrations (TengaPOS, accounting, purchasing, analytics) and explicit assumptions to preserve through MVP design.

---

## Guiding Principle
Tenga Inventory is inventory-first and must remain operable without external integrations. Integrations are optional, decoupled, and must never be prerequisites for core workflows.

---

## Potential Integrations and Contracts

1. TengaPOS (future)
   - Data needed from Inventory: product identifiers (product_id / SKU), current available quantity per location, optional price metadata if shared.
   - Data provided to Inventory by POS: sales events as StockMovement of type Issue (or a POS-to-Inventory integrated gateway that creates Issue movements).
   - Ownership: Inventory remains the source of truth for stock quantity and movement history. POS records sales and sends an authoritative movement to Inventory to reduce stock.
   - Integration assumption: POS submits movements atomically; Inventory validates availability and records the movement.

2. Accounting Systems (external)
   - Data exchange: export of inventory valuation (snapshot), movement history (csv) for auditing and reconciliation.
   - Ownership: Accounting owns ledger/financial records; Inventory provides cost and quantity data for reconciliation.
   - Integration assumption: Exports are read-only and batched; no live double-write from accounting into Inventory.

3. Purchasing / Supplier Systems
   - Data exchange: purchase orders and supplier receipts can be imported; Inventory treats imported receipts as Receipt movements.
   - Ownership: Purchasing owns procurement process; Inventory owns stock records and receipt movements.
   - Integration assumption: Imports include references (PO numbers) mapped to movement.reference.

4. Analytics & BI
   - Data exchange: bulk exports or APIs exposing movements and balances for analysis.
   - Ownership: Analytics consumes data; Inventory remains data source.

5. Backup & Storage Providers
   - Data exchange: scheduled backups to storage (object store) or downloadable DB dumps.
   - Ownership: Inventory controls backup scheduling; storage is passive.

---

## Integration Design Constraints (Apply Now)
- Use stable identifiers (organization_id, product_id, SKU) as integration keys.
- Keep movement model simple and extensible: one StockMovement entity with a type field enables consistent mapping from external events.
- Preserve immutability: external integrations cannot edit historical movements; they can only create new movements.
- Design export APIs and CSV formats upfront (movement export, product snapshot) to avoid breaking changes later.
- Provide a clear event schema for POS integration:
  { event_id, product_sku, quantity, location_id, event_type: 'sale', timestamp, reference }

---

## Information Ownership Summary
- Product identity (name, SKU, barcode): Inventory owns authoritative record.
- Product metadata for retail pricing: could be shared by POS; Inventory may store optional selling price as non-authoritative metadata (but default is to treat selling price as external data).
- Current stock: Inventory is authoritative.
- Movement history: Inventory is authoritative (append-only).
- Cost per receipt: Inventory is authoritative.

---

## Backwards-compatibility & Future-proofing (What to preserve now)
- Movement schema: avoid breaking field names; design with optional extension fields.
- SKU immutability: do not change SKU semantics later; use new products instead of renaming.
- Transfer semantics: maintain atomic transfer event model to avoid future mismatches.

---

## Integration Safety Rules
- Integrations must perform idempotent writes (use event_id/dedup keys) to avoid duplicate movements.
- Inventory must validate incoming movements and reject malformed/unauthorized changes.
- Expose a sandbox or import preview UI for bulk imports.

---

## Integration Implementation Phasing
- Phase 1 (post-MVP): CSV export/import, read-only APIs for movement history.
- Phase 2: POS event ingestion with validation and idempotency handling.
- Phase 3: Real-time integrations (webhooks, streaming) with robust monitoring and conflict resolution.

---

## Summary: Integration Requirements
- Inventory remains the source of truth for stock and movements.
- Integrations are consumers or event producers that create movements; they cannot mutate history.
- Design for idempotency, stable identifiers, and migration-safe exports.

