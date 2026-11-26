import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { IndexedDbOfflineOperationQueue } from './operationQueue'

describe('IndexedDbOfflineOperationQueue', () => {
  it('persists device and operations across queue instances', async () => {
    const name = `offline-restart-${crypto.randomUUID()}`
    const first = new IndexedDbOfflineOperationQueue(name)
    const queued = await first.enqueue({
      organizationId: 7,
      operationId: 'receipt-1',
      operationType: 'INVENTORY_RECEIPT',
      payload: { product_id: 3, location_id: 2, quantity: 5 },
    })
    await first.close()

    const reopened = new IndexedDbOfflineOperationQueue(name)
    const [persisted] = await reopened.list(7)
    expect(await reopened.getDeviceId()).toBe(queued.deviceId)
    expect(persisted).toMatchObject({
      operationId: 'receipt-1',
      organizationId: 7,
      deviceId: queued.deviceId,
      status: 'PENDING',
      attemptCount: 0,
      payload: { product_id: 3, location_id: 2, quantity: 5 },
    })
    await reopened.close()
  })

  it('keeps operations tenant-scoped and prevents identity reuse with changed payload', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`offline-tenant-${crypto.randomUUID()}`)
    await queue.enqueue({
      organizationId: 1,
      operationId: 'same-local-id',
      operationType: 'INVENTORY_ADJUSTMENT',
      payload: { product_id: 3, quantity: 1, reason: 'ADJUSTMENT' },
    })
    await queue.enqueue({
      organizationId: 2,
      operationId: 'same-local-id',
      operationType: 'INVENTORY_ADJUSTMENT',
      payload: { product_id: 3, quantity: 1, reason: 'ADJUSTMENT' },
    })

    expect(await queue.list(1)).toHaveLength(1)
    expect(await queue.list(2)).toHaveLength(1)
    await expect(
      queue.enqueue({
        organizationId: 1,
        operationId: 'same-local-id',
        operationType: 'INVENTORY_ADJUSTMENT',
        payload: { product_id: 3, quantity: 2, reason: 'ADJUSTMENT' },
      }),
    ).rejects.toThrow('already in use')
    await queue.close()
  })

  it('retains explicit acknowledgment states and only retries pending or retryable events', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`offline-acks-${crypto.randomUUID()}`)
    await queue.enqueue({
      organizationId: 4,
      operationId: 'pending',
      operationType: 'INVENTORY_ISSUE',
      payload: { product_id: 3, location_id: 2, quantity: 1, reason: 'DAMAGE' },
    })
    await queue.enqueue({
      organizationId: 4,
      operationId: 'terminal',
      operationType: 'INVENTORY_RETURN',
      payload: { sale_id: 9 },
    })
    await queue.acknowledge(4, 'pending', {
      status: 'RETRYABLE_FAILURE',
      errorCode: 'NETWORK',
      errorMessage: 'Try again',
    })
    await queue.acknowledge(4, 'terminal', {
      status: 'TERMINAL_FAILURE',
      errorCode: 'UNSUPPORTED_OPERATION',
      errorMessage: 'Return processing is unavailable',
    })

    expect((await queue.get(4, 'pending'))?.status).toBe('RETRYABLE_FAILURE')
    expect((await queue.get(4, 'terminal'))?.status).toBe('TERMINAL_FAILURE')
    expect(await queue.listSyncable(4)).toHaveLength(1)

    await queue.acknowledge(4, 'pending', { status: 'APPLIED', appliedEntityId: 19 })
    expect((await queue.get(4, 'pending'))?.status).toBe('SYNCED')
    expect(await queue.listSyncable(4)).toHaveLength(0)
    await queue.close()
  })
})
