import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import type { InventoryCount } from '../api'
import {
  reconcileInventoryCount,
  reviewInventoryCount,
  type InventoryCountQueue,
} from './inventoryCountReconciliation'
import { IndexedDbOfflineOperationQueue, type OfflineOperation } from '../offline/operationQueue'

const draftCount: InventoryCount = {
  id: 41,
  location_id: 3,
  status: 'DRAFT',
  notes: null,
  created_by_id: 8,
  reconciled_by_id: null,
  started_at: '2026-11-17T00:00:00Z',
  reconciled_at: null,
  lines: [{
    id: 51,
    product_id: 7,
    product_name: 'Tea',
    expected_quantity: 5,
    observed_quantity: 4,
    difference: -1,
    reconciled_movement_id: null,
  }],
}

const reconciledCount: InventoryCount = {
  ...draftCount,
  status: 'RECONCILED',
  reconciled_by_id: 8,
  reconciled_at: '2026-11-17T00:05:00Z',
}

async function queueCount(
  queue: IndexedDbOfflineOperationQueue,
  operationId: string,
  countId: number,
): Promise<OfflineOperation> {
  await queue.enqueue({
    organizationId: 3,
    operationId,
    operationType: 'INVENTORY_COUNT',
    payload: { location_id: 3, lines: [{ product_id: 7, observed_quantity: 4 }] },
  })
  await queue.acknowledge(3, operationId, {
    status: 'RECONCILIATION_REQUIRED',
    appliedEntityType: 'inventory_count',
    appliedEntityId: countId,
  })
  return (await queue.get(3, operationId))!
}

describe('inventory count reconciliation recovery', () => {
  it('resolves and persists a server-committed count after the reconciliation response is lost', async () => {
    const databaseName = `count-response-lost-${crypto.randomUUID()}`
    const queue = new IndexedDbOfflineOperationQueue(databaseName)
    const operation = await queueCount(queue, 'count-op', draftCount.id)
    let serverCount = draftCount
    let postAttempts = 0

    await expect(reconcileInventoryCount(
      operation,
      draftCount,
      3,
      async () => serverCount,
      async () => {
        postAttempts += 1
        serverCount = reconciledCount
        throw new Error('response lost after server commit')
      },
      queue,
    )).rejects.toThrow('response lost after server commit')

    const reviewed = await reviewInventoryCount(operation, 3, async () => serverCount, queue)
    expect(reviewed).toMatchObject({ count: { status: 'RECONCILED' }, resolved: true })
    expect(postAttempts).toBe(1)
    expect((await queue.get(3, operation.operationId))?.acknowledgement?.reconciliationResolvedAt).toBeTruthy()
    await queue.close()
  })

  it('recovers on later review when the server succeeds but local resolution fails', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`count-local-resolution-fails-${crypto.randomUUID()}`)
    const operation = await queueCount(queue, 'count-op', draftCount.id)
    let serverCount = draftCount
    let failResolution = true
    const flakyQueue: InventoryCountQueue = {
      markReconciliationResolved: async (...args) => {
        if (failResolution) {
          failResolution = false
          throw new Error('IndexedDB write failed')
        }
        await queue.markReconciliationResolved(...args)
      },
    }

    await expect(reconcileInventoryCount(
      operation,
      draftCount,
      3,
      async () => serverCount,
      async () => {
        serverCount = reconciledCount
        return reconciledCount
      },
      flakyQueue,
    )).rejects.toThrow('IndexedDB write failed')

    expect((await queue.get(3, operation.operationId))?.acknowledgement?.reconciliationResolvedAt).toBeFalsy()
    const reviewed = await reviewInventoryCount(operation, 3, async () => serverCount, flakyQueue)
    expect(reviewed.resolved).toBe(true)
    expect((await queue.get(3, operation.operationId))?.acknowledgement?.reconciliationResolvedAt).toBeTruthy()
    await queue.close()
  })

  it('does not post again when the latest server count is already reconciled', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`count-no-repeat-post-${crypto.randomUUID()}`)
    const operation = await queueCount(queue, 'count-op', draftCount.id)
    let postAttempts = 0

    const result = await reconcileInventoryCount(
      operation,
      draftCount,
      3,
      async () => reconciledCount,
      async () => {
        postAttempts += 1
        return reconciledCount
      },
      queue,
    )

    expect(result).toMatchObject({ count: { status: 'RECONCILED' }, alreadyReconciled: true })
    expect(postAttempts).toBe(0)
    await queue.close()
  })

  it('requires a fresh review when a draft count changed after it was displayed', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`count-changed-after-review-${crypto.randomUUID()}`)
    const operation = await queueCount(queue, 'count-op', draftCount.id)
    const reviewedCount = draftCount
    const currentCount: InventoryCount = {
      ...draftCount,
      lines: draftCount.lines.map((line) => ({ ...line, observed_quantity: 3 })),
    }
    let postAttempts = 0

    const result = await reconcileInventoryCount(
      operation,
      reviewedCount,
      3,
      async () => currentCount,
      async () => {
        postAttempts += 1
        return reconciledCount
      },
      queue,
    )

    expect(result).toMatchObject({ count: currentCount, reviewChanged: true })
    expect(postAttempts).toBe(0)
    await queue.close()
  })

  it('resolves only the operation linked to the fetched count ID', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`count-only-matching-op-${crypto.randomUUID()}`)
    const matching = await queueCount(queue, 'matching-op', draftCount.id)
    const unrelated = await queueCount(queue, 'unrelated-op', draftCount.id + 1)

    await reviewInventoryCount(matching, 3, async () => reconciledCount, queue)

    expect((await queue.get(3, matching.operationId))?.acknowledgement?.reconciliationResolvedAt).toBeTruthy()
    expect((await queue.get(3, unrelated.operationId))?.acknowledgement?.reconciliationResolvedAt).toBeFalsy()
    await queue.close()
  })

  it('keeps the resolved queue state after closing and reopening IndexedDB', async () => {
    const databaseName = `count-resolution-restart-${crypto.randomUUID()}`
    const first = new IndexedDbOfflineOperationQueue(databaseName)
    const operation = await queueCount(first, 'count-op', draftCount.id)
    await reviewInventoryCount(operation, 3, async () => reconciledCount, first)
    await first.close()

    const reopened = new IndexedDbOfflineOperationQueue(databaseName)
    expect(await reopened.get(3, operation.operationId)).toMatchObject({
      status: 'RECONCILIATION_REQUIRED',
      acknowledgement: {
        appliedEntityType: 'inventory_count',
        appliedEntityId: draftCount.id,
        reconciliationResolvedAt: expect.any(String),
      },
    })
    await reopened.close()
  })

  it('allows repeated review of the same reconciled count without changing its resolution', async () => {
    const queue = new IndexedDbOfflineOperationQueue(`count-repeat-review-${crypto.randomUUID()}`)
    const operation = await queueCount(queue, 'count-op', draftCount.id)
    const getCount = async () => reconciledCount

    expect((await reviewInventoryCount(operation, 3, getCount, queue)).resolved).toBe(true)
    const firstResolution = (await queue.get(3, operation.operationId))?.acknowledgement?.reconciliationResolvedAt
    expect((await reviewInventoryCount(operation, 3, getCount, queue)).resolved).toBe(true)
    expect((await queue.get(3, operation.operationId))?.acknowledgement?.reconciliationResolvedAt).toBe(firstResolution)
    await queue.close()
  })
})
