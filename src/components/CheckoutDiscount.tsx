import React, { useState } from 'react'

interface DiscountInfo {
  type: 'percentage' | 'fixed'
  value: number
  reason?: string
}

interface CheckoutDiscountProps {
  subtotal: number
  onDiscountChange: (discount: DiscountInfo | null) => void
}

export default function CheckoutDiscount({ subtotal, onDiscountChange }: CheckoutDiscountProps) {
  const [showDiscountForm, setShowDiscountForm] = useState(false)
  const [discountType, setDiscountType] = useState<'percentage' | 'fixed'>('percentage')
  const [discountValue, setDiscountValue] = useState('')
  const [discountReason, setDiscountReason] = useState('manual')
  const [appliedDiscount, setAppliedDiscount] = useState<DiscountInfo | null>(null)
  const [error, setError] = useState('')

  const handleApplyDiscount = () => {
    if (!discountValue || parseFloat(discountValue) <= 0) {
      setError('Enter a valid discount amount')
      return
    }

    const value = parseFloat(discountValue)

    if (discountType === 'percentage') {
      if (value > 100) {
        setError('Percentage cannot exceed 100%')
        return
      }
    } else {
      const maxDiscount = subtotal / 100
      if (value > maxDiscount) {
        setError(`Cannot exceed subtotal of $${maxDiscount.toFixed(2)}`)
        return
      }
    }

    const discount: DiscountInfo = {
      type: discountType,
      value,
      reason: discountReason,
    }

    setAppliedDiscount(discount)
    onDiscountChange(discount)
    setShowDiscountForm(false)
    setError('')
  }

  const handleRemoveDiscount = () => {
    setAppliedDiscount(null)
    onDiscountChange(null)
    setDiscountValue('')
    setDiscountReason('manual')
  }

  const getDiscountAmount = (): number => {
    if (!appliedDiscount) return 0

    if (appliedDiscount.type === 'percentage') {
      return (subtotal * appliedDiscount.value) / 100
    } else {
      return appliedDiscount.value * 100 // Convert to cents
    }
  }

  const discountAmount = getDiscountAmount()

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Discounts</h2>

      {appliedDiscount ? (
        // Display applied discount
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-4">
          <div className="flex justify-between items-start">
            <div>
              <p className="font-medium text-gray-900">
                {appliedDiscount.type === 'percentage'
                  ? `${appliedDiscount.value}% Discount`
                  : `$${(appliedDiscount.value).toFixed(2)} Discount`}
              </p>
              {appliedDiscount.reason && (
                <p className="text-sm text-gray-600">Reason: {appliedDiscount.reason}</p>
              )}
            </div>
            <div className="text-right">
              <p className="font-semibold text-green-600">
                -${(discountAmount / 100).toFixed(2)}
              </p>
            </div>
          </div>
          <button
            onClick={handleRemoveDiscount}
            className="mt-3 w-full text-sm px-3 py-1 border border-green-300 text-green-600 rounded hover:bg-green-50"
          >
            Remove Discount
          </button>
        </div>
      ) : (
        // Show add discount button
        <button
          onClick={() => setShowDiscountForm(true)}
          className="w-full px-4 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50 font-medium text-sm"
        >
          + Add Discount
        </button>
      )}

      {/* Discount form modal */}
      {showDiscountForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Apply Discount
            </h3>

            <div className="space-y-4">
              {/* Discount type tabs */}
              <div className="flex gap-2 border-b">
                {(['percentage', 'fixed'] as const).map((type) => (
                  <button
                    key={type}
                    onClick={() => setDiscountType(type)}
                    className={`px-4 py-2 font-medium border-b-2 transition-colors ${
                      discountType === type
                        ? 'border-indigo-600 text-indigo-600'
                        : 'border-transparent text-gray-600'
                    }`}
                  >
                    {type === 'percentage' ? 'Percentage' : 'Fixed Amount'}
                  </button>
                ))}
              </div>

              {/* Discount value input */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {discountType === 'percentage' ? 'Discount %' : 'Discount Amount ($)'}
                </label>
                <input
                  type="number"
                  step={discountType === 'percentage' ? '0.1' : '0.01'}
                  min="0"
                  value={discountValue}
                  onChange={(e) => {
                    setDiscountValue(e.target.value)
                    setError('')
                  }}
                  placeholder="0"
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Discount reason */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason (optional)
                </label>
                <select
                  value={discountReason}
                  onChange={(e) => setDiscountReason(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="manual">Manual Adjustment</option>
                  <option value="promotion">Promotion</option>
                  <option value="loyalty">Loyalty Program</option>
                  <option value="damage">Damaged Item</option>
                  <option value="customer_service">Customer Service</option>
                </select>
              </div>

              {/* Error message */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              {/* Discount preview */}
              {discountValue && !error && (
                <div className="bg-blue-50 border border-blue-200 rounded p-3">
                  <div className="flex justify-between text-sm">
                    <span>Discount:</span>
                    <span className="font-semibold text-blue-600">
                      -${(parseFloat(discountValue) * (discountType === 'percentage' ? subtotal / 10000 : 1)).toFixed(2)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowDiscountForm(false)
                  setError('')
                  setDiscountValue('')
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyDiscount}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
