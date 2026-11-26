import { useCallback, useEffect, useState } from 'react'
import { getOfflineOperationQueue, syncOrganizationOperations } from '../offline/runtime'
import type { OfflineOperation } from '../offline/operationQueue'

type Props = { organizationId: number; compact?: boolean }

export function OfflineSyncStatus({ organizationId, compact = false }: Props) {
  const [online, setOnline] = useState(() => navigator.onLine)
  const [operations, setOperations] = useState<OfflineOperation[]>([])
  const [syncing, setSyncing] = useState(false)
  const [message, setMessage] = useState('')

  const refresh = useCallback(async () => {
    try {
      setOperations(await getOfflineOperationQueue().list(organizationId))
    } catch {
      setMessage('Durable offline storage is unavailable. Inventory actions cannot be recorded offline.')
    }
  }, [organizationId])

  const sync = useCallback(async () => {
    if (!navigator.onLine) {
      setOnline(false)
      setMessage('Offline. Queued inventory operations are saved on this device.')
      return
    }
    setSyncing(true)
    setMessage('')
    try {
      const result = await syncOrganizationOperations(organizationId)
      await refresh()
      if (result.attempted) {
        setMessage(`Sync finished: ${result.synced} applied, ${result.retryable} retryable, ${result.terminal} terminal, ${result.reconciliationRequired} need reconciliation.`)
      } else {
        setMessage('There are no pending operations to sync.')
      }
    } catch {
      setMessage('Sync status could not be refreshed. Queued operations remain stored on this device.')
      await refresh()
    } finally {
      setSyncing(false)
    }
  }, [organizationId, refresh])

  useEffect(() => {
    void refresh()
    const handleOnline = () => {
      setOnline(true)
      void sync()
    }
    const handleOffline = () => setOnline(false)
    const handleQueueChange = () => void refresh()
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    window.addEventListener('tenga-offline-queue-updated', handleQueueChange)
    if (navigator.onLine) void sync()
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
      window.removeEventListener('tenga-offline-queue-updated', handleQueueChange)
    }
  }, [refresh, sync])

  const pending = operations.filter((operation) => operation.status === 'PENDING').length
  const retryable = operations.filter((operation) => operation.status === 'RETRYABLE_FAILURE').length
  const terminal = operations.filter((operation) => operation.status === 'TERMINAL_FAILURE').length
  const reconciliation = operations.filter((operation) =>
    operation.status === 'RECONCILIATION_REQUIRED'
    && !operation.acknowledgement?.reconciliationResolvedAt,
  ).length
  const saved = pending + retryable + terminal + reconciliation

  return (
    <div className={compact ? 'flex flex-wrap items-center gap-2 text-xs' : 'rounded-lg border border-gray-200 bg-white p-3'}>
      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-medium ${
        online ? 'bg-green-50 text-green-800' : 'bg-amber-100 text-amber-900'
      }`}>
        <span aria-hidden="true">{online ? '●' : '○'}</span>
        {online ? 'Online' : 'Offline'}
      </span>
      <span className="text-gray-700">
        {saved} saved · {pending} pending · {retryable} retryable · {terminal} terminal · {reconciliation} reconciliation
      </span>
      {(pending > 0 || retryable > 0) && (
        <button
          type="button"
          disabled={!online || syncing}
          onClick={() => void sync()}
          className="rounded border border-indigo-300 px-2.5 py-1 font-medium text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {syncing ? 'Syncing…' : 'Retry sync'}
        </button>
      )}
      {!compact && message && <p role="status" className="w-full text-sm text-gray-700">{message}</p>}
    </div>
  )
}
