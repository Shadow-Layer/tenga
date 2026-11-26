export type OfflineOperationType =
  | 'SALE_COMMIT'
  | 'INVENTORY_RECEIPT'
  | 'INVENTORY_ISSUE'
  | 'INVENTORY_ADJUSTMENT'
  | 'INVENTORY_TRANSFER'
  | 'INVENTORY_COUNT'
  | 'INVENTORY_RETURN'

export type OfflineOperationStatus =
  | 'PENDING'
  | 'RETRYABLE_FAILURE'
  | 'SYNCED'
  | 'TERMINAL_FAILURE'
  | 'RECONCILIATION_REQUIRED'

export type ServerAcknowledgementStatus =
  | 'APPLIED'
  | 'RETRYABLE_FAILURE'
  | 'TERMINAL_FAILURE'
  | 'RECONCILIATION_REQUIRED'

export interface OfflineOperation<Payload = Record<string, unknown>> {
  operationId: string
  organizationId: number
  deviceId: string
  operationType: OfflineOperationType
  payload: Payload
  sequence: number
  createdAt: number
  status: OfflineOperationStatus
  attemptCount: number
  lastError: string | null
  acknowledgement: OperationAcknowledgement | null
}

export interface OperationAcknowledgement {
  status: ServerAcknowledgementStatus
  appliedEntityType?: string | null
  appliedEntityId?: string | number | null
  errorCode?: string | null
  errorMessage?: string | null
  reconciliationResolvedAt?: string | null
  [key: string]: unknown
}

export interface OfflineCatalog {
  organizationId: number
  cachedAt: number
  products: Array<{ id: number; name: string; sku: string; unit_of_measure: string }>
  locations: Array<{ id: number; name: string; code: string }>
}

export interface OfflinePosCatalog {
  organizationId: number
  cachedAt: number
  products: Array<{
    id: number
    name: string
    sku: string
    barcode: string | null
    price: string
    tax_rule_id: number | null
  }>
  taxRules: Array<{
    id: number
    rate: string
    tax_inclusive: boolean
  }>
}

export interface CachedOpenTillSession {
  userId: number
  organizationId: number
  sessionId: number
  till: { id: number; name: string; code: string; location_id: number; is_active: boolean }
  cachedAt: number
}

export interface QueueOperationInput<Payload = Record<string, unknown>> {
  organizationId: number
  operationType: OfflineOperationType
  payload: Payload
  operationId?: string
}

interface QueueMetadata {
  key: string
  value: string
}

const DATABASE_VERSION = 2
const METADATA_STORE = 'metadata'
const OPERATIONS_STORE = 'operations'
const CATALOG_STORE = 'catalog'
const DEVICE_ID_KEY = 'device_id'
const nextSequenceKey = (organizationId: number) => `next_operation_sequence:${organizationId}`
const posCatalogKey = (organizationId: number) => `pos_catalog:${organizationId}`
const openTillSessionKey = (organizationId: number, userId: number) =>
  `open_till_session:${organizationId}:${userId}`

function createId(): string {
  if (!globalThis.crypto?.randomUUID) {
    throw new Error('Secure UUID generation is not available in this browser')
  }
  return globalThis.crypto.randomUUID()
}

function clonePayload(payload: unknown): unknown {
  const encoded = JSON.stringify(payload)
  if (encoded === undefined) {
    throw new TypeError('Offline operation payload must be JSON serializable')
  }
  return JSON.parse(encoded)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function parseMetadataValue<T>(stored: QueueMetadata | undefined, label: string): T | undefined {
  if (!stored) return undefined
  try {
    return JSON.parse(stored.value) as T
  } catch {
    throw new Error(`Saved ${label} data is invalid and requires administrator review.`)
  }
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB request failed'))
  })
}

function transactionDone(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve()
    transaction.onabort = () => reject(transaction.error ?? new Error('IndexedDB transaction aborted'))
    transaction.onerror = () => reject(transaction.error ?? new Error('IndexedDB transaction failed'))
  })
}

export class IndexedDbOfflineOperationQueue {
  private readonly databaseName: string
  private readonly factory: IDBFactory
  private databasePromise: Promise<IDBDatabase> | null = null

  constructor(
    databaseName = 'tenga-offline-operations',
    factory: IDBFactory = globalThis.indexedDB,
  ) {
    if (!factory) {
      throw new Error('IndexedDB is required for durable offline operations')
    }
    this.databaseName = databaseName
    this.factory = factory
  }

  private open(): Promise<IDBDatabase> {
    if (!this.databasePromise) {
      this.databasePromise = new Promise((resolve, reject) => {
        const request = this.factory.open(this.databaseName, DATABASE_VERSION)
        request.onupgradeneeded = () => {
          const database = request.result
          if (!database.objectStoreNames.contains(METADATA_STORE)) {
            database.createObjectStore(METADATA_STORE, { keyPath: 'key' })
          }
          if (!database.objectStoreNames.contains(OPERATIONS_STORE)) {
            const operations = database.createObjectStore(OPERATIONS_STORE, {
              keyPath: ['organizationId', 'operationId'],
            })
            operations.createIndex('by_organization_sequence', ['organizationId', 'sequence'])
          }
          if (!database.objectStoreNames.contains(CATALOG_STORE)) {
            database.createObjectStore(CATALOG_STORE, { keyPath: 'organizationId' })
          }
        }
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error ?? new Error('Unable to open offline queue'))
        request.onblocked = () => reject(new Error('Offline queue database upgrade is blocked'))
      })
    }
    return this.databasePromise
  }

  async close(): Promise<void> {
    if (!this.databasePromise) return
    const database = await this.databasePromise
    database.close()
    this.databasePromise = null
  }

  async getDeviceId(): Promise<string> {
    const database = await this.open()
    const transaction = database.transaction(METADATA_STORE, 'readwrite')
    const store = transaction.objectStore(METADATA_STORE)
    const existing = (await requestResult(store.get(DEVICE_ID_KEY))) as QueueMetadata | undefined
    const deviceId = existing?.value ?? createId()
    if (!existing) {
      store.add({ key: DEVICE_ID_KEY, value: deviceId } satisfies QueueMetadata)
    }
    await transactionDone(transaction)
    return deviceId
  }

  async enqueue<Payload = Record<string, unknown>>(
    input: QueueOperationInput<Payload>,
  ): Promise<OfflineOperation<Payload>> {
    if (!Number.isSafeInteger(input.organizationId) || input.organizationId <= 0) {
      throw new TypeError('organizationId must be a positive integer')
    }
    const payload = clonePayload(input.payload) as Payload
    const database = await this.open()
    const transaction = database.transaction([METADATA_STORE, OPERATIONS_STORE], 'readwrite')
    const metadata = transaction.objectStore(METADATA_STORE)
    const operations = transaction.objectStore(OPERATIONS_STORE)
    const storedDevice = (await requestResult(
      metadata.get(DEVICE_ID_KEY),
    )) as QueueMetadata | undefined
    const sequenceKey = nextSequenceKey(input.organizationId)
    const storedSequence = (await requestResult(
      metadata.get(sequenceKey),
    )) as QueueMetadata | undefined
    const deviceId = storedDevice?.value ?? createId()
    const sequence = Number(storedSequence?.value ?? 0) + 1
    if (!storedDevice) {
      metadata.add({ key: DEVICE_ID_KEY, value: deviceId } satisfies QueueMetadata)
    }
    metadata.put({ key: sequenceKey, value: String(sequence) } satisfies QueueMetadata)

    const operation: OfflineOperation<Payload> = {
      operationId: input.operationId ?? createId(),
      organizationId: input.organizationId,
      deviceId,
      operationType: input.operationType,
      payload,
      sequence,
      createdAt: Date.now(),
      status: 'PENDING',
      attemptCount: 0,
      lastError: null,
      acknowledgement: null,
    }
    try {
      operations.add(operation)
      await transactionDone(transaction)
      return operation
    } catch (error) {
      if (transaction.error?.name !== 'ConstraintError') throw error
      const existing = await this.get(operation.organizationId, operation.operationId)
      if (
        existing &&
        existing.organizationId === operation.organizationId &&
        existing.operationType === operation.operationType &&
        JSON.stringify(existing.payload) === JSON.stringify(operation.payload)
      ) {
        return existing as OfflineOperation<Payload>
      }
      throw new Error(`Offline operation identity ${operation.operationId} is already in use`)
    }
  }

  async get(organizationId: number, operationId: string): Promise<OfflineOperation | undefined> {
    const database = await this.open()
    const transaction = database.transaction(OPERATIONS_STORE, 'readonly')
    const result = await requestResult(
      transaction.objectStore(OPERATIONS_STORE).get([organizationId, operationId]),
    ) as OfflineOperation | undefined
    await transactionDone(transaction)
    return result
  }

  async list(organizationId: number): Promise<OfflineOperation[]> {
    const database = await this.open()
    const transaction = database.transaction(OPERATIONS_STORE, 'readonly')
    const operations = await requestResult(
      transaction.objectStore(OPERATIONS_STORE)
        .index('by_organization_sequence')
        .getAll(IDBKeyRange.bound([organizationId, 0], [organizationId, Number.MAX_SAFE_INTEGER])),
    ) as OfflineOperation[]
    await transactionDone(transaction)
    return operations
  }

  async saveCatalog(catalog: OfflineCatalog): Promise<void> {
    if (!Number.isSafeInteger(catalog.organizationId) || catalog.organizationId <= 0) {
      throw new TypeError('organizationId must be a positive integer')
    }
    const database = await this.open()
    const transaction = database.transaction(CATALOG_STORE, 'readwrite')
    transaction.objectStore(CATALOG_STORE).put(catalog)
    await transactionDone(transaction)
  }

  async getCatalog(organizationId: number): Promise<OfflineCatalog | undefined> {
    const database = await this.open()
    const transaction = database.transaction(CATALOG_STORE, 'readonly')
    const result = await requestResult(
      transaction.objectStore(CATALOG_STORE).get(organizationId),
    ) as OfflineCatalog | undefined
    await transactionDone(transaction)
    return result
  }

  async savePosCatalog(catalog: OfflinePosCatalog): Promise<void> {
    if (!Number.isSafeInteger(catalog.organizationId) || catalog.organizationId <= 0) {
      throw new TypeError('organizationId must be a positive integer')
    }
    const database = await this.open()
    const transaction = database.transaction(METADATA_STORE, 'readwrite')
    transaction.objectStore(METADATA_STORE).put({
      key: posCatalogKey(catalog.organizationId),
      value: JSON.stringify(catalog),
    } satisfies QueueMetadata)
    await transactionDone(transaction)
  }

  async getPosCatalog(organizationId: number): Promise<OfflinePosCatalog | undefined> {
    const database = await this.open()
    const transaction = database.transaction(METADATA_STORE, 'readonly')
    const stored = await requestResult(
      transaction.objectStore(METADATA_STORE).get(posCatalogKey(organizationId)),
    ) as QueueMetadata | undefined
    await transactionDone(transaction)
    const result = parseMetadataValue<OfflinePosCatalog>(stored, 'offline checkout catalog')
    if (!result) return undefined
    if (
      result.organizationId !== organizationId
      || !Number.isSafeInteger(result.cachedAt)
      || !Array.isArray(result.products)
      || !result.products.every((product) =>
        isRecord(product)
        && typeof product.id === 'number'
        && Number.isSafeInteger(product.id)
        && typeof product.name === 'string'
        && typeof product.sku === 'string'
        && (product.barcode === null || typeof product.barcode === 'string')
        && typeof product.price === 'string'
        && /^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(product.price)
        && (product.tax_rule_id === null || (
          typeof product.tax_rule_id === 'number'
          && Number.isSafeInteger(product.tax_rule_id)
          && product.tax_rule_id > 0
        )),
      )
      || !Array.isArray(result.taxRules)
      || !result.taxRules.every((rule) =>
        isRecord(rule)
        && typeof rule.id === 'number'
        && Number.isSafeInteger(rule.id)
        && typeof rule.rate === 'string'
        && /^(0|[1-9]\d*)(?:\.\d{1,2})?$/.test(rule.rate)
        && typeof rule.tax_inclusive === 'boolean',
      )
    ) {
      throw new Error('Saved offline checkout catalog does not match this organization.')
    }
    return result
  }

  async saveOpenTillSession(session: CachedOpenTillSession): Promise<void> {
    if (
      !Number.isSafeInteger(session.userId) || session.userId <= 0
      || !Number.isSafeInteger(session.organizationId) || session.organizationId <= 0
      || !Number.isSafeInteger(session.sessionId) || session.sessionId <= 0
      || !Number.isSafeInteger(session.till.id) || session.till.id <= 0
    ) {
      throw new TypeError('Cached till session does not meet the session identity contract')
    }
    const database = await this.open()
    const transaction = database.transaction(METADATA_STORE, 'readwrite')
    transaction.objectStore(METADATA_STORE).put({
      key: openTillSessionKey(session.organizationId, session.userId),
      value: JSON.stringify(session),
    } satisfies QueueMetadata)
    await transactionDone(transaction)
  }

  async getOpenTillSession(
    organizationId: number,
    userId: number,
  ): Promise<CachedOpenTillSession | undefined> {
    const database = await this.open()
    const transaction = database.transaction(METADATA_STORE, 'readonly')
    const stored = await requestResult(
      transaction.objectStore(METADATA_STORE).get(openTillSessionKey(organizationId, userId)),
    ) as QueueMetadata | undefined
    await transactionDone(transaction)
    const result = parseMetadataValue<CachedOpenTillSession>(stored, 'cached till session')
    if (!result) return undefined
    if (
      result.organizationId !== organizationId || result.userId !== userId
      || !Number.isSafeInteger(result.sessionId) || result.sessionId <= 0
      || !Number.isSafeInteger(result.till?.id) || result.till.id <= 0
      || typeof result.till.name !== 'string'
      || typeof result.till.code !== 'string'
      || !Number.isSafeInteger(result.till.location_id) || result.till.location_id <= 0
      || typeof result.till.is_active !== 'boolean'
      || !Number.isSafeInteger(result.cachedAt)
    ) {
      throw new Error('Saved till session does not match this user and organization.')
    }
    return result
  }

  async clearOpenTillSession(organizationId: number, userId: number): Promise<void> {
    const database = await this.open()
    const transaction = database.transaction(METADATA_STORE, 'readwrite')
    transaction.objectStore(METADATA_STORE).delete(openTillSessionKey(organizationId, userId))
    await transactionDone(transaction)
  }

  async listSyncable(organizationId: number, limit = 100): Promise<OfflineOperation[]> {
    return (await this.list(organizationId))
      .filter((operation) => operation.status === 'PENDING' || operation.status === 'RETRYABLE_FAILURE')
      .slice(0, Math.max(0, limit))
  }

  async acknowledge(
    organizationId: number,
    operationId: string,
    acknowledgement: OperationAcknowledgement,
  ): Promise<void> {
    const database = await this.open()
    const transaction = database.transaction(OPERATIONS_STORE, 'readwrite')
    const store = transaction.objectStore(OPERATIONS_STORE)
    const operation = await requestResult(
      store.get([organizationId, operationId]),
    ) as OfflineOperation | undefined
    if (!operation) {
      transaction.abort()
      throw new Error('Acknowledged operation is not in this organization queue')
    }

    const status = {
      APPLIED: 'SYNCED',
      RETRYABLE_FAILURE: 'RETRYABLE_FAILURE',
      TERMINAL_FAILURE: 'TERMINAL_FAILURE',
      RECONCILIATION_REQUIRED: 'RECONCILIATION_REQUIRED',
    }[acknowledgement.status] as OfflineOperationStatus | undefined
    if (!status) {
      transaction.abort()
      throw new Error('Unknown operation acknowledgment status')
    }
    if (
      operation.status === 'SYNCED' ||
      operation.status === 'TERMINAL_FAILURE' ||
      operation.status === 'RECONCILIATION_REQUIRED'
    ) {
      await transactionDone(transaction)
      return
    }
    operation.status = status
    operation.attemptCount += 1
    operation.lastError = acknowledgement.errorMessage ?? null
    operation.acknowledgement = acknowledgement
    store.put(operation)
    await transactionDone(transaction)
  }

  async markBatchRetryable(
    organizationId: number,
    operations: OfflineOperation[],
    errorMessage: string,
  ): Promise<void> {
    await Promise.all(
      operations.map((operation) =>
        this.acknowledge(organizationId, operation.operationId, {
          status: 'RETRYABLE_FAILURE',
          errorCode: 'SYNC_TRANSPORT_ERROR',
          errorMessage,
        }),
      ),
    )
  }

  async markReconciliationResolved(
    organizationId: number,
    operationId: string,
    expectedCountId: number,
  ): Promise<void> {
    const database = await this.open()
    const transaction = database.transaction(OPERATIONS_STORE, 'readwrite')
    const store = transaction.objectStore(OPERATIONS_STORE)
    const operation = await requestResult(
      store.get([organizationId, operationId]),
    ) as OfflineOperation | undefined
    const acknowledgement = operation?.acknowledgement
    if (
      !operation
      || operation.status !== 'RECONCILIATION_REQUIRED'
      || operation.operationType !== 'INVENTORY_COUNT'
      || acknowledgement?.status !== 'RECONCILIATION_REQUIRED'
      || acknowledgement.appliedEntityType !== 'inventory_count'
      || !Number.isSafeInteger(expectedCountId)
      || expectedCountId <= 0
      || Number(acknowledgement.appliedEntityId) !== expectedCountId
    ) {
      transaction.abort()
      throw new Error('Only the matching inventory count operation can be resolved')
    }
    if (acknowledgement.reconciliationResolvedAt) {
      await transactionDone(transaction)
      return
    }
    operation.acknowledgement = {
      ...acknowledgement,
      reconciliationResolvedAt: new Date().toISOString(),
    }
    store.put(operation)
    await transactionDone(transaction)
  }
}
