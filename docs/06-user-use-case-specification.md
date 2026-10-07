# Tenga Inventory — User & Use-Case Specification

## Purpose

This document details the major workflows users perform in Tenga Inventory. Each use case traces from a business requirement, identifies the actor and their goal, specifies the main flow and alternatives, and links to acceptance criteria.

---

## UC-001 — Create Product

**Use Case ID:** UC-001

**Name:** Create and Register a New Product

**Primary Actor:** Owner/Admin or Manager

**Goal:** Register a new product in the system so it can be tracked and receive stock.

**Trigger:** Business decides to add a new item to inventory (e.g., new SKU received from supplier, new tool purchased).

**Preconditions:**
- User is logged in with Owner/Admin or Manager role.
- System is online and database is accessible.

**Main Flow:**
1. User navigates to Products > New Product.
2. Form is displayed with fields: Name, SKU, Unit, Category, Barcode (optional), Cost (optional), Minimum Level (optional).
3. User fills in required fields (Name, SKU, Unit, Category).
4. User optionally enters cost and minimum level.
5. User submits form.
6. System validates SKU uniqueness within organization; if duplicate, shows error.
7. System creates product and confirms: "Product 'Laptop' (SKU: LT-001) created."
8. Use case ends.

**Alternative Flows:**

**Alt A: Product with Opening Balance**
- After creating product (step 7), user is offered option: "Add opening stock?"
- If yes: Receive Stock form is pre-populated with product; user enters quantity, location, cost, and confirms.
- Opening receipt is recorded as type OpeningBalance.

**Alt B: Duplicate SKU**
- System detects SKU exists (step 6).
- Shows error: "SKU LT-001 already exists for product 'Laptop (2023 Model)'."
- User can: revise SKU or cancel.

**Exceptions:**
- Network fails during form submission: form data is retained; user is prompted to retry.
- User lacks permission: system shows "Access denied."

**Result:**
- Product exists in system.
- Product can receive stock via UC-002.
- Product appears in search and inventory reports.

**Related Requirements:** REQ-001, REQ-004, REQ-025

**Acceptance Criteria:**
- [ ] Required fields (Name, SKU, Unit, Category) are enforced.
- [ ] SKU uniqueness is validated per organization.
- [ ] Optional fields can be omitted.
- [ ] Product persists and is immediately usable.
- [ ] User can optionally add opening stock in same flow.

---

## UC-002 — Receive Stock

**Use Case ID:** UC-002

**Name:** Record Stock Receipt

**Primary Actor:** Staff, Manager, or Owner/Admin

**Goal:** Record new stock entering a location so inventory is accurate.

**Trigger:** Physical stock arrives (delivery from supplier, donation, transfer from another location, or opening balance entry).

**Preconditions:**
- Product exists (created in UC-001).
- Location exists (created in UC-004).
- User is logged in with receive permission.

**Main Flow:**
1. User navigates to Stock > Receive.
2. Form is displayed: Product, Location, Quantity, Cost (optional), Reason (optional), Reference (optional), Date (pre-filled, editable).
3. User selects or searches for product.
4. User selects or searches for location.
5. User enters quantity (positive number).
6. User optionally enters cost per unit (if system is tracking costs for this product) or leaves blank.
7. User optionally enters reason (e.g., "Supplier delivery", "Donation") and reference (e.g., "Invoice #INV-2024-001").
8. User confirms date and submits.
9. System validates: quantity > 0, product and location exist.
10. System creates StockMovement: type=Receipt, product, location, quantity, cost (if provided), reason, user, timestamp.
11. System updates stock balance: Location + Product balance increases by quantity.
12. System updates weighted average cost if cost was provided.
13. User sees confirmation: "Received 50 units of 'Coca-Cola 500ml' at 'Shop Floor'. New balance: 150 units."
14. Use case ends.

**Alternative Flows:**

**Alt A: Bulk Receipt via Import**
- User selects "Import CSV".
- CSV template is downloaded or provided.
- User fills CSV with multiple products: Product SKU, Quantity, Location, Cost, Reference.
- System validates all rows and shows summary.
- On confirm, all receipts are created as movements with type=Receipt, reference tagged with import batch ID.

**Alt B: Receipt with Unknown Cost**
- User leaves cost field empty (step 6).
- System accepts and records receipt without cost.
- Valuation for this item shows quantity only (no value), and note "Cost not recorded".

**Exceptions:**
- Product or location not found: system shows autocomplete suggestions.
- Quantity is zero or negative: system shows error "Quantity must be positive."
- Cost is invalid (non-numeric): system shows error and clears field.

**Result:**
- Stock balance increases.
- Movement appears in history.
- Weighted average cost is updated (if cost provided).

**Related Requirements:** REQ-005, REQ-024

**Acceptance Criteria:**
- [ ] Receipt is recorded without cost; cost is not mandatory.
- [ ] Receipt is recorded with cost; average cost updates correctly.
- [ ] Stock balance reflects receipt.
- [ ] Movement appears in product history and audit trail.
- [ ] CSV import works for bulk opening balance entry.

---

## UC-003 — Issue Stock

**Use Case ID:** UC-003

**Name:** Record Stock Leaving a Location

**Primary Actor:** Staff, Manager, or Owner/Admin

**Goal:** Record stock leaving a location (usage, disposal, loss, or other reason).

**Trigger:** Stock is used, damaged, lost, or removed from location.

**Preconditions:**
- Product exists and has stock at the location.
- User is logged in with issue/remove permission.

**Main Flow:**
1. User navigates to Stock > Issue.
2. Form is displayed: Product, Location, Quantity, Reason (required), Reference (optional), Date (pre-filled, editable).
3. User selects or searches for product.
4. User selects or searches for location.
5. System shows current balance at location (e.g., "Current balance: 150 units").
6. User enters quantity (positive number, ≤ current balance).
7. User enters reason from dropdown or free text (e.g., "Damage", "Loss", "Expired", "Usage").
8. User optionally enters reference (e.g., incident number).
9. User submits.
10. System validates: quantity > 0, quantity ≤ current balance, product and location exist.
11. System creates StockMovement: type=Issue, product, location, quantity (negative), reason, user, timestamp.
12. System updates balance: location + product balance decreases by quantity.
13. User sees confirmation: "Issued 10 units of 'Coca-Cola 500ml' from 'Shop Floor'. Reason: Damage. New balance: 140 units."
14. Use case ends.

**Alternative Flows:**

**Alt A: Over-Issue with Override**
- User enters quantity exceeding balance (step 6).
- System warns: "Quantity (160) exceeds balance (150). Continue?"
- User can proceed (with reason enforced) or cancel.
- If proceed: creates issue and balance goes negative (flag in UI as "Negative balance: requires review").

**Alt B: Bulk Issues via Count Reconciliation**
- Issues are created as part of UC-010 (Reconcile Count).
- Not a primary flow but a consequence of counting.

**Exceptions:**
- Product or location not found: system shows autocomplete suggestions.
- Quantity exceeds balance and user does not confirm: transaction cancelled.
- Network fails: form data retained; user prompted to retry.

**Result:**
- Stock balance decreases (or becomes negative if override).
- Movement recorded in history with reason.
- Audit trail includes who issued stock.

**Related Requirements:** REQ-006, REQ-008

**Acceptance Criteria:**
- [ ] Issue is recorded with required reason.
- [ ] Stock balance decreases.
- [ ] System warns if quantity exceeds available balance.
- [ ] Override allowed with confirmation; balance can go negative.

---

## UC-004 — Transfer Stock Between Locations

**Use Case ID:** UC-004

**Name:** Move Stock from One Location to Another

**Primary Actor:** Manager or Owner/Admin

**Goal:** Transfer stock from one location to another (e.g., replenishment, relocation, inter-department transfer).

**Trigger:** Stock needs to move (e.g., storeroom to shop floor, one department to another).

**Preconditions:**
- Product has stock at source location.
- Source and destination locations exist and are different.
- User is logged in with transfer permission.

**Main Flow:**
1. User navigates to Stock > Transfer.
2. Form is displayed: Product, Source Location, Destination Location, Quantity, Reason (optional), Date (pre-filled, editable).
3. User selects or searches for product.
4. User selects or searches for source location.
5. System shows current balance at source (e.g., "Current: 80 units").
6. User selects destination location (must be different from source).
7. User enters quantity (positive, ≤ source balance).
8. User optionally enters reason (e.g., "Replenishment", "Stock relocation").
9. User submits.
10. System validates: source ≠ destination, quantity > 0, quantity ≤ source balance.
11. System creates single StockMovement: type=Transfer, product, source_location, destination_location, quantity, reason, user, timestamp.
12. System updates both balances: source decreases by quantity, destination increases by quantity, in one transactional operation.
13. User sees confirmation: "Transferred 20 units of 'Laptop' from 'Storeroom' to 'Finance Department'. New balances: Storeroom 60, Finance 26."
14. Use case ends.

**Alternative Flows:**

**Alt A: Transfer with Approval (Future)**
- Transfers between departments may require manager approval in future.
- MVP: no approval workflow; transfers are immediate.

**Exceptions:**
- Source and destination are the same: system shows error "Source and destination must be different."
- Quantity exceeds source balance: system shows error (similar to UC-003).
- Source location has zero balance: system shows error "Insufficient stock."

**Result:**
- Stock moves atomically from source to destination.
- Single movement recorded (not two separate movements).
- Both locations' balances updated consistently.

**Related Requirements:** REQ-007

**Acceptance Criteria:**
- [ ] Transfer is atomic (both balances update together).
- [ ] Movement history shows transfer as one event with both locations.
- [ ] Source and destination balances are correct post-transfer.

---

## UC-005 — Adjust Stock Quantity

**Use Case ID:** UC-005

**Name:** Correct Stock Quantity

**Primary Actor:** Manager or Owner/Admin

**Goal:** Adjust stock quantity to correct discrepancies or account for known changes.

**Trigger:** Physical count reveals discrepancy, damage discovered, or stock loss occurs.

**Preconditions:**
- Product and location exist.
- User is logged in with adjustment permission.

**Main Flow:**
1. User navigates to Stock > Adjust.
2. Form is displayed: Product, Location, Quantity Change (required, can be +/- ), Reason (required), Reference (optional), Date (pre-filled, editable).
3. User selects or searches for product.
4. User selects or searches for location.
5. System shows current balance (e.g., "Current: 100 units").
6. User enters quantity change (e.g., +5 or -3; can be positive or negative).
7. User selects or enters reason from required list (e.g., "Count correction", "Damage found", "Inventory loss").
8. User optionally enters reference (e.g., "Count ID #C-001").
9. User submits.
10. System validates: reason is provided, quantity change is non-zero, product and location exist.
11. System creates StockMovement: type=Adjustment, product, location, quantity (as specified, +/-), reason, user, timestamp.
12. System updates balance: location + product balance changes by the specified amount.
13. User sees confirmation: "Adjusted 'Laptop' at 'Finance Department' by +5 units. Reason: 'Count correction'. New balance: 26."
14. Use case ends.

**Alternative Flows:**

**Alt A: Negative Adjustment**
- User enters negative quantity to reduce stock (e.g., -7).
- System accepts and balance decreases.

**Alt B: Count Correction via UC-010**
- Adjustments are also created automatically when reconciling counts (UC-010).
- User may manually adjust instead of counting.

**Exceptions:**
- Reason is not selected: system shows error "Reason is required for adjustment."
- Quantity change is zero: system shows error "Quantity change cannot be zero."

**Result:**
- Stock balance changes by specified amount.
- Reason is recorded immutably.
- Audit trail includes user and reason.

**Related Requirements:** REQ-008, REQ-010

**Acceptance Criteria:**
- [ ] Adjustment is recorded with required reason.
- [ ] Stock balance changes correctly.
- [ ] Reason is visible in movement history.

---

## UC-006 — Start a Stock Count

**Use Case ID:** UC-006

**Name:** Begin a Physical Inventory Count

**Primary Actor:** Staff or Manager

**Goal:** Initiate a stock count session to verify physical quantities match system records.

**Trigger:** Scheduled inventory count (e.g., weekly, monthly) or ad-hoc check triggered by manager.

**Preconditions:**
- User is logged in with count permission.
- Locations and products exist.

**Main Flow:**
1. User navigates to Stock > Count > Start Count.
2. Form is displayed: Scope (required, location or product or full inventory), Date (pre-filled, editable).
3. User selects scope (e.g., "Finance Department" location or "All products").
4. System generates list of products expected at the selected scope with current system quantities.
5. User starts count session.
6. Count interface displays: Product, Expected Quantity (from system), Observed Quantity (user input), Difference (calculated, system – observed).
7. For each product/location, user records observed quantity or leaves blank if not present.
8. User can save count as pending (to complete later) or submit for review.
9. System creates Count record: count_date, scope, status=Pending, line items (product, location, expected, observed).
10. User sees confirmation: "Count started for Finance Department. 23 products recorded. 18 match system, 5 have differences. Status: Pending review."
11. Use case ends.

**Alternative Flows:**

**Alt A: Count All Locations**
- User selects "Full inventory" as scope.
- System generates list of all products and expected quantities at all locations.
- User proceeds to record observations.

**Alt B: Offline Count (Future)**
- Count data could be recorded offline and synced later (deferred to post-MVP).

**Exceptions:**
- Network fails during count: pending count is saved; user can resume from last saved point.

**Result:**
- Pending count record is created.
- Count can be reviewed in UC-007 and reconciled in UC-008.

**Related Requirements:** REQ-009

**Acceptance Criteria:**
- [ ] Count session captures all products in scope.
- [ ] Expected quantities are pre-populated correctly.
- [ ] Count can be saved as pending or submitted.
- [ ] Differences are calculated and displayed.

---

## UC-007 — Review Pending Count

**Use Case ID:** UC-007

**Name:** Review a Stock Count Before Reconciliation

**Primary Actor:** Manager or Owner/Admin

**Goal:** Review a pending count to verify accuracy before creating movements.

**Trigger:** User completes a count (UC-006) and submits for review; manager wants to verify before reconciliation.

**Preconditions:**
- Pending count exists (created in UC-006).
- User is logged in with manager or admin role.

**Main Flow:**
1. User navigates to Stock > Count > Pending Counts.
2. System displays list of pending counts: Date, Scope, Items Counted, Differences.
3. User selects a pending count to review.
4. Review view displays: Count date, scope, all line items (product, location, expected, observed, difference, % diff).
5. Line items are sorted by difference (largest first).
6. User can: approve all, reject and discard count, or request modifications.
7. If approve: count status changes to "Ready for Reconciliation"; use case proceeds to UC-008.
8. If reject: count is marked "Rejected" and discarded.
9. If modify: user can edit observed quantities inline (for minor typos/corrections).
10. Use case ends.

**Alternative Flows:**

**Alt A: Reject and Redo**
- If differences seem implausible, manager rejects count.
- Count is discarded; staff can start a new count.

**Exceptions:**
- Network fails during review: review state is retained; user can resume.

**Result:**
- Count is approved and ready for reconciliation, or rejected.

**Related Requirements:** REQ-010

**Acceptance Criteria:**
- [ ] Pending counts are displayed clearly.
- [ ] Differences are highlighted.
- [ ] Count can be approved or rejected.

---

## UC-008 — Reconcile Stock Count

**Use Case ID:** UC-008

**Name:** Apply Count Differences as Adjustment Movements

**Primary Actor:** Manager or Owner/Admin

**Goal:** Reconcile count differences by creating adjustment movements to update balances to physical counts.

**Trigger:** Approved count (from UC-007) is ready to reconcile.

**Preconditions:**
- Approved count exists.
- User is logged in with manager or admin role.

**Main Flow:**
1. User navigates to Stock > Count > Reconcile.
2. System displays approved counts ready for reconciliation.
3. User selects a count to reconcile.
4. Reconciliation view displays all line items: Product, Location, Expected, Observed, Difference.
5. For each line with non-zero difference:
   - System suggests an adjustment (±difference).
   - User can approve suggestion, modify it, or skip.
6. User submits reconciliation.
7. For each approved difference, system creates StockMovement: type=CountCorrection, product, location, quantity=difference (to move expected to observed), reason="Physical count", reference="Count ID #C-001".
8. System updates all balances to match observed quantities.
9. System marks count status as "Reconciled".
10. User sees confirmation: "Reconciliation complete. 3 adjustments created. Stock updated to match physical count."
11. Use case ends.

**Alternative Flows:**

**Alt A: Partial Reconciliation**
- User can reconcile only some differences (e.g., manager wants to investigate one discrepancy further before adjusting).
- Count status remains "Pending reconciliation" for non-reconciled items; full reconciliation happens later.

**Exceptions:**
- Discrepancy is very large (e.g., 50% difference): system flags and requires confirmation.

**Result:**
- Balances match physical count.
- CountCorrection movements are recorded with audit trail.
- Count is closed.

**Related Requirements:** REQ-010

**Acceptance Criteria:**
- [ ] CountCorrection movements are created for each difference.
- [ ] Stock balances reflect physical count.
- [ ] Count status is updated to Reconciled.

---

## UC-009 — View Product History and Valuation

**Use Case ID:** UC-009

**Name:** Inspect a Product's Stock, Movements, and Value

**Primary Actor:** All roles

**Goal:** Understand a product's current stock, movement history, and valuation (cost basis).

**Trigger:** User searches for a product (UC-002.1) or navigates to inventory detail view.

**Preconditions:**
- Product exists.
- User is logged in.

**Main Flow:**
1. User navigates to Products or searches for a product.
2. System displays product list with summary: Name, SKU, Category, Current Total Quantity, Current Value.
3. User selects a product.
4. Product Detail view displays:
   - **Header:** Product name, SKU, unit, category, minimum level.
   - **Current Stock:** Summary table showing quantity per location.
   - **Valuation:** Current average cost, total value, note on valuation method (weighted average).
   - **Cost Drill-Down:** Link to see cost history (receipts, calculated average).
   - **Movement History:** Timeline of all movements (last 50), with filters by type, location, date.
5. User can click on individual movements to see full details.
6. User can click "Cost History" to see:
   - Receipt-by-receipt cost history with dates and quantities.
   - Weighted average calculation shown step-by-step.
7. Use case ends.

**Alternative Flows:**

**Alt A: Filter Movement History**
- User applies filters: movement type, location, date range.
- History updates to show matching movements.

**Exceptions:**
- Product has no cost recorded: valuation section shows "Quantity tracked; cost not recorded."

**Result:**
- User understands product's current state and history.

**Related Requirements:** REQ-003, REQ-012, REQ-028

**Acceptance Criteria:**
- [ ] Product detail shows current stock per location.
- [ ] Valuation is displayed with methodology note.
- [ ] Movement history is complete and searchable.
- [ ] Cost history drill-down shows calculation.

---

## UC-010 — Generate Reports

**Use Case ID:** UC-010

**Name:** View Inventory Reports

**Primary Actor:** Manager, Owner/Admin

**Goal:** Generate and review summary reports for inventory status, analysis, and decision-making.

**Trigger:** Manager wants to understand inventory status, low-stock items, or movement activity.

**Preconditions:**
- User is logged in with manager or admin role.
- Inventory data exists.

**Main Flow:**
1. User navigates to Reports.
2. Report menu offers options: Low Stock, Stock by Location, Recent Movements, Inventory Value, Audit Trail.
3. User selects "Low Stock".
4. System displays list of products below minimum level: Product, Current Quantity per Location, Minimum, Status (Low/Critical).
5. Report is sortable by status or location.
6. User can export as CSV or view only in UI.
7. Use case ends (or user selects another report).

**Alternative Flows:**

**Alt B: Stock by Location Report**
- User selects "Stock by Location".
- System displays table: Location, Products at Location, Total Qty, Total Value.
- User can filter by location or category.

**Alt C: Recent Movements Report**
- User selects "Recent Movements".
- System displays last 50 movements: Type, Product, Location(s), Qty, Reason, User, Timestamp.
- User can filter by product, location, type, or date.

**Alt D: Inventory Value Report**
- User selects "Inventory Value".
- System displays: Total Inventory Value, Value by Product (top 20), Value by Location, Valuation Method (Weighted Average).

**Exceptions:**
- No data matches filter: report shows "No items to display."

**Result:**
- Report is generated and displayed.
- User can export or take action (e.g., replenish low-stock items).

**Related Requirements:** REQ-020, REQ-021, REQ-022, REQ-023

**Acceptance Criteria:**
- [ ] Reports are accurate and complete.
- [ ] Reports can be filtered and sorted.
- [ ] Export to CSV works.

---

## UC-011 — Manage Users and Permissions

**Use Case ID:** UC-011

**Name:** Create Users and Assign Roles

**Primary Actor:** Owner/Admin

**Goal:** Set up team members with appropriate roles so they can perform their inventory tasks.

**Trigger:** New employee joins or permissions need to change.

**Preconditions:**
- User is logged in with Owner/Admin role.

**Main Flow:**
1. Admin navigates to Settings > Users.
2. User Management view shows list of existing users with roles: Name, Email, Role, Status (Active/Inactive), Last Login.
3. Admin clicks "Add User".
4. Form is displayed: Email, Full Name, Role (dropdown: Owner/Admin, Manager, Staff), Initial Password (generated or user-provided).
5. Admin fills in fields and assigns a role.
6. Admin sends invitation link (via email) or provides credentials.
7. New user receives invitation and sets password.
8. User is activated in system.
9. User can log in and perform actions according to their role.
10. Admin can later change a user's role or deactivate them.
11. Use case ends.

**Alternative Flows:**

**Alt A: Change User Role**
- Admin selects existing user and clicks "Edit".
- Role can be changed.
- User receives notification of role change (future feature).

**Exceptions:**
- Email address already exists: system shows error "User with this email already exists."

**Result:**
- New user is created and can log in.
- User has appropriate permissions based on role.

**Related Requirements:** REQ-013, REQ-014, REQ-015, REQ-016

**Acceptance Criteria:**
- [ ] User can be created with a role.
- [ ] Role-based permissions are enforced.
- [ ] User receives invitation and can log in.

---

## Summary: Use Case Dependencies

```
UC-001 Create Product
  ↓
UC-002 Receive Stock (or UC-005 Adjust to set opening balance)
  ↓
UC-009 View Product History (and see balance/movements/valuation)
  ├→ UC-003 Issue Stock (when stock needs to leave)
  ├→ UC-004 Transfer Stock (when stock moves between locations)
  ├→ UC-005 Adjust Stock (when discrepancies occur)
  ├→ UC-006 Start Count (when verification needed)
  │  ├→ UC-007 Review Count
  │  └→ UC-008 Reconcile Count (creates adjustments)
  └→ UC-010 Generate Reports (for analysis)

UC-011 Manage Users (enables all other use cases by permissions)
```

---

## Next Steps

1. Identify business rules for each operation (UC → rules).
2. Define domain entities from use cases.
3. Map UX progression and complexity levels.
