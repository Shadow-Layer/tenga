import React, { useEffect, useState } from 'react'
import { useAppContextStore } from '../stores'

interface OfflineStateIndicatorProps {
  isOnline: boolean
  syncStatus?: 'recorded' | 'syncing' | 'synchronized' | 'failed'
  lastSyncTime?: Date
  pendingItems?: number
}

export default function OfflineStateIndicator({
  isOnline,
  syncStatus = 'recorded',
  lastSyncTime,
  pendingItems = 0,
}: OfflineStateIndicatorProps) {
  const [showDetails, setShowDetails] = useState(false)

  const statusColor = {
    recorded: 'bg-yellow-100 text-yellow-800',
    syncing: 'bg-blue-100 text-blue-800',
    synchronized: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }

  const statusIcon = {
    recorded: '⏸',
    syncing: '↻',
    synchronized: '✓',
    failed: '✕',
  }

  const getStatusMessage = () => {
    if (!isOnline) {
      return 'Working Offline'
    }

    switch (syncStatus) {
      case 'recorded':
        return 'Pending Sync'
      case 'syncing':
        return 'Syncing...'
      case 'synchronized':
        return 'Synchronized'
      case 'failed':
        return 'Sync Failed'
      default:
        return 'Unknown'
    }
  }

  return (
    <div className="relative">
      {/* Main status indicator */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium cursor-pointer transition-all ${
          isOnline
            ? statusColor[syncStatus]
            : 'bg-orange-100 text-orange-800'
        }`}
      >
        <span className="text-lg">{statusIcon[syncStatus]}</span>
        <span>{getStatusMessage()}</span>
        {pendingItems > 0 && (
          <span className="ml-1 bg-white/30 px-2 py-0.5 rounded text-xs font-bold">
            {pendingItems}
          </span>
        )}
      </button>

      {/* Details panel */}
      {showDetails && (
        <div className="absolute right-0 top-12 mt-2 w-72 bg-white border rounded-lg shadow-lg z-50 p-4">
          <div className="space-y-3">
            {/* Network status */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Network Status</p>
              <p className="text-sm text-gray-900 mt-1">
                {isOnline ? '🟢 Online' : '🔴 Offline'}
              </p>
            </div>

            {/* Sync status */}
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase">Sync Status</p>
              <p className="text-sm text-gray-900 mt-1 capitalize">
                {syncStatus === 'synchronized' ? '✓ All synced' : getStatusMessage()}
              </p>
            </div>

            {/* Pending items */}
            {pendingItems > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase">Pending</p>
                <p className="text-sm text-gray-900 mt-1">{pendingItems} items waiting to sync</p>
              </div>
            )}

            {/* Last sync time */}
            {lastSyncTime && (
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase">Last Sync</p>
                <p className="text-sm text-gray-900 mt-1">
                  {lastSyncTime.toLocaleTimeString()}
                </p>
              </div>
            )}

            {/* Offline message */}
            {!isOnline && (
              <div className="bg-orange-50 border border-orange-200 rounded p-3 mt-2">
                <p className="text-sm text-orange-800">
                  Working offline. Sales will be synced when connection is restored.
                </p>
              </div>
            )}

            {/* Failed sync message */}
            {syncStatus === 'failed' && (
              <div className="bg-red-50 border border-red-200 rounded p-3 mt-2">
                <p className="text-sm text-red-800">
                  Sync failed. Please check your connection and try again.
                </p>
              </div>
            )}
          </div>

          <button
            onClick={() => setShowDetails(false)}
            className="mt-4 w-full text-center text-sm text-gray-600 hover:text-gray-900 py-2 border-t"
          >
            Close
          </button>
        </div>
      )}
    </div>
  )
}

/**
 * Hook to manage offline state (D010a)
 * Returns: isOnline, syncStatus, pendingItemCount
 */
export function useOfflineState() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [syncStatus, setSyncStatus] = useState<'recorded' | 'syncing' | 'synchronized' | 'failed'>('synchronized')
  const [pendingItems, setPendingItems] = useState(0)
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null)

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Trigger sync when coming back online
      setSyncStatus('syncing')
      setTimeout(() => {
        setSyncStatus('synchronized')
        setLastSyncTime(new Date())
      }, 1000)
    }

    const handleOffline = () => {
      setIsOnline(false)
      setSyncStatus('recorded')
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return {
    isOnline,
    syncStatus,
    pendingItems,
    lastSyncTime,
    addPendingItem: () => setPendingItems((p) => p + 1),
    clearPendingItems: () => setPendingItems(0),
    setSyncStatus,
  }
}
