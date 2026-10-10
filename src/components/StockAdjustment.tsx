import React, { useState } from 'react'
import { ChevronLeft, Plus, Minus, RotateCcw } from 'lucide-react'
import { useAuthStore, useAppContextStore } from '../stores'
import { inventoryAPI } from '../api'

/**
 * Stock Adjustment Screen
 * 
 * Quick adjustment interface for inventory corrections.
 * Supports:
 * - Manual count (set absolute value)
 * - Add stock (restock arrival)
 * - Remove stock (damage, loss, return)
 * 
 * Each adjustment creates a permanent audit entry.
 * Reason is required for accountability.
 * 
 * SECURITY NOTES FOR API INTEGRATION:
 * - DO NOT send: recorded_by_id, organization_id
 * - The backend derives these from the authenticated JWT token
 * - Sending these fields will be rejected by the server
 * - Map user-facing reason labels to backend canonical codes:
 *   'PHYSICAL_COUNT_DISCREPANCY', 'DAMAGE', 'SHRINKAGE', 'ADJUSTMENT'
 * - The backend will verify the location belongs to the user's organization
 */

const reasonMapping: Record<string, string> = {
  'Restock - Supplier Delivery': 'ADJUSTMENT',
  'Return from Customer': 'ADJUSTMENT',
  'Correction': 'ADJUSTMENT',
  'Sale': 'ADJUSTMENT',
  'Damage': 'DAMAGE',
  'Loss/Theft': 'SHRINKAGE',
  'Expiration': 'SHRINKAGE',
  'Return to Supplier': 'ADJUSTMENT',
  'Physical Count': 'PHYSICAL_COUNT_DISCREPANCY',
  'Cycle Count': 'PHYSICAL_COUNT_DISCREPANCY',
  'Reconciliation': 'PHYSICAL_COUNT_DISCREPANCY',
  'Other': 'ADJUSTMENT',
}

export function StockAdjustment() {
  const token = useAuthStore((state) => state.token)
  const selectedLocation = useAppContextStore((state) => state.selectedLocation)
  
  const [adjustmentType, setAdjustmentType] = useState<'add' | 'remove' | 'count'>('add')
  const [quantity, setQuantity] = useState('')
  const [reason, setReason] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [lastSubmitTime, setLastSubmitTime] = useState(0)

  const product = {
    id: 1,
    name: 'Premium Coffee',
    sku: 'COFFEE-001',
    currentStock: 15,
  }

  const reasons = {
    add: ['Restock - Supplier Delivery', 'Return from Customer', 'Correction', 'Other'],
    remove: ['Sale', 'Damage', 'Loss/Theft', 'Expiration', 'Return to Supplier', 'Other'],
    count: ['Physical Count', 'Cycle Count', 'Reconciliation', 'Other'],
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
     
    // Prevent duplicate submissions
    const now = Date.now()
    if (now - lastSubmitTime < 1000) return
    setLastSubmitTime(now)

    if (!token) {
      setError('Authentication required. Please log in.')
      return
    }

    if (!selectedLocation) {
      setError('Please select a location first.')
      return
    }

    if (!reason || !reasonMapping[reason]) {
      setError('Please select a valid reason for adjustment.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const canonicalReason = reasonMapping[reason] || 'ADJUSTMENT'
      const quantityNum = parseInt(quantity)
      
      // Calculate actual quantity change for API
      let adjustmentQuantity = quantityNum
      if (adjustmentType === 'remove') {
        adjustmentQuantity = -quantityNum
      }
      // For 'count' type, send the absolute count value

      await inventoryAPI.adjustStock({
        product_id: product.id,
        location_id: selectedLocation.id,
        quantity: adjustmentQuantity,
        reason: canonicalReason,
        note: note || undefined,
      })

      setSuccess(true)
      setTimeout(() => {
        setSuccess(false)
        setQuantity('')
        setReason('')
        setNote('')
      }, 3000)
    } catch (err: any) {
      const status = err.response?.status
      const errorMessage = err.response?.data?.detail || err.response?.data?.message

      if (status === 400) {
        setError('Invalid input. Please check your values.')
      } else if (status === 403) {
        setError('Access denied. You do not have permission.')
      } else if (status === 404) {
        setError('Product or location not found.')
      } else if (status === 500) {
        setError('Server error. Please try again.')
      } else {
        setError(errorMessage || 'Failed to record adjustment. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <button className="p-1.5 rounded-lg hover:bg-gray-100 transition">
              <ChevronLeft size={20} className="text-gray-600" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Adjust Stock</h1>
              <p className="text-sm text-gray-500 mt-0.5">
                {product.name} ({product.sku})
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Form */}
      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Current Stock Display */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-blue-600 font-medium uppercase tracking-wide mb-1">Current Stock</p>
          <p className="text-3xl font-bold text-blue-700">{product.currentStock} units</p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <span className="text-red-600 text-lg">⚠</span>
            <div>
              <p className="text-sm font-medium text-red-700">{error}</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6">
          {/* Adjustment Type Buttons */}
          <div className="mb-6">
            <p className="text-sm font-medium text-gray-900 mb-3">What are you doing?</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setAdjustmentType('add')}
                className={`py-3 px-4 rounded-lg border-2 transition font-medium text-center h-14 ${
                  adjustmentType === 'add'
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <Plus size={20} className="mx-auto mb-1" />
                Add Stock
              </button>
              <button
                type="button"
                onClick={() => setAdjustmentType('remove')}
                className={`py-3 px-4 rounded-lg border-2 transition font-medium text-center h-14 ${
                  adjustmentType === 'remove'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <Minus size={20} className="mx-auto mb-1" />
                Remove Stock
              </button>
              <button
                type="button"
                onClick={() => setAdjustmentType('count')}
                className={`py-3 px-4 rounded-lg border-2 transition font-medium text-center h-14 ${
                  adjustmentType === 'count'
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <RotateCcw size={20} className="mx-auto mb-1" />
                Physical Count
              </button>
            </div>
          </div>

          {/* Quantity Input */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-900 mb-2">
              {adjustmentType === 'count' ? 'Actual Count' : adjustmentType === 'add' ? 'Add Quantity' : 'Remove Quantity'} *
            </label>
            <div className="flex items-center gap-3">
              <input
                type="number"
                min="0"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="0"
               className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg font-semibold h-12 text-base"
                required
              />
              <span className="text-lg font-medium text-gray-600">units</span>
            </div>
          </div>

          {/* New Stock Preview */}
          {quantity && (
            <div className="mb-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-2">Stock after adjustment</p>
              <p className="text-2xl font-bold text-gray-900">
                {adjustmentType === 'count' ? quantity : adjustmentType === 'add' ? product.currentStock + parseInt(quantity) : Math.max(0, product.currentStock - parseInt(quantity))} units
              </p>
            </div>
          )}

          {/* Reason Dropdown */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-900 mb-2">Reason *</label>
            <select
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 h-12 text-base"
              required
            >
              <option value="">— Select a reason —</option>
              {reasons[adjustmentType].map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          {/* Notes */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-900 mb-2">Additional Notes</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="E.g., Invoice #, customer name, etc."
              rows={3}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
            />
          </div>

          {/* Success Message */}
          {success && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
              <span className="text-green-600 text-lg">✓</span>
              <div>
                <p className="text-sm font-medium text-green-700">Adjustment recorded successfully</p>
                <p className="text-xs text-green-600 mt-0.5">Stock has been updated and audit entry created</p>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 border-t border-gray-200 flex-col sm:flex-row">
            <button
              type="button"
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium h-12 text-base"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !quantity || !reason}
              className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition font-medium h-12 text-base"
            >
              {loading ? 'Saving...' : 'Record Adjustment'}
            </button>
          </div>
        </form>

        {/* Info Box */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            <strong>💡 Note:</strong> All adjustments are recorded in the audit log. Users cannot modify or delete previous entries.
          </p>
        </div>
      </div>
    </div>
  )
}

export default StockAdjustment
