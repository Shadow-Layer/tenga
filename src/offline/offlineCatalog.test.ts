import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { IndexedDbOfflineOperationQueue } from './operationQueue'

describe('offline catalog and count reconciliation state', () => {
  it('upgrades the existing queue database without discarding durable operations', async () => {
    const databaseName = `offline-upgrade-${crypto.randomUUID()}`
    const legacy = await new Promise<IDBDatabase>((resolve, reject) => {
      const request = indexedDB.open(databaseName, 1)
      request.onupgradeneeded = () => {
        const database = request.result
        database.createObjectStore('metadata', { keyPath: 'key' })
        const operations = database.createObjectStore('operations', {
          keyPath: ['organizationId', 'operationId'],
        })
        operations.createIndex('by_organization_sequence', ['organizationId', 'sequence'])
      }
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
    await new Promise<void>((resolve, reject) => {
      const transaction = legacy.transaction(['metadata', 'operations'], 'readwrite')
      transaction.objectStore('metadata').put({ key: 'device_id', value: 'legacy-device' })
      transaction.objectStore('operations').put({
        operationId: 'legacy-receipt',
        organizationId: 6,
        deviceId: 'legacy-device',
        operationType: 'INVENTORY_RECEIPT',
        payload: { product_id: 3, location_id: 2, quantity: 1 },
        sequence: 1,
        createdAt: 1,
        status: 'PENDING',
        attemptCount: 0,
        lastError: null,
        acknowledgement: null,
      })
      transaction.oncomplete = () => resolve()
      transaction.onerror = () => reject(transaction.error)
    })
    legacy.close()

    const upgraded = new IndexedDbOfflineOperationQueue(databaseName)
    expect(await upgraded.list(6)).toMatchObject([
      { operationId: 'legacy-receipt', status: 'PENDING', deviceId: 'legacy-device' },
    ])
    expect(await upgraded.getDeviceId()).toBe('legacy-device')
    await upgraded.close()
  })

  it('keeps catalog choices tenant-scoped and persists count resolution with queue history', async () => {
    const databaseName = `offline-catalog-${crypto.randomUUID()}`
    const queue = new IndexedDbOfflineOperationQueue(databaseName)
    await queue.saveCatalog({
      organizationId: 3,
      cachedAt: 123,
      products: [{ id: 7, name: 'Tea', sku: 'TEA-7', unit_of_measure: 'box' }],
      locations: [{ id: 2, name: 'Main', code: 'MAIN' }],
    })
    expect(await queue.getCatalog(3)).toMatchObject({
      products: [{ id: 7, sku: 'TEA-7' }],
      locations: [{ id: 2, code: 'MAIN' }],
    })
    expect(await queue.getCatalog(4)).toBeUndefined()

    await queue.savePosCatalog({
      organizationId: 3,
      cachedAt: 456,
      products: [{
        id: 7,
        name: 'Tea',
        sku: 'TEA-7',
        barcode: '1234567890',
        price: '2.50',
        tax_rule_id: 8,
      }],
      taxRules: [{ id: 8, rate: '15', tax_inclusive: true }],
    })
    expect(await queue.getPosCatalog(3)).toMatchObject({
      products: [{ id: 7, barcode: '1234567890', price: '2.50', tax_rule_id: 8 }],
      taxRules: [{ id: 8, rate: '15', tax_inclusive: true }],
    })
    expect(await queue.getPosCatalog(4)).toBeUndefined()

    await queue.saveOpenTillSession({
      userId: 11,
      organizationId: 3,
      sessionId: 15,
      till: { id: 4, name: 'Front', code: 'FRONT', location_id: 2, is_active: true },
      cachedAt: 789,
    })
    expect(await queue.getOpenTillSession(3, 11)).toMatchObject({
      sessionId: 15,
      till: { id: 4, name: 'Front' },
    })
    expect(await queue.getOpenTillSession(4, 11)).toBeUndefined()
    await queue.clearOpenTillSession(3, 11)
    expect(await queue.getOpenTillSession(3, 11)).toBeUndefined()

    await queue.enqueue({
      organizationId: 3,
      operationId: 'offline-count',
      operationType: 'INVENTORY_COUNT',
      payload: { location_id: 2, lines: [{ product_id: 7, observed_quantity: 4 }] },
    })
    await queue.acknowledge(3, 'offline-count', {
      status: 'RECONCILIATION_REQUIRED',
      appliedEntityType: 'inventory_count',
      appliedEntityId: 9,
    })
    await queue.markReconciliationResolved(3, 'offline-count', 9)
    const persisted = await queue.get(3, 'offline-count')
    expect(persisted?.status).toBe('RECONCILIATION_REQUIRED')
    expect(persisted?.acknowledgement?.reconciliationResolvedAt).toBeTruthy()
    await queue.close()
  })
})
