import React, { useState, useEffect } from 'react'
import { usePOSStore } from '../stores'

interface SuspendedSale {
  id: string
  timestamp: Date
  itemCount: number
  total: number
  customerName?: string
  notes?: string
}

interface CheckoutSuspendResumeProps {
  currentTotal: number
  currentItemCount: number
  onSuspend?: (reason: string) => void
  onResume?: (saleId: string) => void
}

export default function CheckoutSuspendResume({
  currentTotal,
  currentItemCount,
  onSuspend,
  onResume,
}: CheckoutSuspendResumeProps) {
  const { cartItems } = usePOSStore()
  const [suspendedSales, setSuspendedSales] = useState<SuspendedSale[]>([])
  const [showSuspendModal, setShowSuspendModal] = useState(false)
  const [showResumeModal, setShowResumeModal] = useState(false)
  const [suspendReason, setSuspendReason] = useState('')
  const [suspendNotes, setSuspendNotes] = useState('')

  // Load suspended sales from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('suspendedSales')
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        // Convert timestamp strings back to Date objects
        const restored = parsed.map((sale: any) => ({
          ...sale,
          timestamp: new Date(sale.timestamp),
        }))
        setSuspendedSales(restored)
      } catch (error) {
        console.error('Failed to load suspended sales:', error)
      }
    }
  }, [])

  // Save suspended sales to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('suspendedSales', JSON.stringify(suspendedSales))
  }, [suspendedSales])

  const handleSuspendSale = () => {
    if (!suspendReason.trim()) {
      alert('Please provide a reason for suspending the sale')
      return
    }

    if (cartItems.length === 0) {
      alert('Cannot suspend an empty cart')
      return
    }

    const newSuspendedSale: SuspendedSale = {
      id: `sale-${Date.now()}`,
      timestamp: new Date(),
      itemCount: cartItems.length,
      total: currentTotal,
      notes: suspendNotes,
    }

    setSuspendedSales([...suspendedSales, newSuspendedSale])
    
    if (onSuspend) {
      onSuspend(suspendReason)
    }

    setShowSuspendModal(false)
    setSuspendReason('')
    setSuspendNotes('')
  }

  const handleResumeSale = (saleId: string) => {
    const sale = suspendedSales.find((s) => s.id === saleId)
    if (!sale) return

    if (onResume) {
      onResume(saleId)
    }

    // Remove from suspended sales
    setSuspendedSales(suspendedSales.filter((s) => s.id !== saleId))
    setShowResumeModal(false)
  }

  const handleDeleteSuspendedSale = (saleId: string) => {
    if (window.confirm('Delete this suspended sale permanently?')) {
      setSuspendedSales(suspendedSales.filter((s) => s.id !== saleId))
    }
  }

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <>
      {/* Suspend/Resume buttons */}
      <div className="flex gap-2">
        <button
          onClick={() => setShowSuspendModal(true)}
          disabled={cartItems.length === 0}
          className="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          ⏸ Suspend
        </button>

        {suspendedSales.length > 0 && (
          <button
            onClick={() => setShowResumeModal(true)}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium text-sm relative"
          >
            ▶ Resume ({suspendedSales.length})
          </button>
        )}
      </div>

      {/* Suspend modal */}
      {showSuspendModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Suspend Sale
            </h3>

            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4">
              <p className="text-sm text-yellow-800">
                Current sale with {currentItemCount} items will be suspended for later.
              </p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason for Suspension *
                </label>
                <select
                  value={suspendReason}
                  onChange={(e) => setSuspendReason(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-yellow-500"
                >
                  <option value="">Select a reason...</option>
                  <option value="customer_stepped_out">Customer stepped out</option>
                  <option value="payment_pending">Waiting for payment</option>
                  <option value="stock_check">Checking stock</option>
                  <option value="price_verification">Price verification</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Additional Notes (optional)
                </label>
                <textarea
                  value={suspendNotes}
                  onChange={(e) => setSuspendNotes(e.target.value)}
                  placeholder="e.g., John Doe - will be back in 10 minutes"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-yellow-500 text-sm"
                  rows={3}
                />
              </div>

              <div className="bg-gray-50 rounded p-3">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">Sale Summary:</span>
                </p>
                <p className="text-sm text-gray-600 mt-1">
                  Items: {currentItemCount} | Total: ${(currentTotal / 100).toFixed(2)}
                </p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowSuspendModal(false)
                  setSuspendReason('')
                  setSuspendNotes('')
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSuspendSale}
                disabled={!suspendReason.trim()}
                className="flex-1 px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Suspend
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Resume modal */}
      {showResumeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4 max-h-96 overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 sticky top-0 bg-white">
              Resume Suspended Sale
            </h3>

            {suspendedSales.length === 0 ? (
              <p className="text-gray-600 text-center py-8">
                No suspended sales
              </p>
            ) : (
              <div className="space-y-2">
                {suspendedSales.map((sale) => (
                  <div
                    key={sale.id}
                    className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">
                          {sale.itemCount} items
                        </p>
                        <p className="text-sm text-gray-600">
                          {formatTime(sale.timestamp)}
                        </p>
                        {sale.notes && (
                          <p className="text-xs text-gray-500 mt-1">{sale.notes}</p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-gray-900">
                          ${(sale.total / 100).toFixed(2)}
                        </p>
                      </div>
                    </div>

                    <div className="flex gap-2 mt-3">
                      <button
                        onClick={() => handleResumeSale(sale.id)}
                        className="flex-1 px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                      >
                        Resume
                      </button>
                      <button
                        onClick={() => handleDeleteSuspendedSale(sale.id)}
                        className="px-3 py-1 border border-red-300 text-red-600 text-sm rounded hover:bg-red-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={() => setShowResumeModal(false)}
              className="mt-4 w-full text-center text-sm text-gray-600 hover:text-gray-900 py-2 border-t"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  )
}
