import { submitOfflineSyncBatch } from './syncTransport'
import { syncQueuedOperations, type SyncResult } from './syncService'
import { IndexedDbOfflineOperationQueue } from './operationQueue'

let queue: IndexedDbOfflineOperationQueue | null = null
const syncsInFlight = new Map<number, Promise<SyncResult>>()

export function getOfflineOperationQueue(): IndexedDbOfflineOperationQueue {
  if (!queue) queue = new IndexedDbOfflineOperationQueue()
  return queue
}

export function notifyOfflineQueueUpdated(): void {
  window.dispatchEvent(new Event('tenga-offline-queue-updated'))
}

export function syncOrganizationOperations(organizationId: number): Promise<SyncResult> {
  const active = syncsInFlight.get(organizationId)
  if (active) return active
  if (typeof navigator !== 'undefined' && !navigator.onLine) {
    return Promise.resolve({
      attempted: 0,
      synced: 0,
      retryable: 0,
      terminal: 0,
      reconciliationRequired: 0,
    })
  }
  const sync = syncQueuedOperations(
    getOfflineOperationQueue(),
    organizationId,
    submitOfflineSyncBatch,
  ).finally(() => {
    syncsInFlight.delete(organizationId)
    notifyOfflineQueueUpdated()
  })
  syncsInFlight.set(organizationId, sync)
  return sync
}
