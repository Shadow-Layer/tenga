# Tenga Inventory — Pilot Scoping Questionnaire

Purpose: gather the missing facts needed before implementing the MVP for each pilot site. Focus areas map to unknowns U001, U003, U004, U006, U007, U008, U010.
Instructions for pilot: Please answer each question as accurately as you can. Where choices are given, select the best option and provide examples where requested. Provide sample CSV exports if available.

Contact person: _____________________  Role: _____________________  Email/Phone: _____________________

---

SECTION A — Connectivity & Offline (U001)
1. Primary network connectivity at your primary inventory location(s):
   - [ ] Reliable broadband (stable, <1s typical latency)
   - [ ] Intermittent / cellular (works but occasional dropouts)
   - [ ] Frequent outages (>1 hour/week)
   - [ ] No network (offline) — will require local/offline tools
   Notes / examples (locations and connectivity per site):

2. Do any locations rely on cellular tethering or satellite where network is unreliable? If yes, list locations and estimated outage frequency.

3. If the web app is unavailable, is manual/phone-based recording acceptable short-term, or do you require offline device operation and sync?
   - Manual acceptable
   - Need offline-capable app and sync
   - Unsure — need discussion


SECTION B — Scale & Throughput (U003)
4. How many distinct SKUs (products) do you currently track or expect to track at pilot start?
   - [ ] < 200
   - [ ] 200–1,000
   - [ ] 1,000–5,000
   - [ ] 5,000–20,000
   - [ ] >20,000 (specify)
   Please provide an approximate SKU count and any seasonal spikes.

5. Typical daily movement volume per site (receive/issue/transfer/adjust combined):
   - [ ] < 10/day
   - [ ] 10–50/day
   - [ ] 50–200/day
   - [ ] 200–1,000/day
   - [ ] >1,000/day (specify)
   Notes on peak hours or batch operations:

6. Any heavy bulk imports or batch operations expected on day 1 (e.g., importing all opening balances)? If yes, estimate row counts.


SECTION C — Data Import & Onboarding (U004, U010)
7. Do you have existing inventory data exported from spreadsheets or other systems? If yes:
   - File format(s): [ ] CSV [ ] Excel [ ] Other (specify)
   - Typical file columns available (tick any): SKU, Name, Location, Quantity, Unit, Cost, Barcode, Category, Reference
   Please attach a sample (anonymized 10–50 rows) if possible.

8. How many rows would a full opening-balance import contain (approx)?
   - [ ] < 200
   - [ ] 200–1,000
   - [ ] 1,000–5,000
   - [ ] >5,000 (specify)

9. Desired go-live timeline for pilot (choose one):
   - [ ] Immediately (within 2 weeks)
   - [ ] Short (2–6 weeks)
   - [ ] Medium (6–12 weeks)
   - [ ] Long (>12 weeks)
   Notes on readiness and resources for data entry:


SECTION D — Regulatory / Audit Requirements (U006)
10. Are there any legal or institutional retention/format requirements for inventory records or audits in your organization or jurisdiction? (e.g., retain movement history for X years, CSV formats for auditors)
    - [ ] Yes — please describe (retention periods, export formats, periodic report needs)
    - [ ] No / Not aware

11. Are internal auditors likely to request exports or signed reports? If yes, how frequently (monthly, quarterly, annually)?


SECTION E — Arrupe (Institutional) — Accountability Workflows (U007)
12. Describe how custody/assignment currently works for equipment in your organization (Arrupe example):
    - Is equipment checked out to individuals or assigned to departments?
    - Are custodians assigned (person responsible for a set of items)?
    - Is there a formal check-out/check-in process for issuing items to staff/students?

13. Do you need the system to record custodian or assignee for each movement? (Yes/No)
    If yes, explain what "custodian" means operationally and whether it is required for every movement.

14. Do transfers between departments require approval (e.g., manager sign-off) today? If yes, describe the approval process.


SECTION F — Grocery Shops — Counting Practices (U008)
15. How often do you perform inventory counts?
    - [ ] Daily spot checks
    - [ ] Weekly partial counts
    - [ ] Monthly full counts
    - [ ] Quarterly full counts
    - [ ] Ad-hoc only
    Notes on who performs counts (owner, staff) and time taken per count.

16. Do you perform full counts or partial (e.g., category or shelf-by-shelf) counts more commonly?
    - [ ] Full counts
    - [ ] Partial counts (spot checks)
    - [ ] Both equally

17. Do you require offline/counting mobile support (e.g., scan in warehouse and sync later)?
    - [ ] Yes — must have
    - [ ] Nice to have later
    - [ ] Not needed


SECTION G — Operational Details & Edge Cases
18. What operations do you perform that Tenga must handle from day one (besides receive/issue/transfer/count)? List special cases (e.g., consignment returns, donations, school inventory loans).

19. Have you experienced frequent partial receipts (delivered less than ordered) or backorders that you need to track? (Yes/No) If yes, describe.

20. Typical unit types used (tick all that apply): [ ] units/pieces [ ] boxes/cartons [ ] weight (kg) [ ] volume (liters) [ ] meters [ ] other — specify.


SECTION H — Contacts & Next Steps (U010 follow-up)
21. Preferred format to receive the pilot system and support:
    - [ ] Hosted SaaS with pilot admin access
    - [ ] Self-hosted on our infrastructure (we provide servers)
    - [ ] Unsure — need recommendation

22. Who will be the primary contact to coordinate data import and training? Name / role / contact details.

23. Please attach a small sample dataset (10–50 rows) if available: sample file path / link / note.


---

## Internal interpretation guidance (for Tenga team)
- If any site marks offline requirement = "Need offline-capable app" → escalate: offline becomes a must-validate and may block immediate SaaS-only pilot.
- If SKU count > 5,000 or daily movements > 200/day → mark scale risk and schedule performance benchmark with representative dataset before deploy.
- If opening-balance rows > 1,000 → recommend CSV import be prioritized for that pilot; ask for sample and map columns.
- If auditors require specific export formats/retention → route to compliance and implement export requirements before pilot launch.
- If custodial workflows require per-person assignment and approvals → note as potential Phase-2 feature; check whether transfers can be used to model this initially.

---

Thank you. Please return completed questionnaire and sample files to: project-tenga@placeholder.local or reply to the coordinating contact above.

