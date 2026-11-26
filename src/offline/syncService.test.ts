import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { IndexedDbOfflineOperationQueue } from './operationQueue'
import { syncQueuedOperations, type OfflineSyncRequest } from './syncService'

describe('syncQueuedOperations', () => {
  it('sends stable operation identities and persists per-event reconciliation acknowledgments', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`sync-ack-${crypto.randomUUID()}`)
    await queue.enqueue({
      organizationId: 12,
      operationId: 'offline-count-7',
      operationType: 'INVENTORY_COUNT',
      payload: {
        location_id: 3,
        lines: [{ product_id: 9, observed_quantity: 4 }],
      },
    })
    let sent: OfflineSyncRequest | undefined

    const result = await syncQueuedOperations(queue, 12, async (request) => {
      sent = request
      return {
        device_id: request.device_id,
        organization_id: request.organization_id,
        acknowledgements: [
          {
            operation_id: 'offline-count-7',
            status: 'RECONCILIATION_REQUIRED',
            applied_entity_type: 'inventory_count',
            applied_entity_id: '31',
            error_code: 'MANUAL_RECONCILIATION_REQUIRED',
            error_message: 'Review count before reconciling',
          },
        ],
      }
    })

    expect(sent?.organization_id).toBe(12)
    expect(sent?.operations[0]).toMatchObject({
      operation_id: 'offline-count-7',
      operation_type: 'INVENTORY_COUNT',
    })
    expect(result).toMatchObject({ attempted: 1, reconciliationRequired: 1 })
    expect(await queue.listSyncable(12)).toHaveLength(0)
    expect((await queue.get(12, 'offline-count-7'))).toMatchObject({
      status: 'RECONCILIATION_REQUIRED',
      acknowledgement: { appliedEntityId: '31' },
    })
    await queue.close()
  })

  it('keeps network failures retryable with the same identity after restart', async () => {
    const name = `sync-retry-${crypto.randomUUID()}`
    const first = new IndexedDbOfflineOperationQueue(name)
    const queued = await first.enqueue({
      organizationId: 8,
      operationId: 'stable-receipt',
      operationType: 'INVENTORY_RECEIPT',
      payload: { product_id: 5, location_id: 2, quantity: 3 },
    })
    const failed = await syncQueuedOperations(first, 8, async () => {
      throw new Error('offline')
    })
    expect(failed.retryable).toBe(1)
    await first.close()

    const reopened = new IndexedDbOfflineOperationQueue(name)
    let retryRequest: OfflineSyncRequest | undefined
    const succeeded = await syncQueuedOperations(reopened, 8, async (request) => {
      retryRequest = request
      return {
        device_id: request.device_id,
        organization_id: request.organization_id,
        acknowledgements: [{ operation_id: 'stable-receipt', status: 'APPLIED' }],
      }
    })

    expect(retryRequest?.device_id).toBe(queued.deviceId)
    expect(retryRequest?.operations[0].operation_id).toBe('stable-receipt')
    expect(succeeded.synced).toBe(1)
    expect((await reopened.get(8, 'stable-receipt'))?.status).toBe('SYNCED')
    await reopened.close()
  })

  it('treats a missing acknowledgment as retryable and does not drop the operation', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`sync-missing-${crypto.randomUUID()}`)
    await queue.enqueue({
      organizationId: 5,
      operationId: 'missing-ack',
      operationType: 'INVENTORY_ADJUSTMENT',
      payload: { product_id: 4, location_id: 2, quantity: -1, reason: 'DAMAGE' },
    })

    const result = await syncQueuedOperations(queue, 5, async (request) => ({
      device_id: request.device_id,
      organization_id: request.organization_id,
      acknowledgements: [],
    }))

    expect(result.retryable).toBe(1)
    expect(await queue.list(5)).toHaveLength(1)
    expect((await queue.get(5, 'missing-ack'))?.status).toBe('RETRYABLE_FAILURE')
    await queue.close()
  })
})
