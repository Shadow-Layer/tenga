import React, { useState, useEffect } from 'react'

export type FiscalStatus = 'pending' | 'submitted' | 'assigned' | 'failed' | 'revoked'

interface FiscalInfo {
  status: FiscalStatus
  fiscalNumber?: string
  timestamp?: Date
  errorMessage?: string
  retryCount?: number
}

interface CheckoutFiscalIntegrationProps {
  saleId?: number
  onFiscalAssigned?: (fiscalNumber: string) => void
  onFiscalFailed?: (error: string) => void
}

export default function CheckoutFiscalIntegration({
  saleId,
  onFiscalAssigned,
  onFiscalFailed,
}: CheckoutFiscalIntegrationProps) {
  const [fiscal, setFiscal] = useState<FiscalInfo>({ status: 'pending' })
  const [showDetails, setShowDetails] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)

  // Simulate fiscal assignment (in real system, would call ZIMRA API)
  useEffect(() => {
    if (!saleId) return

    // Start submission process
    setFiscal({ status: 'submitted' })

    // Simulate processing delay
    const timer = setTimeout(() => {
      // 90% success rate for demo
      if (Math.random() > 0.1) {
        const fiscalNumber = `ZM${Date.now().toString().slice(-8)}`
        setFiscal({
          status: 'assigned',
          fiscalNumber,
          timestamp: new Date(),
        })

        if (onFiscalAssigned) {
          onFiscalAssigned(fiscalNumber)
        }
      } else {
        setFiscal({
          status: 'failed',
          errorMessage: 'ZIMRA service temporarily unavailable',
          retryCount: 0,
        })

        if (onFiscalFailed) {
          onFiscalFailed('Failed to get fiscal number')
        }
      }
    }, 2000)

    return () => clearTimeout(timer)
  }, [saleId, onFiscalAssigned, onFiscalFailed])

  const handleRetry = async () => {
    setIsRetrying(true)
    setFiscal({ status: 'submitted', retryCount: (fiscal.retryCount || 0) + 1 })

    // Simulate retry
    setTimeout(() => {
      const fiscalNumber = `ZM${Date.now().toString().slice(-8)}`
      setFiscal({
        status: 'assigned',
        fiscalNumber,
        timestamp: new Date(),
      })
      setIsRetrying(false)

      if (onFiscalAssigned) {
        onFiscalAssigned(fiscalNumber)
      }
    }, 1000)
  }

  const getStatusColor = () => {
    switch (fiscal.status) {
      case 'pending':
        return 'bg-gray-100 text-gray-800'
      case 'submitted':
        return 'bg-blue-100 text-blue-800'
      case 'assigned':
        return 'bg-green-100 text-green-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'revoked':
        return 'bg-orange-100 text-orange-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = () => {
    switch (fiscal.status) {
      case 'pending':
        return '⊙'
      case 'submitted':
        return '↻'
      case 'assigned':
        return '✓'
      case 'failed':
        return '✕'
      case 'revoked':
        return '⚠'
      default:
        return '?'
    }
  }

  const getStatusMessage = () => {
    switch (fiscal.status) {
      case 'pending':
        return 'Pending Fiscal Registration'
      case 'submitted':
        return 'Submitting to ZIMRA...'
      case 'assigned':
        return 'Fiscal Number Assigned'
      case 'failed':
        return 'Fiscal Registration Failed'
      case 'revoked':
        return 'Fiscal Number Revoked'
      default:
        return 'Unknown Status'
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Fiscal Integration (D014)</h2>

      {/* Status indicator */}
      <div
        className={`flex items-center gap-3 p-4 rounded-lg mb-4 cursor-pointer transition-all ${getStatusColor()}`}
        onClick={() => setShowDetails(!showDetails)}
      >
        <span className="text-2xl">{getStatusIcon()}</span>
        <div className="flex-1">
          <p className="font-semibold">{getStatusMessage()}</p>
          {fiscal.fiscalNumber && (
            <p className="text-sm opacity-75 font-mono">{fiscal.fiscalNumber}</p>
          )}
        </div>
        <span className="text-lg">▾</span>
      </div>

      {/* Details panel */}
      {showDetails && (
        <div className="bg-gray-50 rounded-lg p-4 mb-4 space-y-3">
          {/* Status details */}
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-1">Status</p>
            <p className="text-sm text-gray-900 capitalize">{fiscal.status}</p>
          </div>

          {/* Fiscal number */}
          {fiscal.fiscalNumber && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase mb-1">Fiscal Number</p>
              <p className="text-sm font-mono bg-white rounded px-2 py-1">
                {fiscal.fiscalNumber}
              </p>
            </div>
          )}

          {/* Timestamp */}
          {fiscal.timestamp && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase mb-1">Assigned At</p>
              <p className="text-sm text-gray-900">{fiscal.timestamp.toLocaleString()}</p>
            </div>
          )}

          {/* Error message */}
          {fiscal.errorMessage && (
            <div className="bg-red-50 border border-red-200 rounded p-3">
              <p className="text-xs font-medium text-red-800 uppercase mb-1">Error</p>
              <p className="text-sm text-red-800">{fiscal.errorMessage}</p>
            </div>
          )}

          {/* Retry count */}
          {fiscal.retryCount && fiscal.retryCount > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-500 uppercase mb-1">Retries</p>
              <p className="text-sm text-gray-900">{fiscal.retryCount}</p>
            </div>
          )}

          {/* ZIMRA status note */}
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs">
            <p className="text-blue-900 font-medium mb-1">ℹ ZIMRA Integration</p>
            <p className="text-blue-800">
              Fiscal numbers are assigned by ZIMRA (Zimbabwe Revenue Authority) for compliance.
              Retry automatically if assignment fails.
            </p>
          </div>
        </div>
      )}

      {/* Retry button */}
      {fiscal.status === 'failed' && (
        <button
          onClick={handleRetry}
          disabled={isRetrying}
          className="w-full px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm"
        >
          {isRetrying ? 'Retrying...' : 'Retry Fiscal Registration'}
        </button>
      )}

      {/* Success notification */}
      {fiscal.status === 'assigned' && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-800">
            ✓ Fiscal number successfully assigned. Sale is compliant with ZIMRA requirements.
          </p>
        </div>
      )}
    </div>
  )
}

/**
 * Utility function to format fiscal number for display/receipt
 */
export function formatFiscalNumber(fiscalNumber: string): string {
  if (!fiscalNumber) return 'Pending'

  // Format as ZIMRA fiscal number (ZM + 8 digits)
  if (fiscalNumber.startsWith('ZM')) {
    return `${fiscalNumber.slice(0, 2)}-${fiscalNumber.slice(2, 6)}-${fiscalNumber.slice(6)}`
  }

  return fiscalNumber
}

/**
 * Utility function to determine if sale can be completed based on fiscal status
 */
export function canCompleteSaleWithFiscal(status: FiscalStatus): boolean {
  return status === 'assigned' || status === 'revoked'
}

/**
 * Utility function to get ZIMRA status label for receipts
 */
export function getFiscalReceiptLabel(status: FiscalStatus, fiscalNumber?: string): string {
  switch (status) {
    case 'pending':
      return 'Fiscal # (Pending)'
    case 'submitted':
      return 'Fiscal # (Registering...)'
    case 'assigned':
      return `Fiscal # ${fiscalNumber || 'N/A'}`
    case 'failed':
      return 'Fiscal # (Failed - Will Retry)'
    case 'revoked':
      return `Fiscal # ${fiscalNumber || 'N/A'} (Revoked)`
    default:
      return 'Fiscal # (Unknown)'
  }
}
