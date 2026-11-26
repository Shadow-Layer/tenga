export type CashSaleRequest = {
  till_id: number
  till_session_id: number
  payment_method: 'CASH'
  expected_total: string
  amount_tendered: string
  items: Array<{
    product_id: number
    quantity: number
    unit_price: string
    tax_rate: string
    tax_inclusive: boolean
  }>
  notes: string
}

export type PendingCashSale = {
  idempotency_key: string
  sale_total_minor: number
  request: CashSaleRequest
}

type StoredPendingCashSale = {
  userId: number
  sale: unknown
}

const STORE_NAME = 'pending_sales'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value > 0
}

function isCashSaleRequest(value: unknown): value is CashSaleRequest {
  if (!isRecord(value) || !Array.isArray(value.items) || value.items.length === 0) return false
  return (
    isPositiveInteger(value.till_id)
    && isPositiveInteger(value.till_session_id)
    && value.payment_method === 'CASH'
    && typeof value.expected_total === 'string'
    && /^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(value.expected_total)
    && typeof value.amount_tendered === 'string'
    && /^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(value.amount_tendered)
    && typeof value.notes === 'string'
    && value.items.every((item) =>
      isRecord(item)
      && isPositiveInteger(item.product_id)
      && isPositiveInteger(item.quantity)
      && typeof item.unit_price === 'string'
      && /^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(item.unit_price)
      && typeof item.tax_rate === 'string'
      && /^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(item.tax_rate)
      && typeof item.tax_inclusive === 'boolean',
    )
  )
}

function isPendingCashSale(value: unknown): value is PendingCashSale {
  return (
    isRecord(value)
    && typeof value.idempotency_key === 'string'
    && value.idempotency_key.length >= 8
    && value.idempotency_key.length <= 90
    && Number.isSafeInteger(value.sale_total_minor)
    && Number(value.sale_total_minor) >= 0
    && isCashSaleRequest(value.request)
  )
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('Pending sale database request failed'))
  })
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve()
    transaction.onabort = () => reject(transaction.error ?? new Error('Pending sale database transaction aborted'))
    transaction.onerror = () => reject(transaction.error ?? new Error('Pending sale database transaction failed'))
  })
}

export class PendingCashSaleStore {
  private readonly databaseName: string
  private readonly factory: IDBFactory
  private databasePromise: Promise<IDBDatabase> | null = null

  constructor(databaseName = 'tenga-pending-cash-sales-v1', factory: IDBFactory = globalThis.indexedDB) {
    if (!factory) throw new Error('IndexedDB is required to safely persist cash sales')
    this.databaseName = databaseName
    this.factory = factory
  }

  private open(): Promise<IDBDatabase> {
    if (!this.databasePromise) {
      this.databasePromise = new Promise((resolve, reject) => {
        const request = this.factory.open(this.databaseName, 1)
        request.onupgradeneeded = () => {
          if (!request.result.objectStoreNames.contains(STORE_NAME)) {
            request.result.createObjectStore(STORE_NAME, { keyPath: 'userId' })
          }
        }
        request.onsuccess = () => {
          const database = request.result
          database.onversionchange = () => {
            database.close()
            this.databasePromise = null
          }
          resolve(database)
        }
        request.onerror = () => {
          this.databasePromise = null
          reject(request.error ?? new Error('Unable to open pending sale database'))
        }
        request.onblocked = () => {
          this.databasePromise = null
          reject(new Error('Pending sale database upgrade is blocked'))
        }
      })
    }
    return this.databasePromise
  }

  async load(userId: number): Promise<PendingCashSale | null> {
    const database = await this.open()
    const transaction = database.transaction(STORE_NAME, 'readonly')
    const stored = await requestResult(
      transaction.objectStore(STORE_NAME).get(userId),
    ) as StoredPendingCashSale | undefined
    await transactionDone(transaction)
    if (!stored) return null
    if (stored.userId !== userId || !isPendingCashSale(stored.sale)) {
      throw new Error('A pending sale record is invalid. Do not start another sale; contact a manager.')
    }
    return stored.sale
  }

  async save(userId: number, sale: PendingCashSale): Promise<void> {
    if (!isPositiveInteger(userId) || !isPendingCashSale(sale)) {
      throw new TypeError('Pending cash sale data does not meet the API contract')
    }
    const database = await this.open()
    const transaction = database.transaction(STORE_NAME, 'readwrite')
    transaction.objectStore(STORE_NAME).add({ userId, sale } satisfies StoredPendingCashSale)
    try {
      await transactionDone(transaction)
    } catch (error) {
      if (transaction.error?.name === 'ConstraintError') {
        throw new Error('An unresolved sale already exists for this user.')
      }
      throw error
    }
  }

  async clear(userId: number): Promise<void> {
    const database = await this.open()
    const transaction = database.transaction(STORE_NAME, 'readwrite')
    transaction.objectStore(STORE_NAME).delete(userId)
    await transactionDone(transaction)
  }

  async has(userId: number): Promise<boolean> {
    const database = await this.open()
    const transaction = database.transaction(STORE_NAME, 'readonly')
    const stored = await requestResult(transaction.objectStore(STORE_NAME).get(userId))
    await transactionDone(transaction)
    return stored !== undefined
  }

  async close(): Promise<void> {
    if (!this.databasePromise) return
    const database = await this.databasePromise
    database.close()
    this.databasePromise = null
  }
}

export const pendingCashSales = new PendingCashSaleStore()
