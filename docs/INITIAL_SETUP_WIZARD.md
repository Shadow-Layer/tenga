# Tenga Initial Setup Wizard — Operator Manual

This manual explains the eight-step, administrator-only setup flow shown on the Tenga dashboard. It covers the order of work, each action's effect, supported CSV formats, validation, and how to recover from common errors.

> **Verified documentation discrepancies (2026-11-11):** The current wizard
> includes editable organization settings; it does not only display the
> organization as described in the original Step 1 text below. Its single-
> product form includes unit of measure and low-stock threshold, but its CSV
> flow calls a separate setup-import endpoint. That endpoint's product CSV
> contract differs from the newer catalog-import endpoint; details are called
> out in Step 5. Other workflow intent is not inferred here.

## Before you begin

1. Sign in with an active administrator account for this installation.
2. Confirm that the organization and first administrator were created by the protected first-install bootstrap. This wizard does not create, rename, or edit the organization.
3. Decide which locations, tills, staff accounts, products, and opening counts are needed.
4. Prepare CSV files from a trusted source. Use UTF-8, a comma delimiter, one header row, and no more than 5 MB or 5,000 data rows per file.
5. If importing historical sales, prepare item-level tax and discount information. The importer will not guess missing values.
6. Confirm that the application schema is current before using imports. Production schema changes are applied with the approved Alembic release procedure, not by opening the dashboard.

Setup progress (current step and explicit deferrals) is saved in this browser for this organization. Created locations, users, tills, products, inventory movements, and sales are saved by the server as each action succeeds. Clearing browser storage can reset the progress indicator, but does not delete server records.

## The eight steps

### 1. Review organization settings

The wizard loads the existing organization and signed-in administrator. Its
current form can update the business name, phone, email, address, region,
timezone, and currency; it does not create a second organization. The API
prevents currency changes after inventory or sales activity, except for an
explicitly confirmed currency assignment when a legacy organization has no
currency set. Historical records are not converted. Confirm the target
organization before saving.

### 2. Add locations

Add a location for each store or stock site. A location has a name, an organization-unique code, and an optional description. Tills are assigned to locations; opening inventory rows use the location code.

If a code is already in use, the API rejects the request. Refresh the dashboard and choose a different code. The wizard never retries a failed create request automatically.

### 3. Add users

Create separate accounts for staff. Enter a full name, unique username, email, password, and role:

- **Cashier / operator**: basic point-of-sale operations.
- **Manager**: store operations such as locations, tills and products.

Only an administrator can create another administrator, and this setup form does not create admin accounts. Give staff their temporary password through an appropriate private channel; it is not shown again or stored in setup progress. Ask each person to use the established account/password change process after sign-in.

This step can be deferred. Do not share the administrator's credentials as a substitute.

### 4. Configure tills

Create a till name and unique code and assign it to a location. Creating a till does not open a till session. A session is opened only when an operator starts trading or when the guided first-sale step needs one.

If no location exists, return to step 2. A till code conflict means the code is already used; choose another and retry after checking the current till list.

### 5. Load the product catalog

Either add one product or import `products.csv`. The wizard's manual product
form requires SKU, name, selling price, unit of measure, and a non-negative
low-stock threshold. Its CSV route requires SKU, name, and selling price and
supports the optional columns listed below. The newer catalog-import API at
`/api/v1/products/imports/products/...` instead requires
`unit_of_measure` and `minimum_stock_level`; the current wizard calls
`/api/v1/setup/imports/products/...`, whose parser does not map those fields.
Do not assume the wizard's CSV import sets the unit or threshold until these
contracts are aligned. Both paths are additive; they do not update or replace
products.

#### Product CSV

Required headers for the setup wizard's current CSV route:

```csv
sku,name,price
```

Optional headers:

```csv
cost,barcode,category,description,tax_rule_id
```

Example:

```csv
sku,name,price,cost,barcode,category,description,tax_rule_id
TEA-001,Breakfast tea,4.50,2.10,6001234567890,Beverages,Black tea,1
COF-002,Ground coffee,8.75,4.20,,Beverages,Medium roast,
```

The separate catalog-import API requires `unit_of_measure` and
`minimum_stock_level`; the wizard endpoint currently does not map those fields.
Prices and costs use the same major currency units used by existing product
prices (for example `4.50`, not `450` cents). A supplied tax-rule ID must
refer to an active rule in this organization. Leave optional cells blank when
not applicable.

### 6. Load opening inventory

Import counted quantities by SKU and location code. This records an append-only inventory adjustment that reconciles the current stock ledger to the entered count. It does not erase existing movements. For each row, the adjustment is:

`counted quantity − current ledger quantity`

A zero difference records no stock change. The same exact file is idempotent and will not be applied twice. If a count is corrected, review the new preview carefully: a changed file is a new import and reconciles the ledger to its new target quantities.

#### Opening inventory CSV

Required headers:

```csv
sku,location_code,quantity
```

Example:

```csv
sku,location_code,quantity
TEA-001,MAIN,36
COF-002,MAIN,18
```

Quantity must be a whole number greater than or equal to zero. Each SKU/location pair must appear once. Product SKUs and location codes must already exist and be active. Unknown references, duplicate pairs, invalid quantities, or malformed rows block the whole import.

### 7. Optionally import historical sales

This step is optional. Historical records are imported for reporting only. They are marked `HISTORICAL_IMPORT`, retain the source receipt reference and timestamp, and **do not create inventory movements or alter current stock**.

Before previewing, select a default Tenga till and cashier association. These associations are required because Tenga sales records link to a till and cashier. They are import/reporting associations, not a claim about which till or person handled the original source transaction.

#### Historical sales CSV

Use one row per sold item. Repeat the receipt ID and receipt timestamp on each line in the same sale. Required headers:

```csv
receipt_id,sold_at,sku,quantity,unit_price,discount_per_item,tax_rate,tax_inclusive,payment_method
```

Example:

```csv
receipt_id,sold_at,sku,quantity,unit_price,discount_per_item,tax_rate,tax_inclusive,payment_method
OLD-100,2025-01-02T10:00:00+02:00,TEA-001,2,4.50,0.00,15.00,false,CASH
OLD-100,2025-01-02T10:00:00+02:00,COF-002,1,8.75,0.50,15.00,false,CASH
```

Rules:

- `receipt_id` is the stable source receipt/order identifier. It must not already exist as an imported reference.
- `sold_at` must be ISO 8601 and include a timezone. The importer converts it to UTC for storage.
- `sku` must match an active product. Quantity is a positive whole number.
- `unit_price` and `discount_per_item` are per item in the same major currency units used for product prices. Discount cannot exceed unit price.
- `tax_rate` is the historical percentage for that line, from `0` through `100`. `tax_inclusive` must be `true` or `false`. Enter `0,false` for a line with no tax. The importer does not use today's product tax rule to guess historical tax.
- Every line in one receipt must have the same timestamp and payment method.
- The stored sale amount is calculated from line prices, discounts and tax flags. The historical import associates the sale with the selected till/cashier, records the sale as completed, and does not create a till-session cash reconciliation or fiscal receipt.

The importer accepts any non-empty payment method up to 50 characters as source history. This does not enable that payment method for live checkout. An imported receipt already present in the organization is rejected, even if the file content changed.

### 8. Record a first operation

Choose either or both:

#### Guided first sale

Choose an existing till and product, enter quantity, cash tendered, and opening till cash. The wizard checks the till session; it opens the session only if none is open, then records a live cash sale through the normal sales API.

This is a real transaction. It creates a completed sale and stock-out movement. The application uses the product's current selling price and tax configuration. Confirm the product, quantity, till, and tendered cash before submitting. If cash tendered is below the calculated total, the sale is rejected and no sale is created.

#### Inventory count adjustment

Choose a location and product, enter the physical count, and confirm the change. The wizard reads current ledger quantity and submits the difference as an inventory adjustment. This is a real, auditable stock movement, not a preview.

You may finish setup without creating a sale or changing inventory. Return to this step later when the business is ready.

## Import workflow and safety

1. Choose a CSV and check the selected filename.
2. Click **Validate and preview**. The browser sends the file text to the authenticated API; the preview performs validation only and writes no imported records.
3. Correct every reported error in the original file, select the corrected file, and validate it again. A preview with any errors cannot be committed.
4. Review the till/cashier associations for historical sales and the destination location codes for opening stock.
5. Click **Import** only after reviewing the preview. Each import commits as one database transaction. A failure rolls back the batch rather than leaving a partial import.
6. The server stores an organization-scoped import batch with the file-content hash. Repeating the exact file/type returns the previous result without duplicating records. Corrected or changed files are treated as new imports; opening counts will reconcile to the new quantities.

The supported limits are 5 MB and 5,000 rows. The API reports at most 200 validation errors at a time; it indicates when more errors were found. Fix errors in the file and preview again instead of attempting partial imports.

## Troubleshooting

| Message or symptom | What to do |
|---|---|
| Missing CSV columns | Use the exact required header names above. Header matching ignores case and surrounding spaces. |
| Unknown SKU or location code | Complete product/location setup first, or correct the CSV reference. |
| Duplicate SKU, SKU/location, or receipt | Resolve duplicates in the source file or inspect existing records. Do not change identifiers merely to force a commit. |
| A file was already imported | The exact content and import type were committed before. Verify the records before deciding whether a genuinely new import is needed. |
| Import conflicts with existing data | No rows were committed. Refresh records, correct the source, preview again, and do not keep retrying an unchanged conflicting file. |
| User/till/location is unavailable | Refresh the dashboard and confirm the record remains active and belongs to this organization. |
| First sale fails at till open | Check subscription/session eligibility and the returned API message. Do not repeatedly submit a sale. |
| Setup progress resets | Server-side records remain. Reopen the wizard; it reloads organization resources. Explicit browser deferrals/current step may need to be recorded again. |

## Administrator and deployment notes

- Setup routes require an active authenticated administrator. The organization identity is derived from the signed-in user; clients cannot choose another organization.
- The public Nginx route must continue to reject anonymous organization bootstrap and direct organization management. Authenticated organization-detail and user-management paths are required by the wizard and must remain protected by API authorization.
- This feature adds an Alembic revision for import-batch auditing and imported-sale identity. Apply it only through the approved backup, review, and migration process before deploying code that calls setup-import endpoints. Do not run `Base.metadata.create_all()` against an existing production database as a substitute.
- Historical sale rows are distinguishable from live sales. Their fiscal status is `imported`; they are not submitted for fiscalization by the import path.
- Customer and supplier returns are not supported in this release. Do not model a sale return as an ordinary receipt or adjustment.
- The wizard does not implement central licensing, owner recovery, organization editing, XLSX imports, bulk product updates, or stock movements from historical sales.
- Keep a database backup before schema upgrades or bulk imports. Never use database reset, volume deletion, or destructive SQL as an import recovery method.
