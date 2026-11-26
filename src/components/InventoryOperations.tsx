import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  catalogImportAPI,
  inventoryAPI,
  locationsAPI,
  productsAPI_v2,
  type CsvImportPreview,
  type InventoryCount,
  type InventoryMovement,
  type Location,
  type Product,
} from '../api'
import { getOfflineOperationQueue, notifyOfflineQueueUpdated, syncOrganizationOperations } from '../offline/runtime'
import type { OfflineOperation } from '../offline/operationQueue'
import { reconcileInventoryCount, reviewInventoryCount } from './inventoryCountReconciliation'
import { useAuthStore } from '../stores'
import {
  buildCountLines,
  operationStatusLabel,
  provisionalStockDelta,
  toQueuedInventoryOperation,
  type InventoryActionInput,
} from './inventoryWorkflow'
import { OfflineSyncStatus } from './OfflineSyncStatus'

type View = 'receipt' | 'issue' | 'adjustment' | 'transfer' | 'count' | 'history' | 'reports' | 'import'
type CatalogProduct = Pick<Product, 'id' | 'name' | 'sku' | 'unit_of_measure'>
type CatalogLocation = Pick<Location, 'id' | 'name' | 'code'>
type Props = { initialView?: View; initialProductId?: number }
const HISTORY_PAGE_SIZE = 50

const views: Array<{ id: View; label: string }> = [
  { id: 'receipt', label: 'Receive' },
  { id: 'issue', label: 'Issue' },
  { id: 'adjustment', label: 'Adjust' },
  { id: 'transfer', label: 'Transfer' },
  { id: 'count', label: 'Count' },
  { id: 'history', label: 'Movement history' },
  { id: 'reports', label: 'Reports' },
  { id: 'import', label: 'CSV import/export' },
]

function errorText(error: unknown): string {
  if (typeof error === 'object' && error && 'response' in error) {
    const data = (error as { response?: { data?: { detail?: unknown } } }).response?.data
    if (typeof data?.detail === 'string') return data.detail
    if (data?.detail) return JSON.stringify(data.detail)
  }
  return error instanceof Error ? error.message : 'The request failed. Please try again.'
}

function downloadCsv(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.append(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export default function InventoryOperations({
  initialView = 'receipt',
  initialProductId,
}: Props) {
  const user = useAuthStore((state) => state.user)
  const [view, setView] = useState<View>(initialView)
  const [locations, setLocations] = useState<CatalogLocation[]>([])
  const [products, setProducts] = useState<CatalogProduct[]>([])
  const [catalogCachedAt, setCatalogCachedAt] = useState<number | null>(null)
  const [catalogError, setCatalogError] = useState('')
  const [queue, setQueue] = useState<OfflineOperation[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<number | ''>('')
  const [sourceLocationId, setSourceLocationId] = useState<number | ''>('')
  const [destinationLocationId, setDestinationLocationId] = useState<number | ''>('')
  const [productId, setProductId] = useState<number | ''>(initialProductId ?? '')
  const [quantity, setQuantity] = useState('')
  const [unitCost, setUnitCost] = useState('')
  const [reason, setReason] = useState('RECEIPT')
  const [adjustmentDirection, setAdjustmentDirection] = useState<'INCREASE' | 'DECREASE'>('DECREASE')
  const [adjustmentReason, setAdjustmentReason] = useState('ADJUSTMENT')
  const [notes, setNotes] = useState('')
  const [countValues, setCountValues] = useState<Record<number, string>>({})
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [history, setHistory] = useState<InventoryMovement[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historySkip, setHistorySkip] = useState(0)
  const [lowStock, setLowStock] = useState<Array<{ product_id: number; product_name: string; quantity: number; minimum_stock_level: number }>>([])
  const [valuation, setValuation] = useState<{ currency_code: string | null; total_value: number | string | null } | null>(null)
  const [csvKind, setCsvKind] = useState<'products' | 'opening-stock'>('products')
  const [csvText, setCsvText] = useState('')
  const [csvName, setCsvName] = useState('')
  const [csvPreview, setCsvPreview] = useState<CsvImportPreview | null>(null)
  const [countReview, setCountReview] = useState<{ operationId: string; count: InventoryCount } | null>(null)
  const manager = user?.role === 'admin' || user?.role === 'manager'

  const refreshQueue = useCallback(async () => {
    if (!user) return
    try {
      setQueue(await getOfflineOperationQueue().list(user.organization_id))
    } catch (caught) {
      setError(errorText(caught))
    }
  }, [user])

  useEffect(() => {
    let active = true
    async function loadCatalog() {
      if (!user) return
      setCatalogError('')
      try {
        const [locationsResponse, firstPage] = await Promise.all([
          locationsAPI.list(user.organization_id, 0, 100),
          productsAPI_v2.list({ organization_id: user.organization_id, skip: 0, limit: 100 }),
        ])
        const allProducts = [...firstPage.data.items]
        for (let skip = firstPage.data.items.length; skip < firstPage.data.total; skip += 100) {
          const page = await productsAPI_v2.list({
            organization_id: user.organization_id,
            skip,
            limit: 100,
          })
          allProducts.push(...page.data.items)
        }
        if (!active) return
        const catalogProducts = allProducts.map(({ id, name, sku, unit_of_measure }) => ({
          id, name, sku, unit_of_measure: unit_of_measure || 'each',
        }))
        setLocations(locationsResponse.data.items)
        setProducts(catalogProducts)
        setSelectedLocationId((current) =>
          current || locationsResponse.data.items[0]?.id || '',
        )
        setSourceLocationId((current) => current || locationsResponse.data.items[0]?.id || '')
        setDestinationLocationId((current) =>
          current || locationsResponse.data.items.find((item) => item.id !== locationsResponse.data.items[0]?.id)?.id || '',
        )
        await getOfflineOperationQueue().saveCatalog({
          organizationId: user.organization_id,
          cachedAt: Date.now(),
          products: catalogProducts,
          locations: locationsResponse.data.items.map(({ id, name, code }) => ({ id, name, code: code || '' })),
        })
      } catch {
        try {
          const cached = await getOfflineOperationQueue().getCatalog(user.organization_id)
          if (!active) return
          if (cached) {
            setProducts(cached.products)
            setLocations(cached.locations)
            setCatalogCachedAt(cached.cachedAt)
            setSelectedLocationId((current) => current || cached.locations[0]?.id || '')
            setSourceLocationId((current) => current || cached.locations[0]?.id || '')
            setDestinationLocationId((current) =>
              current || cached.locations.find((item) => item.id !== cached.locations[0]?.id)?.id || '',
            )
          } else {
            setCatalogError('Product and location choices are unavailable offline. Connect once to load this organization’s catalog before capturing offline stock operations.')
          }
        } catch (caught) {
          setCatalogError(`Offline catalog could not be loaded: ${errorText(caught)}`)
        }
      }
    }
    void loadCatalog()
    void refreshQueue()
    return () => { active = false }
  }, [user?.id, user?.organization_id, refreshQueue])

  useEffect(() => {
    if (initialProductId) setProductId(initialProductId)
  }, [initialProductId])

  const selectedProduct = products.find((product) => product.id === Number(productId))
  const provisionalDelta = useMemo(() => {
    const balanceLocationId = view === 'transfer' ? sourceLocationId : selectedLocationId
    if (!selectedProduct || !balanceLocationId) return 0
    return queue.reduce(
      (total, operation) => total + provisionalStockDelta(operation, selectedProduct.id, Number(balanceLocationId)),
      0,
    )
  }, [queue, selectedLocationId, selectedProduct, sourceLocationId, view])

  async function enqueueAndSync(input: InventoryActionInput) {
    if (!user) throw new Error('Authentication is required.')
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const { operationType, payload } = toQueuedInventoryOperation(input)
      const operation = await getOfflineOperationQueue().enqueue({
        organizationId: user.organization_id,
        operationType,
        payload,
      })
      notifyOfflineQueueUpdated()
      await refreshQueue()
      if (!navigator.onLine) {
        setNotice(`Saved on this device as pending (${operation.operationId}). The balance is provisional until the server acknowledges sync.`)
        return
      }
      await syncOrganizationOperations(user.organization_id)
      await refreshQueue()
      const saved = await getOfflineOperationQueue().get(user.organization_id, operation.operationId)
      if (!saved) {
        setError('The operation was queued, but its status could not be read. Do not repeat it; retry sync from the queue.')
      } else if (saved.status === 'SYNCED') {
        setNotice(`${operationType.replace(/_/g, ' ').toLowerCase()} applied by the server (operation ${operation.operationId}).`)
      } else if (saved.status === 'RECONCILIATION_REQUIRED') {
        setNotice(`Saved by the server and requires explicit review/reconciliation (operation ${operation.operationId}).`)
      } else {
        setNotice(`Saved on this device; status: ${operationStatusLabel(saved)}. It has not been reported as applied.`)
      }
    } catch (caught) {
      setError(`Operation was not confirmed as saved: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function submitStockAction(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const location = Number(selectedLocationId)
    const product = Number(productId)
    const amount = Number(quantity)
    if (!Number.isSafeInteger(product) || product <= 0 || !Number.isSafeInteger(location) || location <= 0) {
      setError('Choose a product and location.')
      return
    }
    if (!Number.isSafeInteger(amount) || amount <= 0) {
      setError('Quantity must be a positive whole number.')
      return
    }
    if (view === 'receipt' && unitCost !== '' && (!Number.isFinite(Number(unitCost)) || Number(unitCost) < 0)) {
      setError('Unit cost must be a non-negative amount.')
      return
    }
    const input: InventoryActionInput = view === 'receipt'
      ? {
          operationType: 'INVENTORY_RECEIPT',
          product_id: product,
          location_id: location,
          quantity: amount,
          reason: reason.trim() || 'RECEIPT',
          ...(unitCost === '' ? {} : { unit_cost: Number(unitCost) }),
        }
      : view === 'issue'
        ? {
            operationType: 'INVENTORY_ISSUE',
            product_id: product,
            location_id: location,
            quantity: amount,
            reason: reason.trim(),
          }
        : {
            operationType: 'INVENTORY_ADJUSTMENT',
            product_id: product,
            location_id: location,
            quantity: adjustmentDirection === 'INCREASE' ? amount : -amount,
            reason: adjustmentReason,
          }
    await enqueueAndSync(input)
    setQuantity('')
  }

  async function submitTransfer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const product = Number(productId)
    const amount = Number(quantity)
    if (!manager) {
      setError('Only an administrator or manager can transfer stock.')
      return
    }
    if (!Number.isSafeInteger(product) || product <= 0 || !Number.isSafeInteger(amount) || amount <= 0) {
      setError('Choose a product and enter a positive whole-number quantity.')
      return
    }
    if (!sourceLocationId || !destinationLocationId || sourceLocationId === destinationLocationId) {
      setError('Choose different source and destination locations.')
      return
    }
    await enqueueAndSync({
      operationType: 'INVENTORY_TRANSFER',
      source_location_id: Number(sourceLocationId),
      destination_location_id: Number(destinationLocationId),
      lines: [{ product_id: product, quantity: amount }],
      reason: reason.trim() || 'TRANSFER',
    })
    setQuantity('')
  }

  async function submitCount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedLocationId) {
      setError('Choose a location.')
      return
    }
    const lines = buildCountLines(products.map((product) => product.id), countValues)
    if (lines.some((line) => line.observed_quantity !== null
      && (!Number.isSafeInteger(line.observed_quantity) || line.observed_quantity < 0))) {
      setError('Every observed quantity must be a whole non-negative number.')
      return
    }
    if (!lines.some((line) => line.observed_quantity !== null)) {
      setError('Enter at least one observed quantity. Blank products remain uncounted, not zero.')
      return
    }
    await enqueueAndSync({
      operationType: 'INVENTORY_COUNT',
      location_id: Number(selectedLocationId),
      lines,
      notes: notes || undefined,
    })
    setCountValues({})
  }

  async function reviewCount(operation: OfflineOperation) {
    if (!operation.acknowledgement?.appliedEntityId) {
      setError('The server did not return a count identifier. The operation remains visible for manual follow-up.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await reviewInventoryCount(
        operation,
        user!.organization_id,
        async (countId) => (await inventoryAPI.getCount(countId)).data,
        getOfflineOperationQueue(),
      )
      if (result.resolved) {
        notifyOfflineQueueUpdated()
        await refreshQueue()
        setCountReview(null)
        setNotice(`Count ${result.count.id} was already reconciled and is now confirmed on this device.`)
        return
      }
      setCountReview({ operationId: operation.operationId, count: result.count })
    } catch (caught) {
      setError(`Count review could not be loaded. The count was not reconciled: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function reconcileCount(operation: OfflineOperation) {
    if (!manager || !operation.acknowledgement?.appliedEntityId || !countReview) return
    if (!window.confirm('Post the displayed physical-count differences to the inventory ledger? This will create stock movements.')) return
    setBusy(true)
    setError('')
    try {
      const result = await reconcileInventoryCount(
        operation,
        countReview.count,
        user!.organization_id,
        async (countId) => (await inventoryAPI.getCount(countId)).data,
        async (countId, observations) =>
          (await inventoryAPI.reconcileCount(countId, observations)).data,
        getOfflineOperationQueue(),
      )
      if (result.reviewChanged) {
        setCountReview({ operationId: operation.operationId, count: result.count })
        setError('The count changed since it was reviewed. Review the refreshed count before posting.')
        return
      }
      notifyOfflineQueueUpdated()
      await refreshQueue()
      setCountReview(null)
      setNotice(result.alreadyReconciled
        ? `Count ${result.count.id} was already reconciled and is now confirmed on this device.`
        : `Count ${result.count.id} was explicitly reconciled and posted.`)
    } catch (caught) {
      setError(`Count was not confirmed as reconciled: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function loadHistory(skip = historySkip) {
    if (!navigator.onLine) {
      setError('Movement history is server-authoritative and unavailable offline.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const result = await inventoryAPI.listMovementHistory({
        location_id: selectedLocationId ? Number(selectedLocationId) : undefined,
        product_id: productId ? Number(productId) : undefined,
        skip,
        limit: HISTORY_PAGE_SIZE,
      })
      setHistory(result.data.items)
      setHistoryTotal(result.data.total)
      setHistorySkip(skip)
    } catch (caught) {
      setError(`Movement history could not be loaded: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function loadReports() {
    if (!navigator.onLine) {
      setError('Inventory reports are server-authoritative and unavailable offline.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const [low, value] = await Promise.all([
        inventoryAPI.getLowStock(selectedLocationId ? Number(selectedLocationId) : undefined),
        inventoryAPI.getValuation(selectedLocationId ? Number(selectedLocationId) : undefined),
      ])
      setLowStock(low.data.items)
      setValuation({ currency_code: value.data.currency_code, total_value: value.data.total_value })
    } catch (caught) {
      setError(`Inventory reports could not be loaded: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function previewCsv() {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = csvKind === 'products'
        ? await catalogImportAPI.previewProducts(csvText)
        : await catalogImportAPI.previewOpeningStock(csvText)
      setCsvPreview(response.data)
    } catch (caught) {
      setError(`CSV preview failed: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function commitCsv() {
    if (!csvPreview?.valid || !manager) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = csvKind === 'products'
        ? await catalogImportAPI.commitProducts(csvText)
        : await catalogImportAPI.commitOpeningStock(csvText)
      setNotice(`Import committed by the server: ${response.data.record_count} records, batch ${response.data.batch_id}.`)
      setCsvPreview(null)
      await refreshQueue()
    } catch (caught) {
      setError(`CSV import was not confirmed: ${errorText(caught)}`)
    } finally {
      setBusy(false)
    }
  }

  async function downloadTemplate() {
    try {
      const result = csvKind === 'products'
        ? await catalogImportAPI.getProductTemplate()
        : await catalogImportAPI.getOpeningStockTemplate()
      downloadCsv(result.data, csvKind === 'products' ? 'products-template.csv' : 'opening-stock-template.csv')
    } catch (caught) {
      setError(`Template download failed: ${errorText(caught)}`)
    }
  }

  async function exportProducts() {
    try {
      const result = await catalogImportAPI.exportProducts()
      downloadCsv(result.data, 'products.csv')
    } catch (caught) {
      setError(`Product export failed: ${errorText(caught)}`)
    }
  }

  function chooseCsv(file?: File) {
    if (!file) return
    setCsvName(file.name)
    setCsvPreview(null)
    void file.text().then(setCsvText).catch(() => setError('The selected CSV file could not be read.'))
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-6">
      <header className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900">Inventory operations</h1>
        <p className="mt-1 text-sm text-gray-600">
          The server ledger is authoritative. Locally queued quantities are provisional until acknowledged.
        </p>
        <div className="mt-3"><OfflineSyncStatus organizationId={user?.organization_id ?? 0} /></div>
      </header>

      {catalogError && <p role="alert" className="mb-4 rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">{catalogError}</p>}
      {catalogCachedAt && !navigator.onLine && (
        <p role="status" className="mb-4 text-sm text-amber-800">
          Using cached product/location choices from {new Date(catalogCachedAt).toLocaleString()}; balances are not cached as authoritative.
        </p>
      )}
      {error && <p role="alert" className="mb-4 rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {notice && <p role="status" className="mb-4 rounded border border-green-300 bg-green-50 p-3 text-sm text-green-800">{notice}</p>}

      <nav aria-label="Inventory workflows" className="mb-5 flex flex-wrap gap-2">
        {views.map((item) => (
          <button
            key={item.id}
            type="button"
            aria-current={view === item.id ? 'page' : undefined}
            onClick={() => { setView(item.id); setError(''); setNotice('') }}
            className={`rounded px-3 py-2 text-sm font-medium ${view === item.id ? 'bg-indigo-100 text-indigo-800' : 'border bg-white text-gray-700'}`}
          >
            {item.label}
          </button>
        ))}
        <button type="button" disabled title="Customer and supplier returns are not supported in this release." className="cursor-not-allowed rounded border px-3 py-2 text-sm text-gray-400">
          Returns unavailable
        </button>
      </nav>

      <div className="mb-4 grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-2">
        <label className="text-sm font-medium text-gray-700">
          {view === 'transfer' ? 'Source location' : 'Location'}
          <select
            value={view === 'transfer' ? sourceLocationId : selectedLocationId}
            onChange={(event) => {
              if (view === 'transfer') setSourceLocationId(event.target.value ? Number(event.target.value) : '')
              else setSelectedLocationId(event.target.value ? Number(event.target.value) : '')
              setHistorySkip(0)
            }}
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-2"
          >
            <option value="">Select location</option>
            {locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}
          </select>
        </label>
        {view === 'transfer' ? (
          <label className="text-sm font-medium text-gray-700">
            Destination location
            <select value={destinationLocationId} onChange={(event) => setDestinationLocationId(event.target.value ? Number(event.target.value) : '')} className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-2">
              <option value="">Select destination</option>
              {locations.map((location) => <option key={location.id} value={location.id}>{location.name}</option>)}
            </select>
          </label>
        ) : view === 'history' ? (
          <label className="text-sm font-medium text-gray-700">
            Product (optional)
            <select value={productId} onChange={(event) => { setProductId(event.target.value ? Number(event.target.value) : ''); setHistorySkip(0) }} className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-2">
              <option value="">All products</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name} ({product.sku})</option>)}
            </select>
          </label>
        ) : null}
      </div>

      {(view === 'receipt' || view === 'issue' || view === 'adjustment' || view === 'transfer') && (
        <form onSubmit={view === 'transfer' ? submitTransfer : submitStockAction} className="max-w-3xl space-y-4 rounded-lg border bg-white p-5">
          <label className="block text-sm font-medium text-gray-700">
            Product
            <select required value={productId} onChange={(event) => setProductId(event.target.value ? Number(event.target.value) : '')} className="mt-1 block w-full rounded border px-3 py-2">
              <option value="">Select product</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name} ({product.sku})</option>)}
            </select>
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Quantity (whole {selectedProduct?.unit_of_measure || 'units'})
            <input type="number" min="1" step="1" required value={quantity} onChange={(event) => setQuantity(event.target.value)} className="mt-1 block w-full rounded border px-3 py-2" />
          </label>
          {view === 'receipt' && (
            <label className="block text-sm font-medium text-gray-700">
              Unit cost (optional, major currency units)
              <input type="number" min="0" step="0.01" value={unitCost} onChange={(event) => setUnitCost(event.target.value)} className="mt-1 block w-full rounded border px-3 py-2" />
            </label>
          )}
          {view !== 'transfer' && (
            <label className="block text-sm font-medium text-gray-700">
              {view === 'adjustment' ? 'Adjustment reason' : 'Reason'}
              {view === 'adjustment' ? (
                <div className="mt-1 grid grid-cols-2 gap-2">
                <select aria-label="Adjustment direction" value={adjustmentDirection} onChange={(event) => setAdjustmentDirection(event.target.value as typeof adjustmentDirection)} className="rounded border px-3 py-2">
                  <option value="DECREASE">Decrease</option>
                  <option value="INCREASE">Increase</option>
                </select>
                <select aria-label="Adjustment reason" value={adjustmentReason} onChange={(event) => setAdjustmentReason(event.target.value)} className="rounded border px-3 py-2">
                  <option value="ADJUSTMENT">General adjustment</option>
                  <option value="DAMAGE">Damage</option>
                  <option value="SHRINKAGE">Shrinkage</option>
                  <option value="PHYSICAL_COUNT_DISCREPANCY">Physical count discrepancy</option>
                </select>
                </div>
              ) : (
                <input required value={reason} onChange={(event) => setReason(event.target.value)} className="mt-1 block w-full rounded border px-3 py-2" />
              )}
            </label>
          )}
          {view === 'transfer' && (
            <label className="block text-sm font-medium text-gray-700">
              Reason
              <input required value={reason} onChange={(event) => setReason(event.target.value)} className="mt-1 block w-full rounded border px-3 py-2" />
            </label>
          )}
          {selectedProduct && selectedLocationId && (
            <p className="rounded bg-amber-50 p-3 text-sm text-amber-900">
              Provisional local change for {selectedProduct.name} at this location: {provisionalDelta > 0 ? '+' : ''}{provisionalDelta} {selectedProduct.unit_of_measure}. This is not a server-confirmed balance.
            </p>
          )}
          {view === 'transfer' && !manager && <p role="alert" className="text-sm text-red-700">Transfers require administrator or manager permission.</p>}
          <button disabled={busy || (view === 'transfer' && !manager)} className="rounded bg-indigo-600 px-4 py-2 font-medium text-white disabled:opacity-50">
            {busy ? 'Saving…' : `Save ${view === 'receipt' ? 'receipt' : view === 'issue' ? 'issue' : view === 'adjustment' ? 'adjustment' : 'transfer'}`}
          </button>
        </form>
      )}

      {view === 'count' && (
        <form onSubmit={submitCount} className="space-y-4 rounded-lg border bg-white p-5">
          <p className="text-sm text-gray-700">Count observations are saved as a draft. They do not change stock until a manager reviews the differences and explicitly posts reconciliation.</p>
          {products.length === 0 ? <p className="text-sm text-gray-600">No products are available for this count.</p> : (
            <div className="max-h-[28rem] overflow-auto">
              <table className="w-full text-left text-sm">
                <thead><tr className="border-b"><th className="p-2">Product</th><th className="p-2">Observed quantity</th></tr></thead>
                <tbody>{products.map((product) => (
                  <tr key={product.id} className="border-b">
                    <td className="p-2">{product.name} <span className="text-xs text-gray-500">({product.sku})</span></td>
                    <td className="p-2"><input aria-label={`Observed quantity for ${product.name}`} type="number" min="0" step="1" value={countValues[product.id] ?? ''} onChange={(event) => setCountValues((current) => ({ ...current, [product.id]: event.target.value }))} className="w-36 rounded border px-2 py-1" /></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <label className="block text-sm font-medium text-gray-700">Count notes<textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={2} className="mt-1 block w-full rounded border px-3 py-2" /></label>
          <button disabled={busy || !selectedLocationId || products.length === 0} className="rounded bg-indigo-600 px-4 py-2 font-medium text-white disabled:opacity-50">Save count observations</button>
        </form>
      )}

      {view === 'history' && (
        <section className="rounded-lg border bg-white p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div><h2 className="font-semibold">Immutable movement ledger</h2><p className="text-sm text-gray-600">{historyTotal} movements match the selected filters.</p></div>
            <button type="button" onClick={() => void loadHistory()} disabled={busy} className="rounded border px-3 py-2 text-sm">Refresh history</button>
          </div>
          {!navigator.onLine && <p className="mb-3 text-sm text-amber-800">History requires the server and is not shown from a local cache while offline.</p>}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b"><th className="p-2">Date</th><th className="p-2">Product</th><th className="p-2">Movement</th><th className="p-2">Quantity</th><th className="p-2">Reason</th><th className="p-2">From → To</th></tr></thead>
              <tbody>{history.map((movement) => {
                const product = products.find((item) => item.id === movement.product_id)
                return <tr key={movement.id} className="border-b">
                  <td className="p-2">{new Date(movement.created_at).toLocaleString()}</td>
                  <td className="p-2">{product?.name ?? `Product #${movement.product_id}`}</td>
                  <td className="p-2">{movement.movement_type}</td>
                  <td className="p-2">{movement.quantity}</td>
                  <td className="p-2">{movement.reason}</td>
                  <td className="p-2">{locations.find((item) => item.id === movement.location_id)?.name ?? movement.location_id} {movement.to_location_id ? `→ ${locations.find((item) => item.id === movement.to_location_id)?.name ?? movement.to_location_id}` : ''}</td>
                </tr>
              })}</tbody>
            </table>
            {history.length === 0 && <p className="py-5 text-sm text-gray-600">Select filters and refresh to load movement history.</p>}
          </div>
          {historyTotal > HISTORY_PAGE_SIZE && (
            <div className="mt-4 flex items-center justify-between">
              <span className="text-sm text-gray-600">Page {Math.floor(historySkip / HISTORY_PAGE_SIZE) + 1} of {Math.ceil(historyTotal / HISTORY_PAGE_SIZE)}</span>
              <div className="flex gap-2">
                <button type="button" disabled={busy || historySkip === 0} onClick={() => void loadHistory(Math.max(0, historySkip - HISTORY_PAGE_SIZE))} className="rounded border px-3 py-2 text-sm disabled:opacity-50">Previous</button>
                <button type="button" disabled={busy || historySkip + HISTORY_PAGE_SIZE >= historyTotal} onClick={() => void loadHistory(historySkip + HISTORY_PAGE_SIZE)} className="rounded border px-3 py-2 text-sm disabled:opacity-50">Next</button>
              </div>
            </div>
          )}
        </section>
      )}

      {view === 'reports' && (
        <section className="rounded-lg border bg-white p-5">
          <div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">Low-stock and valuation reports</h2><button type="button" disabled={busy} onClick={() => void loadReports()} className="rounded border px-3 py-2 text-sm">Refresh reports</button></div>
          {valuation && <p className="mb-4 text-sm">Known inventory value: {valuation.currency_code ?? 'Currency not configured'} {valuation.total_value ?? 'unavailable'}</p>}
          <h3 className="mb-2 font-medium">At or below minimum stock</h3>
          <ul className="divide-y">{lowStock.map((item) => <li key={`${item.product_id}:${selectedLocationId}`} className="py-2 text-sm">{item.product_name}: {item.quantity} on hand; threshold {item.minimum_stock_level}</li>)}</ul>
          {lowStock.length === 0 && <p className="text-sm text-gray-600">No low-stock report loaded, or no products are below threshold.</p>}
        </section>
      )}

      {view === 'import' && (
        <section className="max-w-4xl space-y-4 rounded-lg border bg-white p-5">
          <h2 className="font-semibold">Catalog CSV</h2>
          <p className="text-sm text-gray-700">CSV imports use the authenticated server preview and atomic commit endpoints. No import is queued or claimed successful offline.</p>
          <label className="block text-sm font-medium text-gray-700">CSV type
            <select value={csvKind} onChange={(event) => { setCsvKind(event.target.value as typeof csvKind); setCsvPreview(null) }} className="mt-1 block w-full rounded border px-3 py-2">
              <option value="products">Products</option>
              <option value="opening-stock">Opening stock</option>
            </select>
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => void downloadTemplate()} className="rounded border px-3 py-2 text-sm">Download template</button>
            <button type="button" onClick={() => void exportProducts()} className="rounded border px-3 py-2 text-sm">Export products</button>
          </div>
          {!manager && <p role="alert" className="text-sm text-amber-800">Import preview and commit are administrator-only on the API. Product export remains available.</p>}
          <label className="block text-sm font-medium text-gray-700">Choose CSV file
            <input type="file" accept=".csv,text/csv" onChange={(event) => chooseCsv(event.target.files?.[0])} className="mt-1 block w-full" />
          </label>
          {csvName && <p className="text-sm text-gray-600">Selected: {csvName}</p>}
          <label className="block text-sm font-medium text-gray-700">CSV content<textarea value={csvText} onChange={(event) => { setCsvText(event.target.value); setCsvPreview(null) }} rows={8} className="mt-1 block w-full rounded border px-3 py-2 font-mono text-xs" /></label>
          <button type="button" disabled={busy || !manager || !csvText.trim()} onClick={() => void previewCsv()} className="rounded bg-indigo-600 px-4 py-2 font-medium text-white disabled:opacity-50">Preview import</button>
          {csvPreview && (
            <div className="rounded border p-3">
              <p className="font-medium">{csvPreview.valid ? 'Preview valid' : 'Preview has errors'} · {csvPreview.valid_count}/{csvPreview.row_count} rows valid</p>
              {csvPreview.already_imported && <p className="text-sm text-amber-800">This file was already imported; committing will return the existing batch.</p>}
              {csvPreview.rows.length > 0 && (
                <div className="mt-3 overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead><tr className="border-b">{Object.keys(csvPreview.rows[0]).map((key) => <th key={key} className="p-2">{key}</th>)}</tr></thead>
                    <tbody>{csvPreview.rows.slice(0, 10).map((row, index) => (
                      <tr key={index} className="border-b">
                        {Object.keys(csvPreview.rows[0]).map((key) => <td key={key} className="p-2">{String(row[key] ?? '')}</td>)}
                      </tr>
                    ))}</tbody>
                  </table>
                  {csvPreview.rows.length > 10 && <p className="mt-1 text-xs text-gray-500">Showing first 10 preview rows.</p>}
                </div>
              )}
              <ul className="mt-2 list-disc pl-5 text-sm text-red-700">
                {csvPreview.errors.map((item, index) => <li key={`${item.row_number}:${item.field}:${index}`}>Row {item.row_number}, {item.field}: {item.message}</li>)}
              </ul>
              <button type="button" disabled={busy || !manager || !csvPreview.valid} onClick={() => void commitCsv()} className="mt-3 rounded bg-green-700 px-4 py-2 font-medium text-white disabled:opacity-50">Commit validated import</button>
            </div>
          )}
        </section>
      )}

      <section className="mt-6 rounded-lg border bg-white p-4">
        <h2 className="mb-2 font-semibold">Saved operations on this device</h2>
        {queue.length === 0 ? <p className="text-sm text-gray-600">No locally recorded inventory operations.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b"><th className="p-2">Recorded</th><th className="p-2">Operation</th><th className="p-2">State</th><th className="p-2">Details</th><th className="p-2">Action</th></tr></thead>
              <tbody>{queue.map((operation) => (
                <tr key={`${operation.organizationId}:${operation.operationId}`} className="border-b align-top">
                  <td className="p-2">{new Date(operation.createdAt).toLocaleString()}</td>
                  <td className="p-2">{operation.operationType.replace(/_/g, ' ')}</td>
                  <td className="p-2">{operationStatusLabel(operation)}</td>
                  <td className="p-2">{operation.acknowledgement?.errorMessage ?? operation.lastError ?? operation.operationId}</td>
                  <td className="p-2">
                    {operation.status === 'RECONCILIATION_REQUIRED' && !operation.acknowledgement?.reconciliationResolvedAt && operation.operationType === 'INVENTORY_COUNT' && (
                      <button type="button" disabled={busy} onClick={() => void reviewCount(operation)} className="rounded border px-2 py-1">Review count</button>
                    )}
                    {operation.operationType === 'INVENTORY_COUNT'
                      && countReview?.operationId === operation.operationId
                      && !operation.acknowledgement?.reconciliationResolvedAt && (
                        <div className="mt-2 min-w-64">
                          <p className="font-medium">Count #{countReview.count.id} · {countReview.count.status}</p>
                          <ul className="my-2">{countReview.count.lines.map((line) => (
                            <li key={line.product_id}>{line.product_name}: expected {line.expected_quantity}, observed {line.observed_quantity ?? 'not counted'}, difference {line.difference ?? '—'}</li>
                          ))}</ul>
                          {manager && countReview.count.status === 'DRAFT' && (
                            <button type="button" disabled={busy} onClick={() => void reconcileCount(operation)} className="rounded bg-indigo-700 px-2 py-1 text-white">Post count differences</button>
                          )}
                        </div>
                      )}
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>
      <p className="mt-4 text-xs text-gray-600">
        Customer and supplier returns are not part of this release. Do not record a return as a stock receipt. Offline sync runs in the authenticated app only; the service worker never replays mutations.
      </p>
    </main>
  )
}
