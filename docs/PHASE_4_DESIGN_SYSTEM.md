# Tenga Inventory — Design System (Phase 4)

**Status**: Foundation + Component Specs  
**Last Updated**: October 9, 2026  
**Scope**: Inventory + Checkout + Offline + Admin workflows  
**Tech Stack**: React 19, TypeScript, Tailwind CSS, Zustand

---

## Part 1: Design Philosophy

### Guiding Principles

1. **Progressive Complexity**: New users see only essential actions. Advanced features appear when needed.
2. **Operational Clarity**: Every metric, status, and action must answer a business question or enable work.
3. **Offline-First Acknowledgment**: UI reflects the actual capability: offline is normal, sync is eventual.
4. **Inventory Independence**: Inventory is useful without POS. Checkout is additive, not required.
5. **Simple Presentation, Rigorous Behavior**: Clean UI must not conceal system state or hide failures.
6. **Consistency**: Layout, navigation, language, and interaction patterns are predictable across screens.

---

## Part 2: Design Tokens

### Color System

**Semantic Colors** (Primary use, not decorative):

```
Neutral (Default):
  - text-primary:      #1F2937  (Tailwind gray-800)
  - text-secondary:    #6B7280  (Tailwind gray-500)
  - text-disabled:     #D1D5DB  (Tailwind gray-300)
  - bg-primary:        #FFFFFF  (White)
  - bg-secondary:      #F3F4F6  (Tailwind gray-100)
  - bg-tertiary:       #E5E7EB  (Tailwind gray-200)
  - border:            #D1D5DB  (Tailwind gray-300)

Success (Positive, confirmed actions):
  - bg:                #DCF8D8  (Light green)
  - text:              #16A34A  (Tailwind green-600)
  - border:            #86EFAC  (Tailwind green-300)

Warning (Caution, review required):
  - bg:                #FEF3C7  (Light amber)
  - text:              #D97706  (Tailwind amber-600)
  - border:            #FCD34D  (Tailwind amber-300)

Error (Problem, action required):
  - bg:                #FEE2E2  (Light red)
  - text:              #DC2626  (Tailwind red-600)
  - border:            #FECACA  (Tailwind red-300)

Info (Informational, no action):
  - bg:                #DBEAFE  (Light blue)
  - text:              #2563EB  (Tailwind blue-600)
  - border:            #93C5FD  (Tailwind blue-300)

Offline (Offline/pending sync):
  - bg:                #F5F3FF  (Light purple)
  - text:              #7C3AED  (Tailwind violet-600)
  - border:            #DDD6FE  (Tailwind violet-300)
```

**Primary Action Colors**:
- Button (Primary): #2563EB (blue, Tailwind)
- Button (Secondary): #6B7280 (gray, Tailwind)
- Button (Destructive): #DC2626 (red, Tailwind)

### Typography

**Font Family**: System stack (no web fonts for performance)
- `font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;`

**Scale**:
```
XS:  12px / 1.5 / 500
SM:  14px / 1.5 / 400
MD:  16px / 1.5 / 400  (body default)
LG:  18px / 1.5 / 500
XL:  20px / 1.6 / 600
2XL: 24px / 1.6 / 700
3XL: 32px / 1.6 / 700
```

**Usage**:
- **3XL**: Page title / main heading
- **2XL**: Section heading
- **XL**: Subsection heading / modal title
- **LG**: Form label / table header
- **MD**: Body text, product names, quantities
- **SM**: Secondary text, timestamps, hints
- **XS**: Badge text, small labels

### Spacing Scale

All values based on `4px` base unit:

```
0:   0px
1:   4px
2:   8px
3:   12px
4:   16px
5:   20px
6:   24px
7:   28px
8:   32px
10:  40px
12:  48px
14:  56px
16:  64px
```

**Usage**:
- **2-3**: Padding within components (button, input)
- **4-6**: Padding in cards/containers
- **4**: Margin between elements
- **6-8**: Margin between sections
- **10-12**: Margin between major sections or between header/body

### Border & Shadows

```
Border Radius:
  - Small:    4px   (inputs, buttons, badges)
  - Medium:   8px   (cards, modals)
  - Large:    12px  (featured containers)

Borders:
  - Subtle:   1px solid #D1D5DB  (default container)
  - Strong:   2px solid #6B7280  (focus, important)

Shadows:
  - SM:  0 1px 2px 0 rgba(0,0,0,0.05)
  - MD:  0 4px 6px -1px rgba(0,0,0,0.1)
  - LG:  0 10px 15px -3px rgba(0,0,0,0.1)
```

---

## Part 3: Component Library

### Core Components

#### 1. Button

**Variants**: Primary, Secondary, Destructive, Ghost

**States**: Default, Hover, Active, Disabled, Loading

```tsx
// Primary button (call-to-action)
<Button variant="primary">
  Save
</Button>

// Secondary button (alternative action)
<Button variant="secondary">
  Cancel
</Button>

// Destructive button (delete, void, etc.)
<Button variant="destructive">
  Delete
</Button>

// Ghost button (low priority)
<Button variant="ghost">
  Learn More
</Button>
```

**Behavior**:
- Min width: 44px (touch target)
- Min height: 40px (touch target)
- Hover: 5% darker shade
- Active: 10% darker shade
- Disabled: 50% opacity, cursor not-allowed
- Loading: Show spinner, disable click

**Accessibility**:
- Clear focus ring (2px, blue #2563EB)
- Keyboard: Space/Enter triggers
- Touch: Min 44x40px

---

#### 2. Text Input

**Variants**: Standard, Search, Number, Currency

**States**: Default, Focus, Filled, Error, Disabled, Loading

```tsx
// Standard input
<Input
  label="Product Name"
  placeholder="e.g., Coffee Beans"
  error={errors.name}
/>

// Search input (within list/table)
<Input
  type="search"
  placeholder="Search products..."
  onSearch={handleSearch}
/>

// Currency input
<Input
  type="currency"
  label="Unit Price"
  value={price}
  currency="USD"
/>
```

**Behavior**:
- Height: 40px
- Padding: 12px horizontal, 8px vertical
- Border: 1px solid #D1D5DB
- Focus: Border #2563EB, 2px
- Error: Border #DC2626, show error message below
- Disabled: Background #F3F4F6, cursor not-allowed

**Accessibility**:
- Associated label or aria-label
- Clear error messages
- Focus visible (ring)

---

#### 3. Table / Product List

**Variants**: Compact (mobile), Normal (desktop), Expanded (detail)

**States**: Loading, Empty, Normal, Error, Sortable, Filterable

```tsx
// Product list table
<Table>
  <Header>
    <Column label="Product" sortable />
    <Column label="SKU" />
    <Column label="Stock" numeric />
    <Column label="Actions" />
  </Header>
  <Row>
    <Cell>Coffee Beans</Cell>
    <Cell>SKU-001</Cell>
    <Cell numeric>15</Cell>
    <Cell>
      <Button size="sm">Edit</Button>
      <Button size="sm" variant="ghost">Details</Button>
    </Cell>
  </Row>
</Table>
```

**Responsive Behavior**:
- **Desktop (≥1024px)**: Full table, all columns
- **Tablet (768-1023px)**: Hide SKU column, show actions as dropdown
- **Mobile (<768px)**: Stack as cards, show only name + stock + actions

**Empty State**:
- Show icon + message: "No products yet"
- Show primary action: "Add Product"

---

#### 4. Form (Product Creation / Editing)

**Sections**:
1. Basic Info (Name, SKU, Description)
2. Pricing (Unit Price, Cost Price, optional)
3. Stock (optional, can be set later)
4. Advanced (optional, hidden by default)

```tsx
<Form onSubmit={handleSave}>
  <FormSection title="Basic Information">
    <Input label="Product Name" name="name" required />
    <Input label="SKU" name="sku" />
    <Input label="Description" name="description" type="textarea" />
  </FormSection>

  <FormSection title="Pricing">
    <Input label="Unit Price" name="unit_price" type="currency" required />
    <Input label="Cost Price" name="cost_price" type="currency" hint="For inventory valuation" />
  </FormSection>

  <Collapsible label="Advanced Options">
    <Input label="Barcode" name="barcode" />
    <Input label="Reorder Level" name="reorder_level" type="number" />
  </Collapsible>

  <ButtonGroup>
    <Button variant="primary" type="submit">Save</Button>
    <Button variant="secondary" type="button" onClick={handleCancel}>Cancel</Button>
  </ButtonGroup>
</Form>
```

**Behavior**:
- Required fields marked with `*`
- Validation on blur, not submit
- Show validation error inline
- Primary action (Save) becomes enabled only when form is valid
- Cancel returns to previous screen without saving

---

#### 5. Status Indicator

**Types**: Online, Offline, Syncing, Synced, Error, Pending, Limited

```tsx
// Offline indicator
<StatusIndicator status="offline" label="Offline" />

// Syncing indicator
<StatusIndicator status="syncing" label="Syncing... (3 items)" />

// Synced (temporary, disappears after 5s)
<StatusIndicator status="synced" label="Synced" autoHide={5000} />

// Error (persistent, requires action)
<StatusIndicator status="error" label="Sync failed. Tap to retry." onRetry={handleRetry} />

// Subscription limited
<StatusIndicator status="limited" label="Subscription expired. Renew to record new sales." />
```

**Visual**:
- 8px indicator dot (color-coded)
- Label text (semantic color)
- Optional action (button or link)

---

#### 6. Empty State

**Components**: Icon, Heading, Description, Primary Action

```tsx
<EmptyState
  icon={<ShoppingCartIcon />}
  title="No Products Yet"
  description="Add your first product to get started with inventory management."
  action={<Button variant="primary">Add Product</Button>}
/>
```

**Scenarios**:
- No products
- No sales
- No stock movements
- Search returns empty
- No offline pending sync
- Subscription limited (no new actions available)

---

#### 7. Modal / Dialog

**Variants**: Confirmation, Form, Alert, Status

```tsx
// Confirmation modal
<Modal title="Delete Product?" onClose={handleClose}>
  <p>This action cannot be undone. All stock history will be preserved.</p>
  <ButtonGroup>
    <Button variant="destructive" onClick={handleDelete}>Delete</Button>
    <Button variant="secondary" onClick={handleClose}>Cancel</Button>
  </ButtonGroup>
</Modal>

// Status modal (e.g., after checkout)
<Modal title="Sale Complete">
  <StatusBox status="success" message="Sale recorded." />
  <p>Receipt ID: RCP-2026-001</p>
  <ButtonGroup>
    <Button variant="primary" onClick={handlePrint}>Print Receipt</Button>
    <Button variant="secondary" onClick={handleClose}>New Sale</Button>
  </ButtonGroup>
</Modal>
```

**Behavior**:
- Backdrop: Overlay 50% dark
- Modal centered, max-width 500px
- Click outside closes (if not blocking)
- Escape key closes
- Focus trap (keyboard nav within modal only)

---

#### 8. Toast Notification

**Types**: Success, Error, Warning, Info

**Auto-dismiss**: 5-10 seconds (except error)

```tsx
// Success (transient)
<Toast type="success" message="Product saved." autoHide={5000} />

// Error (persistent, requires dismiss)
<Toast type="error" message="Failed to sync sale. Tap to retry." action={<Button>Retry</Button>} />

// Info (no action)
<Toast type="info" message="Offline mode: Changes will sync when connected." autoHide={10000} />
```

---

### Compound Components

#### 9. Product Row (List Item)

**Desktop View**:
```
[Product Name] [SKU-001] [Stock: 15] [Price: 50.00] [▼ Menu]
```

**Mobile/Tablet View** (Card):
```
┌─────────────────────────────┐
│ Product Name                │
│ SKU: SKU-001 | Stock: 15    │
│ Price: 50.00 USD            │
│ [Edit] [Details] [Menu ▼]   │
└─────────────────────────────┘
```

**Interactive**:
- Tap name/card → Show product detail
- Tap "Details" → Show stock history
- Menu → Edit, Adjust, Reconcile, Delete

---

#### 10. Cart Item (Checkout)

**View**:
```
[Product Name]
SKU: SKU-001
Qty: [1] [+] [-]    Unit Price: 50.00    Total: 50.00 USD
```

**Interactive**:
- `[+]` → Increase quantity
- `[-]` → Decrease quantity (or remove if qty becomes 0)
- Tap quantity field → Edit directly
- Tap product name → Show product detail in overlay

---

#### 11. Offline/Sync Indicator Panel

**Offline State**:
```
⚠️ Offline
Working offline. Changes will sync when connected.
[Sync Now] (optional if connection available)
```

**Syncing State**:
```
↻ Syncing (4 items)
Please wait...
```

**Synced State** (temporary, 3 sec):
```
✓ Synced
All changes saved.
```

**Error State**:
```
✗ Sync Failed
Error: [Specific reason]
[Retry] [View Details]
```

**Conflict State**:
```
⚠️ Stock Conflict Detected
Item "Coffee Beans": Sold 3 offline, but stock was oversold.
[Review Conflict] [Reconcile]
```

---

## Part 4: Screen States

### Universal States

Every screen should handle:

| State | Appearance | Action |
|-------|------------|--------|
| **Loading** | Skeleton / spinner | Wait for data |
| **Loaded (Normal)** | Full content | User actions available |
| **Empty** | Empty state graphic + message | Primary action (create, search, etc.) |
| **Error** | Error message + retry button | Retry or dismiss |
| **Offline** | Content visible (stale data possible) + Offline indicator | Work offline, sync later |
| **No Permission** | Empty state + message | Request access or contact admin |

---

## Part 5: Responsive Breakpoints

**Supported Devices**:
- **Mobile** (≤480px): Phones, small tablets
- **Tablet** (481-1024px): iPad, Android tablets
- **Desktop** (≥1025px): Laptops, large monitors

**Key Rules**:

1. **Mobile**: Stack content vertically, prioritize primary action
2. **Tablet**: 2-column layout possible, keep touch targets ≥44x40px
3. **Desktop**: 3-column layout, full table views possible

**Responsive Adjustments**:
- **Font sizes**: Reduce on mobile (MD → SM for body text)
- **Spacing**: Reduce margins on mobile (4-6 → 2-3)
- **Tables**: Convert to card stack on mobile
- **Modals**: Full-width on mobile, centered on desktop
- **Navigation**: Tab-based on desktop, hamburger on mobile

---

## Part 6: Accessibility Standards

### Color Contrast
- **Text on background**: 4.5:1 minimum (WCAG AA)
- **UI components**: 3:1 minimum

### Touch Targets
- **Minimum size**: 44px × 40px (mobile)
- **Minimum spacing**: 8px between targets

### Keyboard Navigation
- **Tab order**: Logical, left-to-right, top-to-bottom
- **Focus visible**: 2px ring, clear color (#2563EB)
- **Escape key**: Close overlays, dismiss dialogs
- **Enter key**: Submit forms, activate buttons

### Semantic HTML
- **Labels**: Every input has associated `<label>` or `aria-label`
- **Error messages**: Connected to input via `aria-describedby`
- **Lists**: Use `<ul>`, `<ol>`, `<li>` semantically
- **Tables**: Use `<thead>`, `<tbody>`, `<th>`, semantic headers

### Screen Reader Support
- **Headings**: Logical hierarchy (h1, h2, h3)
- **Landmarks**: `<nav>`, `<main>`, `<aside>`
- **ARIA**: Only where semantic HTML insufficient
- **Images**: Alt text or `role="presentation"` if decorative

### Mobile Considerations
- **Text size**: Min 16px (prevents auto-zoom on iOS)
- **Click targets**: Min 44x40px (standard)
- **Touch gestures**: Support tap, not swipe-only
- **Screen reader**: Test with VoiceOver (iOS) and TalkBack (Android)

---

## Part 7: Unresolved Design Decisions

### D010a: Offline Stock Policy (Affects Checkout UI)

**Question**: When offline, should checkout show stock warnings, allow oversale, or block sales?

**Design Implications**:

| Approach | Checkout UI | Consequences |
|----------|-------------|--------------|
| **Permit (Current)** | No warnings shown. "Sale recorded locally." | Simple, but oversale possible. Reconciliation required. |
| **Cache & Warn** | Show cached stock. If sale exceeds cache: "Stock may be low. Selling anyway." | Reduces obvious errors. Cache can be stale. |
| **Block** | Cannot checkout. "Sync required to sell." | No oversale. Blocks workflow. |

**Status**: ⚠️ **Unresolved** — Product decision required.

**Placeholder Design**: Will use "Permit" approach initially; mark as provisional.

### D014: Fiscal Integration (Affects Sale Completion UI)

**Question**: Is a sale "complete" after local recording, or does it require fiscal/tax certification?

**Design Implications**:

| Scenario | Current Design | With Fiscal |
|----------|-----------------|------------|
| Checkout success | "Sale recorded. Receipt printing..." | "Sale pending fiscal certification..." |
| Receipt fails | "Sale complete. Receipt failed." (recoverable) | "Sale incomplete. Fiscal cert. failed." (requires retry) |
| Offline sale syncs | "Sale now synced." | "Sale synced, pending fiscal cert. on reconnect." |

**Status**: ⚠️ **Unresolved** — Regulatory research required.

**Placeholder Design**: Will assume receipt printing is not transaction-critical; adjust if fiscal requirements surface.

---

## Part 8: Implementation Notes

### No New Dependencies

Design system uses **only** existing stack:
- React 19
- TypeScript 5.3
- Tailwind CSS 4.3
- zustand (state)
- axios (API)
- react-router-dom (navigation)

No UI component libraries (Material-UI, shadcn, etc.). All components built from primitives.

### File Structure

```
src/
  components/
    common/
      Button.tsx
      Input.tsx
      Table.tsx
      Modal.tsx
      Toast.tsx
      StatusIndicator.tsx
      EmptyState.tsx
    inventory/
      ProductList.tsx
      ProductForm.tsx
      ProductDetail.tsx
      StockMovementHistory.tsx
      StockCountForm.tsx
      ReconciliationView.tsx
    checkout/
      CheckoutView.tsx
      Cart.tsx
      PaymentForm.tsx
      SaleConfirmation.tsx
    admin/
      UserList.tsx
      LocationList.tsx
      TillList.tsx
      Reports.tsx
    status/
      OfflineIndicator.tsx
      SyncStatus.tsx
      StatusPanel.tsx
  styles/
    tokens.css           (Color, spacing, typography tokens)
    components.css       (Component base styles)
    utilities.css        (Helpers)
  hooks/
    useOnline.ts         (Network status)
    useSync.ts           (Sync state)
    useAuth.ts           (Auth, permissions)
  stores/
    inventoryStore.ts    (Products, stock)
    checkoutStore.ts     (Cart, sale)
    syncStore.ts         (Pending transactions)
```

### CSS Architecture

- **Tokens**: Custom CSS properties (--color-primary, --spacing-4, etc.)
- **Tailwind**: @apply directives for component styles
- **Utilities**: Global helpers (reset, container, etc.)
- **No BEM or complex selectors**: Keep CSS simple, let Tailwind handle composition

---

## Acceptance Criteria for Design System

✅ **Complete when**:

1. All tokens defined and documented
2. Core components specified (button, input, table, form, etc.)
3. Component states defined (default, hover, active, disabled, loading)
4. Responsive rules documented for all components
5. Accessibility requirements specified
6. Unresolved decisions marked and explained
7. No new dependencies introduced
8. Implementation notes ready for developers
9. Colors meet WCAG AA contrast requirements
10. Touch targets meet 44x40px minimum

---

**Status**: ✅ Specification Complete  
**Next Step**: Create HTML/CSS wireframes for Inventory slice
