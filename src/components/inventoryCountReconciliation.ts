import type { InventoryCount } from '../api'
import type { OfflineOperation } from '../offline/operationQueue'

export interface InventoryCountQueue {
  markReconciliationResolved(
    organizationId: number,
    operationId: string,
    countId: number,
  ): Promise<void>
}

type GetInventoryCount = (countId: number) => Promise<InventoryCount>
type PostInventoryCountReconciliation = (
  countId: number,
  observations: Array<{ product_id: number; observed_quantity: number | null }>,
) => Promise<InventoryCount>

function reviewChanged(reviewedCount: InventoryCount, currentCount: InventoryCount): boolean {
  if (reviewedCount.lines.length !== currentCount.lines.length) return true
  const reviewedLines = new Map(reviewedCount.lines.map((line) => [
    line.product_id,
    [line.expected_quantity, line.observed_quantity],
  ]))
  return currentCount.lines.some((line) => {
    const reviewed = reviewedLines.get(line.product_id)
    return !reviewed
      || reviewed[0] !== line.expected_quantity
      || reviewed[1] !== line.observed_quantity
  })
}

function countIdForOperation(operation: OfflineOperation, organizationId: number): number {
  const acknowledgement = operation.acknowledgement
  const countId = Number(acknowledgement?.appliedEntityId)
  if (
    operation.organizationId !== organizationId
    || operation.operationType !== 'INVENTORY_COUNT'
    || operation.status !== 'RECONCILIATION_REQUIRED'
    || acknowledgement?.status !== 'RECONCILIATION_REQUIRED'
    || acknowledgement.appliedEntityType !== 'inventory_count'
    || !Number.isSafeInteger(countId)
    || countId <= 0
  ) {
    throw new Error('The queued operation is not linked to a valid inventory count.')
  }
  return countId
}

async function fetchMatchingCount(countId: number, getCount: GetInventoryCount): Promise<InventoryCount> {
  const count = await getCount(countId)
  if (count.id !== countId) {
    throw new Error('The server returned a different inventory count than the queued operation references.')
  }
  return count
}

export async function reviewInventoryCount(
  operation: OfflineOperation,
  organizationId: number,
  getCount: GetInventoryCount,
  queue: InventoryCountQueue,
): Promise<{ count: InventoryCount; resolved: boolean }> {
  const countId = countIdForOperation(operation, organizationId)
  const count = await fetchMatchingCount(countId, getCount)
  if (count.status !== 'RECONCILED') return { count, resolved: false }

  await queue.markReconciliationResolved(organizationId, operation.operationId, countId)
  return { count, resolved: true }
}

export async function reconcileInventoryCount(
  operation: OfflineOperation,
  reviewedCount: InventoryCount,
  organizationId: number,
  getCount: GetInventoryCount,
  postReconciliation: PostInventoryCountReconciliation,
  queue: InventoryCountQueue,
): Promise<{ count: InventoryCount; alreadyReconciled: boolean; reviewChanged: boolean }> {
  const countId = countIdForOperation(operation, organizationId)
  if (reviewedCount.id !== countId) {
    throw new Error('The displayed inventory count does not match the queued operation.')
  }
  const currentCount = await fetchMatchingCount(countId, getCount)
  if (currentCount.status === 'RECONCILED') {
    await queue.markReconciliationResolved(organizationId, operation.operationId, countId)
    return { count: currentCount, alreadyReconciled: true, reviewChanged: false }
  }
  if (currentCount.status !== 'DRAFT') {
    throw new Error(`Inventory count ${countId} cannot be reconciled from ${currentCount.status}.`)
  }
  if (reviewChanged(reviewedCount, currentCount)) {
    return { count: currentCount, alreadyReconciled: false, reviewChanged: true }
  }

  const count = await postReconciliation(countId, reviewedCount.lines.map((line) => ({
    product_id: line.product_id,
    observed_quantity: line.observed_quantity,
  })))
  if (count.id !== countId || count.status !== 'RECONCILED') {
    throw new Error(`The server did not confirm reconciliation of inventory count ${countId}.`)
  }
  await queue.markReconciliationResolved(organizationId, operation.operationId, countId)
  return { count, alreadyReconciled: false, reviewChanged: false }
}
