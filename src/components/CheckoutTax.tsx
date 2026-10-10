import React, { useState, useMemo } from 'react'

export interface TaxBreakdown {
  rate: number
  taxableAmount: number
  taxAmount: number
}

interface CheckoutTaxProps {
  subtotal: number
  discount?: number
  selectedTaxRate?: number
  onTaxRateChange: (rate: number) => void
}

// Standard tax rates by country/region
const TAX_RATES = [
  { rate: 0, label: 'No Tax' },
  { rate: 5, label: 'Reduced Rate (5%)' },
  { rate: 15, label: 'Standard Rate (15%)' },
  { rate: 20, label: 'High Rate (20%)' },
]

export default function CheckoutTax({
  subtotal,
  discount = 0,
  selectedTaxRate = 15,
  onTaxRateChange,
}: CheckoutTaxProps) {
  const [showTaxSelector, setShowTaxSelector] = useState(false)
  const [customRate, setCustomRate] = useState<number | null>(null)

  // Calculate taxable amount (after discount)
  const taxableAmount = Math.max(0, subtotal - discount)

  // Calculate tax based on selected rate
  const calculateTax = (rate: number) => {
    return Math.round((taxableAmount * rate) / 100)
  }

  const currentRate = customRate !== null ? customRate : selectedTaxRate
  const taxAmount = calculateTax(currentRate)
  const total = taxableAmount + taxAmount

  const handleSelectRate = (rate: number) => {
    setCustomRate(null)
    onTaxRateChange(rate)
    setShowTaxSelector(false)
  }

  const handleCustomRate = () => {
    if (customRate !== null && customRate >= 0 && customRate <= 100) {
      onTaxRateChange(customRate)
      setShowTaxSelector(false)
    }
  }

  const getTaxLabel = (rate: number) => {
    const standard = TAX_RATES.find((t) => t.rate === rate)
    return standard?.label || `Custom (${rate}%)`
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Tax Information</h2>
        <button
          onClick={() => setShowTaxSelector(!showTaxSelector)}
          className="text-sm text-indigo-600 hover:text-indigo-700 font-medium"
        >
          Change Rate
        </button>
      </div>

      {/* Tax calculation breakdown */}
      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between text-gray-700">
          <span>Subtotal:</span>
          <span>${(subtotal / 100).toFixed(2)}</span>
        </div>

        {discount > 0 && (
          <>
            <div className="flex justify-between text-gray-700">
              <span>Discount:</span>
              <span className="text-green-600">-${(discount / 100).toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-gray-700">
              <span>Taxable Amount:</span>
              <span>${(taxableAmount / 100).toFixed(2)}</span>
            </div>
          </>
        )}

        <div className="border-t pt-2 flex justify-between font-medium">
          <span>Tax ({currentRate}%):</span>
          <span>${(taxAmount / 100).toFixed(2)}</span>
        </div>

        <div className="flex justify-between text-lg font-bold text-gray-900 pt-2 border-t">
          <span>Total:</span>
          <span>${(total / 100).toFixed(2)}</span>
        </div>
      </div>

      {/* Current tax rate display */}
      <div className="bg-gray-50 rounded p-3 mb-4">
        <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Current Rate</p>
        <p className="text-sm font-semibold text-gray-900">
          {getTaxLabel(currentRate)}
        </p>
      </div>

      {/* Tax rate selector */}
      {showTaxSelector && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Select Tax Rate
            </h3>

            <div className="space-y-2 mb-4">
              {TAX_RATES.map((taxOption) => (
                <button
                  key={taxOption.rate}
                  onClick={() => handleSelectRate(taxOption.rate)}
                  className={`w-full text-left px-4 py-2 rounded border-2 transition-colors ${
                    currentRate === taxOption.rate
                      ? 'border-indigo-600 bg-indigo-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium text-gray-900">{taxOption.label}</div>
                  <div className="text-sm text-gray-600 mt-1">
                    Tax on ${(taxableAmount / 100).toFixed(2)}: ${(calculateTax(taxOption.rate) / 100).toFixed(2)}
                  </div>
                </button>
              ))}
            </div>

            {/* Custom rate input */}
            <div className="border-t pt-4">
              <p className="text-sm font-medium text-gray-900 mb-2">Custom Rate</p>
              <div className="flex gap-2">
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={customRate ?? selectedTaxRate}
                  onChange={(e) => setCustomRate(parseFloat(e.target.value) || 0)}
                  className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="0"
                />
                <span className="flex items-center text-gray-600">%</span>
              </div>
              <button
                onClick={handleCustomRate}
                className="mt-2 w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium"
              >
                Apply Custom Rate
              </button>
            </div>

            {/* Close button */}
            <button
              onClick={() => {
                setShowTaxSelector(false)
                setCustomRate(null)
              }}
              className="mt-4 w-full text-center text-sm text-gray-600 hover:text-gray-900 py-2 border-t"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * Tax calculation utility function
 * Used throughout checkout to calculate tax amounts
 */
export function calculateTotalWithTax(
  subtotal: number,
  taxRate: number,
  discount: number = 0
): { subtotal: number; discount: number; taxableAmount: number; tax: number; total: number } {
  const taxableAmount = Math.max(0, subtotal - discount)
  const tax = Math.round((taxableAmount * taxRate) / 100)
  const total = taxableAmount + tax

  return {
    subtotal,
    discount,
    taxableAmount,
    tax,
    total,
  }
}
