# Phase D: Product Owner Decision Brief

**Status:** ✅ APPROVED (October 10, 2026)  
**Prepared By:** Copilot / Tenga Inventory Team  
**Executive Summary:** Two critical decisions (D010a & D014) are now approved and documented. Slice B (POS Checkout) can proceed. TengaVFD integration with ZIMRA compliance verification should run in parallel.

---

## Decision Summary

### D010a — Offline Inventory Mutation and Reconciliation Policy

**What:** Tenga will support durable offline recording for all core inventory operations (sales, receipts, transfers, counts, adjustments, returns) with operation-specific reconciliation rules.

**Why:** Small shops in Zimbabwe operate multiple checkouts that frequently go offline. The current backend implementation (U006) allows overselling and reconciles afterward via physical count. This decision formalizes that policy across all inventory operations.

**How It Works:**
1. Cashiers and managers can record inventory movements while offline (will be stored locally)
2. When devices reconnect, all pending movements sync to the server
3. Server applies movements and detects any discrepancies (e.g., stock went negative)
4. Manager performs physical count to reconcile discrepancies
5. System marks reconciliation complete

**User Impact:**
- Cashiers see "Sale recorded locally" (not "Sale confirmed")
- After sync: "Sale synchronized" (confirmed by server)
- If stock imbalance detected: Manager prompted for physical count

**No Implementation Work Required Now:** Architecture is already in place (U006). Documentation provides guidance for Slice B UI design.

**Implementation Timeline:** Part of Slice B checkout UI (2-3 weeks)

**Risk Level:** 🟢 Low (foundation already tested; well-understood)

---

### D014 — Fiscal Integration and ZIMRA Compliance Policy

**What:** Tenga will support ZIMRA-compliant fiscalization for all sales in Zimbabwe deployments using either online real-time submission or approved offline procedures.

**Why:** Fiscalization is a mandatory regulatory requirement in Zimbabwe for all taxpayers (including small shops below VAT threshold). A compliant POS system must integrate with ZIMRA's Fiscal Device Management System (FDMS).

**Authoritative Basis:**
- ZIMRA official guidance confirms fiscalization is mandatory
- ZIMRA Fiscal Device Gateway API supports both online and offline modes
- Virtual fiscal devices and direct POS-to-FDMS integration are approved approaches

**How It Works:**
1. **Online (normal operation):** Sale recorded → Fiscal submission to ZIMRA in real-time → Fiscal number assigned → Receipt printed with fiscal number
2. **Offline (if approved for deployment):** Sale recorded → Fiscal request queued locally → Receipt printed with "Fiscal # pending" → On reconnection, batch submitted to ZIMRA → Receipts updated
3. **Error recovery:** If ZIMRA unavailable, sales complete (fiscal retries automatically); manager monitors queue
4. **Duplicate prevention:** Idempotent submission (retrying returns same fiscal number, no double-reporting)

**Key Architectural Principle:**
- Sale completion and fiscal status are separate concerns
- Sale is ALWAYS recorded immediately (inventory-complete)
- Fiscal confirmation happens async (may be delayed or may be pending)
- Both are accurate; neither is "false"

**User Impact:**
- Online: Transparent; takes ~500ms
- Offline: Receipt shows "Fiscal # pending"; no customer action needed; fiscal updates after reconnection
- Failed fiscal: Manager notified; can retry manually or wait for automatic retry

**Implementation Work Required:**
1. **Phase D (current):** ✅ Architecture approved (no code changes yet)
2. **Phase D Parallel:** TengaVFD integration + ZIMRA verification (separate system; not blocking Slice B)
3. **Slice B:** Integrate fiscalization interface into checkout (estimate: 2-3 weeks after TengaVFD ready)

**Outstanding Questions (To Be Verified):**
- Specific ZIMRA device approval process
- Offline approval status for target deployments
- Offline numbering scheme
- Maximum allowed offline delay
- Annual reconciliation procedures
- Audit trail requirements

**Implementation Timeline:** TengaVFD integration (4-6 weeks), Slice B integration (2-3 weeks), Total ~6-9 weeks

**Risk Level:** 🟡 Medium (regulatory compliance required; depends on TengaVFD; outstanding verification questions)

**Mitigation:** Conduct ZIMRA verification in parallel with TengaVFD development to reduce schedule risk

---

## Approval Checklist

### D010a — Offline Inventory Mutation Policy

- [✅] **Approved** — Support durable offline recording for all 6 core operations
- [✅] **Approved** — Allow negative stock short-term; reconcile via physical count
- [✅] **Approved** — Backend ledger authoritative; device balance provisional
- [✅] **Approved** — Operation-specific reconciliation rules (not "reject all conflicts")

**Status:** ✅ READY FOR IMPLEMENTATION

---

### D014 — Fiscal Integration Policy

- [✅] **Approved** — Fiscalization mandatory for Zimbabwe deployments
- [✅] **Approved** — TengaVFD handles fiscal independently; separate from TengaPOS
- [✅] **Approved** — Use approved ZIMRA offline procedure if deployment approved
- [✅] **Approved** — Sales complete immediately; fiscal confirmation async
- [✅] **Approved** — If ZIMRA unavailable, sales proceed (fiscal retries); manager notified

**Status:** ✅ ARCHITECTURE APPROVED; PARALLEL ZIMRA VERIFICATION RECOMMENDED

---

## Next Steps

### Immediate (This Week)

1. **Phase D Complete**
   - ✅ Investigation documents finalized (PHASE_D_OFFLINE_STOCK_POLICY.md, PHASE_D_FISCAL_INTEGRATION.md)
   - ✅ Decision register updated (D010a + D014)
   - ✅ Approval recorded (October 10, 2026)

2. **Slice B Unblocked**
   - Checkout implementation can now proceed
   - Design should incorporate UI states from D010a (Recorded, Syncing, Synced, Reconciliation Required)
   - Receipt layout should accommodate fiscal number placement (from D014)

### Week 2-3 (Parallel Tracks)

**Track A: Slice B Implementation (Tenga Inventory Team)**
- Implement checkout screen (2-3 weeks)
- Integrate D010a UI states (Recorded, Syncing, Synced, Reconciliation Required)
- Integrate D014 receipt interface (placeholder for fiscal number)
- Assume fiscalization interface provided by TengaVFD

**Track B: TengaVFD + ZIMRA Verification (Separate Team or External)**
- Implement ZIMRA Fiscal Device Gateway integration (4-6 weeks)
- Verify outstanding compliance questions with ZIMRA (ongoing)
- Provide fiscalization interface to TengaPOS (defined contract)

### Handoff (Week 4-6)

- TengaVFD integration ready
- ZIMRA verification complete or documented as ongoing
- Slice B can integrate fiscalization (2-3 additional weeks)
- Full checkout workflow ready for testing

---

## Risk Summary

| Decision | Risk Level | Mitigation |
|----------|-----------|-----------|
| **D010a** | 🟢 Low | Infrastructure already in place; well-tested |
| **D014** | 🟡 Medium | Conduct ZIMRA verification in parallel; document assumptions |

**Overall Phase D:** ✅ READY TO PROCEED (both decisions approved; no blockers)

---

## Document References

- **Full Policy Details:** 
  - `PHASE_D_OFFLINE_STOCK_POLICY.md` (270 lines)
  - `PHASE_D_FISCAL_INTEGRATION.md` (240 lines)

- **Decision Register:** 
  - `docs/final-decision-ledger.md` (D010a + D014 entries)

- **Implementation Artifacts:** 
  - Test scenarios in policy documents (5 for D010a, 7 for D014)
  - Architecture diagrams (D014 system boundaries)
  - API changes and data model additions specified

- **Related Decisions:**
  - D001 (Inventory-first)
  - U006 (Permit & Reconcile Afterward)
  - U007 (Tiered Grace Periods)
  - U008 (Offline Optimism)

---

## Sign-Off

**Decisions Approved By:** Product Owner  
**Approval Date:** October 10, 2026  
**Status:** ✅ APPROVED & DOCUMENTED  
**Next Phase:** Slice B (POS Checkout) Implementation  
**Blocker Status:** 🟢 CLEAR — All blockers resolved; ready to proceed

---

**Prepared:** October 10, 2026  
**Document Version:** 1.0  
**Status:** Final
