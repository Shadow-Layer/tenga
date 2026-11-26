import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { apiClient, employeesAPI, type Employee, type Location, type Product, type Till, type User } from '../api'
import { getEmployeeTillAccess } from './employeeAssignmentLogic'
import './SetupWizard.css'

type Props = { user: User; onManageEmployeeAssignments: () => void }
type ImportKind = 'products' | 'opening-inventory' | 'historical-sales'
type ImportPreview = {
  valid: boolean
  row_count: number
  valid_count: number
  errors: string[]
  rows: Array<{ row: number; reference: string; status: string }>
}
type OrganizationSettings = {
  name: string
  phone: string
  email: string
  address: string
  region: string
  timezone: string
  currency_code: string
}

const STEPS = [
  'Organization',
  'Locations',
  'Users',
  'Tills',
  'Product catalog',
  'Opening inventory',
  'Sales history',
  'First operation',
]

const STORAGE_KEY = 'tenga-setup-wizard-v1'

function messageFromError(error: unknown): string {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail) return JSON.stringify(detail)
  }
  return error instanceof Error ? error.message : 'The request failed. Please try again.'
}

export default function SetupWizard({ user, onManageEmployeeAssignments }: Props) {
  const [step, setStep] = useState(0)
  const [completed, setCompleted] = useState<number[]>([])
  const [skipped, setSkipped] = useState<number[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [employees, setEmployees] = useState<Employee[]>([])
  const [tills, setTills] = useState<Till[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [organization, setOrganization] = useState<{
    id: number
    name: string
    code: string
    currency_code?: string | null
  } | null>(null)
  const [organizationSettings, setOrganizationSettings] = useState<OrganizationSettings>({
    name: '',
    phone: '',
    email: '',
    address: '',
    region: '',
    timezone: 'UTC',
    currency_code: 'USD',
  })
  const [confirmLegacyCurrency, setConfirmLegacyCurrency] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  const [locationName, setLocationName] = useState('')
  const [locationCode, setLocationCode] = useState('')
  const [locationDescription, setLocationDescription] = useState('')
  const [staffName, setStaffName] = useState('')
  const [staffUsername, setStaffUsername] = useState('')
  const [staffEmail, setStaffEmail] = useState('')
  const [staffPassword, setStaffPassword] = useState('')
  const [staffRole, setStaffRole] = useState<'manager' | 'operator'>('operator')
  const [tillName, setTillName] = useState('')
  const [tillCode, setTillCode] = useState('')
  const [tillLocationId, setTillLocationId] = useState<number | ''>('')
  const [productSku, setProductSku] = useState('')
  const [productName, setProductName] = useState('')
  const [productPrice, setProductPrice] = useState('')
  const [productCost, setProductCost] = useState('')
  const [productUnit, setProductUnit] = useState('each')
  const [productMinimumStock, setProductMinimumStock] = useState('0')

  const [importKind, setImportKind] = useState<ImportKind | null>(null)
  const [csvText, setCsvText] = useState('')
  const [csvName, setCsvName] = useState('')
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [importTillId, setImportTillId] = useState<number | ''>('')
  const [importCashierId, setImportCashierId] = useState<number | ''>(user.id)

  const [saleTillId, setSaleTillId] = useState<number | ''>('')
  const [saleProductId, setSaleProductId] = useState<number | ''>('')
  const [saleQuantity, setSaleQuantity] = useState(1)
  const [cashTendered, setCashTendered] = useState('')
  const [openingBalance, setOpeningBalance] = useState('0')
  const [confirmRealSale, setConfirmRealSale] = useState(false)

  const [stockLocationId, setStockLocationId] = useState<number | ''>('')
  const [stockProductId, setStockProductId] = useState<number | ''>('')
  const [stockQuantity, setStockQuantity] = useState('0')
  const [confirmStockChange, setConfirmStockChange] = useState(false)

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === Number(saleProductId)),
    [products, saleProductId],
  )

  async function loadSetupData() {
    setLoadError('')
    try {
      const [orgResponse, locationResponse, userResponse, tillResponse, productResponse, employeeResponse] = await Promise.all([
        apiClient.get(`/api/v1/organizations/${user.organization_id}`),
        apiClient.get<{ items: Location[] }>(`/api/v1/locations?organization_id=${user.organization_id}&limit=100`),
        apiClient.get<{ items: User[] }>(`/api/v1/organizations/${user.organization_id}/users`),
        apiClient.get<{ items: Till[] }>('/api/v1/tills/?limit=100'),
        apiClient.get<{ items: Product[] }>(`/api/v1/products?organization_id=${user.organization_id}&limit=100`),
        employeesAPI.list(user.organization_id),
      ])
      setOrganization(orgResponse.data)
      setOrganizationSettings({
        name: orgResponse.data.name ?? '',
        phone: orgResponse.data.phone ?? '',
        email: orgResponse.data.email ?? '',
        address: orgResponse.data.address ?? '',
        region: orgResponse.data.region ?? '',
        timezone: orgResponse.data.timezone ?? 'UTC',
        currency_code: orgResponse.data.currency_code ?? '',
      })
      setLocations(locationResponse.data.items)
      setUsers(userResponse.data.items)
      setTills(tillResponse.data.items)
      setProducts(productResponse.data.items)
      setEmployees(employeeResponse.data.items.filter((employee) => employee.is_active))
    } catch (error) {
      setLoadError(messageFromError(error))
    }
  }

  useEffect(() => {
    try {
      const saved = localStorage.getItem(`${STORAGE_KEY}:${user.organization_id}`)
      if (saved) {
        const state = JSON.parse(saved) as { step?: number; completed?: number[]; skipped?: number[] }
        setStep(Math.min(Math.max(state.step ?? 0, 0), STEPS.length - 1))
        setCompleted(state.completed ?? [])
        setSkipped(state.skipped ?? [])
      }
    } catch {
      setLoadError('Saved setup progress could not be read. You can continue; current records will remain unchanged.')
    }
    void loadSetupData()
  }, [user.organization_id])

  useEffect(() => {
    try {
      localStorage.setItem(
        `${STORAGE_KEY}:${user.organization_id}`,
        JSON.stringify({ step, completed, skipped }),
      )
    } catch {
      setNotice('Progress could not be saved in this browser. Records saved to the server remain safe.')
    }
  }, [step, completed, skipped, user.organization_id])

  function markComplete(index = step) {
    setCompleted((previous) => previous.includes(index) ? previous : [...previous, index])
    setSkipped((previous) => previous.filter((item) => item !== index))
    setNotice('Step saved.')
  }

  function skipStep(index = step) {
    setSkipped((previous) => previous.includes(index) ? previous : [...previous, index])
    setNotice('Step deferred. You can return to it later.')
  }

  function clearImport() {
    setCsvText('')
    setCsvName('')
    setPreview(null)
  }

  function chooseImport(kind: ImportKind) {
    setImportKind(kind)
    clearImport()
  }

  async function runAction(action: () => Promise<string | void>, successMessage: string) {
    setBusy(true)
    setNotice('')
    try {
      const result = await action()
      setNotice(result ?? successMessage)
      await loadSetupData()
    } catch (error) {
      setNotice(messageFromError(error))
    } finally {
      setBusy(false)
    }
  }

  async function createLocation(event: FormEvent) {
    event.preventDefault()
    await runAction(async () => {
      await apiClient.post('/api/v1/locations', {
        organization_id: user.organization_id,
        name: locationName,
        code: locationCode,
        description: locationDescription || undefined,
      })
      setLocationName('')
      setLocationCode('')
      setLocationDescription('')
      markComplete()
    }, 'Location created.')
  }

  async function updateOrganization(event: FormEvent) {
    event.preventDefault()
    if (!organization) return
    await runAction(async () => {
      await apiClient.patch(`/api/v1/organizations/${organization.id}`, {
        ...organizationSettings,
        confirm_legacy_currency: confirmLegacyCurrency,
      })
      markComplete()
    }, 'Organization settings saved.')
  }

  async function createStaff(event: FormEvent) {
    event.preventDefault()
    await runAction(async () => {
      await apiClient.post(`/api/v1/organizations/${user.organization_id}/users`, {
        full_name: staffName,
        username: staffUsername,
        email: staffEmail,
        password: staffPassword,
        role: staffRole,
      })
      setStaffName('')
      setStaffUsername('')
      setStaffEmail('')
      setStaffPassword('')
      markComplete()
    }, 'User created. The password is not stored in setup progress.')
  }

  async function createTill(event: FormEvent) {
    event.preventDefault()
    if (!tillLocationId) {
      setNotice('Choose a location for this till.')
      return
    }
    await runAction(async () => {
      await apiClient.post('/api/v1/tills/', {
        location_id: Number(tillLocationId),
        code: tillCode,
        name: tillName,
      })
      setTillName('')
      setTillCode('')
      markComplete()
    }, 'Till created. It has not been opened.')
  }

  async function createProduct(event: FormEvent) {
    event.preventDefault()
    await runAction(async () => {
      await apiClient.post('/api/v1/products', {
        organization_id: user.organization_id,
        sku: productSku,
        name: productName,
        price: Number(productPrice),
        cost: productCost ? Number(productCost) : undefined,
        unit_of_measure: productUnit.trim(),
        minimum_stock_level: Number(productMinimumStock),
      })
      setProductSku('')
      setProductName('')
      setProductPrice('')
      setProductCost('')
      setProductUnit('each')
      setProductMinimumStock('0')
      markComplete()
    }, 'Product created.')
  }

  async function readCSV(file?: File) {
    clearImport()
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setNotice('Choose a .csv file.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setNotice('CSV files must be 5 MB or smaller.')
      return
    }
    try {
      const text = await file.text()
      setCsvText(text)
      setCsvName(file.name)
      setNotice('File loaded locally. Nothing has been sent or saved yet.')
    } catch (error) {
      setNotice(messageFromError(error))
    }
  }

  async function previewImport() {
    if (!importKind || !csvText) {
      setNotice('Choose a CSV file first.')
      return
    }
    if (importKind === 'historical-sales' && !importTillId) {
      setNotice('Choose the default till association for imported receipts.')
      return
    }
    await runAction(async () => {
      const response = await apiClient.post<ImportPreview>(
        `/api/v1/setup/imports/${importKind}/preview`,
        {
          csv_text: csvText,
          default_till_id: importKind === 'historical-sales' ? Number(importTillId) : undefined,
          default_cashier_id: importKind === 'historical-sales' ? Number(importCashierId) : undefined,
        },
      )
      setPreview(response.data)
    }, 'Preview complete. Review every error before importing.')
  }

  async function commitImport() {
    if (!importKind || !csvText || !preview?.valid) {
      setNotice('A valid preview is required before importing.')
      return
    }
    await runAction(async () => {
      const response = await apiClient.post(
        `/api/v1/setup/imports/${importKind}/commit`,
        {
          csv_text: csvText,
          default_till_id: importKind === 'historical-sales' ? Number(importTillId) : undefined,
          default_cashier_id: importKind === 'historical-sales' ? Number(importCashierId) : undefined,
        },
      )
      setCompleted((previous) => previous.includes(step) ? previous : [...previous, step])
      setSkipped((previous) => previous.filter((item) => item !== step))
      clearImport()
      return response.data.already_imported
        ? 'This exact file was already imported. No duplicate records were created.'
        : `Import committed: ${response.data.record_count ?? response.data.row_count} records.`
    }, 'Import complete.')
  }

  async function submitFirstSale(event: FormEvent) {
    event.preventDefault()
    if (!saleTillId || !saleProductId || !confirmRealSale) {
      setNotice('Choose a till and product, then confirm that this will record a real sale.')
      return
    }
    const price = Number(selectedProduct?.price)
    await runAction(async () => {
      const employeeResponse = await employeesAPI.list(user.organization_id)
      const activeEmployees = employeeResponse.data.items.filter((employee) => employee.is_active)
      if (getEmployeeTillAccess(activeEmployees, user.id, Number(saleTillId)) !== 'ready') {
        return 'This login must be linked to an active employee assigned to the selected till. No employee was created or linked automatically. Use Manage employee and till assignments, save the assignment, then retry.'
      }

      const status = await apiClient.get(`/api/v1/tills/${saleTillId}/status`)
      if (status.data.is_open && status.data.operator_id !== user.id) {
        throw new Error('This till is already open for a different operator. Select another till or ask a manager to close the session.')
      }
      if (!status.data.is_open) {
        await apiClient.post(`/api/v1/tills/${saleTillId}/open`, {
          opening_balance: Number(openingBalance),
        })
      }
      await apiClient.post('/api/v1/sales', {
        till_id: Number(saleTillId),
        payment_method: 'CASH',
        amount_tendered: Number(cashTendered),
        items: [{ product_id: Number(saleProductId), quantity: saleQuantity, unit_price: price }],
        is_offline: false,
        notes: 'Recorded during initial setup.',
      })
      markComplete()
    }, 'First sale recorded. Inventory has been updated by the sale service.')
  }

  const selectedSaleTillId = saleTillId === '' ? null : Number(saleTillId)
  const saleEmployeeAccess = getEmployeeTillAccess(employees, user.id, selectedSaleTillId)

  async function submitOpeningCount(event: FormEvent) {
    event.preventDefault()
    if (!stockLocationId || !stockProductId || !confirmStockChange) {
      setNotice('Choose a location and product, then confirm the stock change.')
      return
    }
    await runAction(async () => {
      const current = await apiClient.get<{ items: Array<{ product_id: number; quantity: number }> }>(
        `/api/v1/stock/locations/${stockLocationId}/stock`,
      )
      const existing = current.data.items.find((item) => item.product_id === Number(stockProductId))?.quantity ?? 0
      const delta = Number(stockQuantity) - existing
      if (delta !== 0) {
        await apiClient.post('/api/v1/stock/stock/adjust', {
          product_id: Number(stockProductId),
          location_id: Number(stockLocationId),
          quantity: delta,
          reason: 'PHYSICAL_COUNT_DISCREPANCY',
          note: 'Opening count recorded during initial setup.',
        })
      }
      markComplete()
    }, 'Physical count reconciled to the entered quantity.')
  }

  const isComplete = (index: number) => completed.includes(index)
  const isSkipped = (index: number) => skipped.includes(index)

  return (
    <section className="setup-shell">
      <header className="setup-header">
        <div>
          <p className="setup-kicker">ADMIN · INITIAL CONFIGURATION</p>
          <h2>Get your store ready</h2>
          <p>Set up the essentials, import opening data and choose a first operation. Each step is saved independently.</p>
        </div>
        <a className="setup-manual-link" href="/INITIAL_SETUP_WIZARD.md" target="_blank" rel="noreferrer">
          Open setup manual
        </a>
      </header>

      <div className="setup-progress" aria-label={`Step ${step + 1} of ${STEPS.length}`}>
        <span>Step {step + 1} of {STEPS.length}</span>
        <div className="setup-progress-track"><span style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} /></div>
      </div>

      <div className="setup-layout">
        <nav className="setup-steps" aria-label="Setup steps">
          {STEPS.map((title, index) => (
            <button
              key={title}
              className={`setup-step ${index === step ? 'active' : ''}`}
              onClick={() => setStep(index)}
              type="button"
              aria-current={index === step ? 'step' : undefined}
            >
              <span className={`setup-step-number ${isComplete(index) ? 'complete' : ''}`}>
                {isComplete(index) ? '✓' : index + 1}
              </span>
              <span>{title}{isSkipped(index) ? <small> · deferred</small> : null}</span>
            </button>
          ))}
        </nav>

        <div className="setup-content">
          {loadError && <p className="setup-alert error" role="alert">{loadError}</p>}
          {notice && <p className="setup-alert" role="status">{notice}</p>}

          {step === 0 && (
            <>
              <h3>Configure your organization</h3>
              <p>These details identify your business. Currency is locked after the first stock movement or sale; historical records are never converted.</p>
              <dl className="setup-summary">
                <div><dt>Name</dt><dd>{organization?.name ?? 'Loading…'}</dd></div>
                <div><dt>Code</dt><dd>{organization?.code ?? '—'}</dd></div>
                <div><dt>Administrator</dt><dd>{user.full_name || user.username} · {user.email}</dd></div>
              </dl>
              <form className="setup-form two-columns" onSubmit={updateOrganization}>
                <Field label="Business name" value={organizationSettings.name} onChange={(value) => setOrganizationSettings((current) => ({ ...current, name: value }))} required />
                <Field label="Phone" value={organizationSettings.phone} onChange={(value) => setOrganizationSettings((current) => ({ ...current, phone: value }))} />
                <Field label="Business email" value={organizationSettings.email} onChange={(value) => setOrganizationSettings((current) => ({ ...current, email: value }))} type="email" />
                <Field label="Region" value={organizationSettings.region} onChange={(value) => setOrganizationSettings((current) => ({ ...current, region: value }))} />
                <Field label="Timezone" value={organizationSettings.timezone} onChange={(value) => setOrganizationSettings((current) => ({ ...current, timezone: value }))} required />
                <Field label="Currency (3-letter ISO code)" value={organizationSettings.currency_code} onChange={(value) => setOrganizationSettings((current) => ({ ...current, currency_code: value.toUpperCase() }))} required />
                <label className="setup-field">Business address
                  <textarea value={organizationSettings.address} onChange={(event) => setOrganizationSettings((current) => ({ ...current, address: event.target.value }))} rows={3} />
                </label>
                {organization?.currency_code == null && (
                  <label className="setup-confirm">
                    <input type="checkbox" checked={confirmLegacyCurrency} onChange={(event) => setConfirmLegacyCurrency(event.target.checked)} />
                    If this organization has legacy activity, confirm this currency applies only to future operations; historical records remain unchanged.
                  </label>
                )}
                <button className="setup-primary" disabled={busy || !organization}>Save organization settings</button>
              </form>
            </>
          )}

          {step === 1 && (
            <>
              <h3>Set up locations</h3>
              <p>Locations represent stores or stock sites. Each till must belong to a location.</p>
              <RecordList label="Existing locations" records={locations.map((item) => `${item.name} (${item.code})`)} />
              <form className="setup-form" onSubmit={createLocation}>
                <Field label="Location name" value={locationName} onChange={setLocationName} required />
                <Field label="Location code" value={locationCode} onChange={setLocationCode} required />
                <Field label="Description (optional)" value={locationDescription} onChange={setLocationDescription} />
                <button className="setup-primary" disabled={busy}>Add location</button>
              </form>
              <button className="setup-link-button" type="button" onClick={() => markComplete()}>I have at least one location</button>
            </>
          )}

          {step === 2 && (
            <>
              <h3>Add users</h3>
              <p>Create individual accounts for staff. Never share the administrator account.</p>
              <RecordList label="Current users" records={users.map((item) => `${item.full_name || item.username} · ${item.role}`)} />
              <form className="setup-form two-columns" onSubmit={createStaff}>
                <Field label="Full name" value={staffName} onChange={setStaffName} required />
                <Field label="Username" value={staffUsername} onChange={setStaffUsername} required />
                <Field label="Email" value={staffEmail} onChange={setStaffEmail} required type="email" />
                <Field label="Temporary password" value={staffPassword} onChange={setStaffPassword} required type="password" />
                <label className="setup-field">Role
                  <select value={staffRole} onChange={(event) => setStaffRole(event.target.value as 'manager' | 'operator')}>
                    <option value="operator">Cashier / operator</option>
                    <option value="manager">Manager</option>
                  </select>
                </label>
                <button className="setup-primary" disabled={busy}>Create user</button>
              </form>
              <button className="setup-link-button" type="button" onClick={() => skipStep()}>Defer user setup</button>
            </>
          )}

          {step === 3 && (
            <>
              <h3>Configure tills</h3>
              <p>Add registers and assign each to a location. A till session opens only when an operator starts work.</p>
              <RecordList label="Current tills" records={tills.map((item) => `${item.name} (${item.code})`)} />
              <form className="setup-form two-columns" onSubmit={createTill}>
                <Field label="Till name" value={tillName} onChange={setTillName} required />
                <Field label="Till code" value={tillCode} onChange={setTillCode} required />
                <label className="setup-field">Location
                  <select required value={tillLocationId} onChange={(event) => setTillLocationId(event.target.value ? Number(event.target.value) : '')}>
                    <option value="">Choose a location</option>
                    {locations.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.code})</option>)}
                  </select>
                </label>
                <button className="setup-primary" disabled={busy || locations.length === 0}>Add till</button>
              </form>
              {locations.length === 0 && <p className="setup-help">Add a location before creating a till.</p>}
              <button className="setup-link-button" type="button" onClick={() => skipStep()}>Defer till setup</button>
            </>
          )}

          {step === 4 && (
            <>
              <h3>Load product catalog</h3>
              <p>Create one product or import a CSV. Price and SKU are required; imports are additive and never overwrite existing products.</p>
              <RecordList label={`Products currently loaded (${products.length})`} records={products.slice(0, 5).map((item) => `${item.name} · ${item.sku}`)} />
              <div className="setup-tabs">
                <button type="button" onClick={() => chooseImport('products')}>Import CSV</button>
                <span>or add one product</span>
              </div>
              <form className="setup-form two-columns" onSubmit={createProduct}>
                <Field label="SKU" value={productSku} onChange={setProductSku} required />
                <Field label="Product name" value={productName} onChange={setProductName} required />
                <Field label="Selling price" value={productPrice} onChange={setProductPrice} required type="number" />
                <Field label="Cost (optional)" value={productCost} onChange={setProductCost} type="number" />
                <Field label="Unit of measure" value={productUnit} onChange={setProductUnit} required />
                <Field label="Low-stock threshold" value={productMinimumStock} onChange={setProductMinimumStock} type="number" min={0} step={1} required />
                <button className="setup-primary" disabled={busy}>Add product</button>
              </form>
              {importKind === 'products' && <ImportPanel kind="products" csvName={csvName} preview={preview} busy={busy} onFile={readCSV} onPreview={previewImport} onCommit={commitImport} onClose={() => { setImportKind(null); clearImport() }} />}
            </>
          )}

          {step === 5 && (
            <>
              <h3>Import opening inventory</h3>
              <p>Opening quantities are reconciled as append-only inventory movements at the chosen locations.</p>
              <ImportPanel
                kind="opening-inventory"
                csvName={csvName}
                preview={preview}
                busy={busy}
                onFile={(file) => { setImportKind('opening-inventory'); void readCSV(file) }}
                onPreview={() => { setImportKind('opening-inventory'); void previewImport() }}
                onCommit={() => { setImportKind('opening-inventory'); void commitImport() }}
                onClose={clearImport}
              />
              <button className="setup-link-button" type="button" onClick={() => skipStep()}>Defer opening inventory</button>
            </>
          )}

          {step === 6 && (
            <>
              <h3>Optional: import sales history</h3>
              <p>Historical sales are added for reporting only. They do not create stock movements or change current inventory.</p>
              <div className="setup-form two-columns">
                <label className="setup-field">Associate receipts with till
                  <select value={importTillId} onChange={(event) => { setImportTillId(event.target.value ? Number(event.target.value) : ''); setPreview(null) }}>
                    <option value="">Choose a till</option>
                    {tills.map((item) => <option key={item.id} value={item.id}>{item.name} ({item.code})</option>)}
                  </select>
                </label>
                <label className="setup-field">Import cashier association
                  <select value={importCashierId} onChange={(event) => { setImportCashierId(Number(event.target.value)); setPreview(null) }}>
                    {users.map((item) => <option key={item.id} value={item.id}>{item.full_name || item.username} · {item.role}</option>)}
                  </select>
                </label>
              </div>
              <p className="setup-help">These are Tenga associations, not claims about the source system’s original till or cashier.</p>
              <ImportPanel kind="historical-sales" csvName={csvName} preview={preview} busy={busy} onFile={(file) => { setImportKind('historical-sales'); void readCSV(file) }} onPreview={() => { setImportKind('historical-sales'); void previewImport() }} onCommit={() => { setImportKind('historical-sales'); void commitImport() }} onClose={clearImport} />
              <button className="setup-link-button" type="button" onClick={() => skipStep()}>Skip historical import</button>
            </>
          )}

          {step === 7 && (
            <>
              <h3>Choose a first operation</h3>
              <p>A live sale creates a real transaction and stock movement. A stock count changes the inventory ledger.</p>
              <div className="setup-operation">
                <h4>Guided first sale</h4>
                <form className="setup-form two-columns" onSubmit={submitFirstSale}>
                  <label className="setup-field">Till
                    <select required value={saleTillId} onChange={(event) => setSaleTillId(event.target.value ? Number(event.target.value) : '')}>
                      <option value="">Choose a till</option>
                      {tills.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </label>
                  <label className="setup-field">Product
                    <select required value={saleProductId} onChange={(event) => setSaleProductId(event.target.value ? Number(event.target.value) : '')}>
                      <option value="">Choose a product</option>
                      {products.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.sku} · {item.price}</option>)}
                    </select>
                  </label>
                  <Field label="Quantity" value={String(saleQuantity)} onChange={(value) => setSaleQuantity(Number(value))} type="number" min={1} step={1} required />
                  <Field label="Cash tendered" value={cashTendered} onChange={setCashTendered} type="number" required />
                  <Field label="Opening till cash (if closed)" value={openingBalance} onChange={setOpeningBalance} type="number" required />
                  <label className="setup-confirm"><input type="checkbox" checked={confirmRealSale} onChange={(event) => setConfirmRealSale(event.target.checked)} /> I understand this records a real sale and reduces stock.</label>
                  {saleEmployeeAccess === 'ready' ? (
                    <p className="setup-help" role="status">Your active employee profile is linked to this login and assigned to the selected till.</p>
                  ) : (
                    <div className="setup-operation" role="alert">
                      <p>
                        {saleEmployeeAccess === 'missing-employee'
                          ? 'This login has no active linked employee profile.'
                          : 'The linked employee is not assigned to the selected till.'}
                        {' '}Employee profiles are separate from user accounts; setup will not create or link one automatically.
                      </p>
                      <button className="setup-link-button" type="button" onClick={onManageEmployeeAssignments}>
                        Manage employee and till assignments
                      </button>
                    </div>
                  )}
                  <button className="setup-primary" disabled={busy || !confirmRealSale || !saleTillId || !saleProductId || saleEmployeeAccess !== 'ready'}>
                    Open session if needed and record sale
                  </button>
                </form>
              </div>
              <div className="setup-operation">
                <h4>Or reconcile an opening/physical count</h4>
                <form className="setup-form two-columns" onSubmit={submitOpeningCount}>
                  <label className="setup-field">Location
                    <select required value={stockLocationId} onChange={(event) => setStockLocationId(event.target.value ? Number(event.target.value) : '')}>
                      <option value="">Choose a location</option>
                      {locations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </label>
                  <label className="setup-field">Product
                    <select required value={stockProductId} onChange={(event) => setStockProductId(event.target.value ? Number(event.target.value) : '')}>
                      <option value="">Choose a product</option>
                      {products.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.sku}</option>)}
                    </select>
                  </label>
                  <Field label="Counted quantity" value={stockQuantity} onChange={setStockQuantity} type="number" min={0} step={1} required />
                  <label className="setup-confirm"><input type="checkbox" checked={confirmStockChange} onChange={(event) => setConfirmStockChange(event.target.checked)} /> I understand this writes an inventory adjustment.</label>
                  <button className="setup-secondary" disabled={busy || !confirmStockChange || !stockLocationId || !stockProductId}>Record count adjustment</button>
                </form>
              </div>
              <button className="setup-link-button" type="button" onClick={() => skipStep()}>Finish setup without a transaction</button>
            </>
          )}

          <footer className="setup-footer">
            <button type="button" className="setup-secondary" onClick={() => setStep((current) => Math.max(0, current - 1))} disabled={step === 0}>Previous</button>
            <span>{completed.length} of 8 steps confirmed{skipped.length ? ` · ${skipped.length} deferred` : ''}</span>
            <button type="button" className="setup-primary" onClick={() => setStep((current) => Math.min(STEPS.length - 1, current + 1))} disabled={step === STEPS.length - 1}>Next step</button>
          </footer>
        </div>
      </div>
    </section>
  )
}

function Field({
  label,
  value,
  onChange,
  required = false,
  type = 'text',
  min,
  step,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  required?: boolean
  type?: string
  min?: number
  step?: number | 'any'
}) {
  return (
    <label className="setup-field">{label}
      <input type={type} required={required} min={min ?? (type === 'number' ? 0 : undefined)} step={step ?? (type === 'number' ? 'any' : undefined)} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  )
}

function RecordList({ label, records }: { label: string; records: string[] }) {
  return (
    <div className="setup-record-list">
      <strong>{label}</strong>
      {records.length
        ? <ul>{records.map((record) => <li key={record}>{record}</li>)}</ul>
        : <p>No records found yet.</p>}
    </div>
  )
}

function ImportPanel({
  kind,
  csvName,
  preview,
  busy,
  onFile,
  onPreview,
  onCommit,
  onClose,
}: {
  kind: ImportKind
  csvName: string
  preview: ImportPreview | null
  busy: boolean
  onFile: (file?: File) => void
  onPreview: () => void
  onCommit: () => void
  onClose: () => void
}) {
  const title = kind === 'products' ? 'products.csv'
    : kind === 'opening-inventory' ? 'opening-inventory.csv'
      : 'historical-sales.csv'
  return (
    <div className="setup-import">
      <h4>CSV import</h4>
      <p>Use the required header row from the <a href="/INITIAL_SETUP_WIZARD.md" target="_blank" rel="noreferrer">manual</a>. Maximum 5 MB and 5,000 rows.</p>
      <p className="setup-code">{title}</p>
      <label className="setup-field">Choose a CSV file
        <input type="file" accept=".csv,text/csv" onChange={(event) => onFile(event.target.files?.[0])} />
      </label>
      {csvName && <p className="setup-help">Selected: {csvName} · preview is local until you click Validate.</p>}
      <div className="setup-button-row">
        <button type="button" className="setup-secondary" disabled={!csvName || busy} onClick={onPreview}>Validate and preview</button>
        <button type="button" className="setup-secondary" onClick={onClose}>Clear file</button>
      </div>
      {preview && (
        <div className="setup-preview">
          <p role="status">{preview.valid ? `${preview.row_count} rows ready.` : `${preview.errors.length} validation error(s). No rows were imported.`}</p>
          {preview.errors.length > 0 && <ul className="setup-errors">{preview.errors.map((error) => <li key={error}>{error}</li>)}</ul>}
          {preview.rows.length > 0 && (
            <ul className="setup-preview-rows">
              {preview.rows.map((row) => (
                <li key={`${row.row}-${row.reference}`}>
                  Row {row.row}: {row.reference || 'record'} — {row.status}
                </li>
              ))}
            </ul>
          )}
          <button type="button" className="setup-primary" disabled={busy || !preview.valid} onClick={onCommit}>Import {preview.row_count} rows</button>
        </div>
      )}
    </div>
  )
}
