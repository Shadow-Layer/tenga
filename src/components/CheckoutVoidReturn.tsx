import React, { useState } from 'react'
import { salesAPI } from '../api'

interface Sale {
  id: number
  total_amount: number | string
  payment_method: string
  created_at: string
  sale_items: Array<{
    product_id: number
    quantity: number
    unit_price: number | string
    total_price?: number | string
    tax_inclusive?: boolean
    tax_amount?: number | string
  }>
}

interface VoidReturnProps {
  saleId?: number
  onVoid?: (saleId: number, reason: string) => void
  onReturn?: (saleId: number, items: number[]) => void
}

export default function CheckoutVoidReturn({ saleId, onVoid, onReturn }: VoidReturnProps) {
  const [showVoidModal, setShowVoidModal] = useState(false)
  const [showReturnModal, setShowReturnModal] = useState(false)
  const [voidReason, setVoidReason] = useState('')
  const [returnReason, setReturnReason] = useState('')
  const [selectedItems, setSelectedItems] = useState<number[]>([])
  const [sale, setSale] = useState<Sale | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleOpenVoidModal = async () => {
    if (!saleId) {
      setError('No sale selected')
      return
    }

    setLoading(true)
    try {
      const response = await salesAPI.get(saleId)
      setSale(response.data)
      setShowVoidModal(true)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sale')
    } finally {
      setLoading(false)
    }
  }

  const handleOpenReturnModal = async () => {
    if (!saleId) {
      setError('No sale selected')
      return
    }

    setLoading(true)
    try {
      const response = await salesAPI.get(saleId)
      setSale(response.data)
      setShowReturnModal(true)
      setError('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sale')
    } finally {
      setLoading(false)
    }
  }

  const handleVoidSale = () => {
    if (!voidReason.trim()) {
      setError('Please provide a reason for void')
      return
    }

    if (!saleId) return

    // In real system, would call void API
    if (onVoid) {
      onVoid(saleId, voidReason)
    }

    setShowVoidModal(false)
    setVoidReason('')
  }

  const handleReturnItems = () => {
    if (selectedItems.length === 0) {
      setError('Please select items to return')
      return
    }

    if (!returnReason.trim()) {
      setError('Please provide a reason for return')
      return
    }

    if (!saleId) return

    // In real system, would call return API
    if (onReturn) {
      onReturn(saleId, selectedItems)
    }

    setShowReturnModal(false)
    setSelectedItems([])
    setReturnReason('')
  }

  const toggleItemSelection = (index: number) => {
    if (selectedItems.includes(index)) {
      setSelectedItems(selectedItems.filter((i) => i !== index))
    } else {
      setSelectedItems([...selectedItems, index])
    }
  }

  const calculateReturnAmount = () => {
    if (!sale) return 0

    return sale.sale_items
      .filter((_, idx) => selectedItems.includes(idx))
      .reduce((sum, item) => {
        const base = Number(item.total_price ?? Number(item.unit_price) * item.quantity)
        const tax = item.tax_inclusive ? 0 : Number(item.tax_amount ?? 0)
        return sum + base + tax
      }, 0)
  }

  return (
    <div className="space-y-3">
      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-3">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleOpenVoidModal}
          disabled={!saleId || loading}
          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          ✕ Void Sale
        </button>

        <button
          onClick={handleOpenReturnModal}
          disabled={!saleId || loading}
          className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed text-sm"
        >
          ↩ Return Items
        </button>
      </div>

      {/* Void modal */}
      {showVoidModal && sale && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Void Sale
            </h3>

            <div className="bg-red-50 border border-red-200 rounded p-3 mb-4">
              <p className="text-sm text-red-800">
                ⚠️ This will completely void Sale #{sale.id} and the transaction cannot be reversed.
              </p>
            </div>

            <div className="bg-gray-50 rounded p-3 mb-4">
              <p className="text-sm text-gray-700">
                <span className="font-semibold">Sale Amount:</span> {Number(sale.total_amount).toFixed(2)}
              </p>
              <p className="text-sm text-gray-700 mt-1">
                <span className="font-semibold">Payment Method:</span> {sale.payment_method}
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reason for Void *
              </label>
              <select
                value={voidReason}
                onChange={(e) => setVoidReason(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-red-500"
              >
                <option value="">Select a reason...</option>
                <option value="duplicate_transaction">Duplicate Transaction</option>
                <option value="incorrect_amount">Incorrect Amount</option>
                <option value="wrong_product">Wrong Product</option>
                <option value="customer_cancellation">Customer Cancellation</option>
                <option value="system_error">System Error</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowVoidModal(false)
                  setVoidReason('')
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleVoidSale}
                disabled={!voidReason.trim()}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Void Sale
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Return modal */}
      {showReturnModal && sale && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-md w-full mx-4 max-h-96 overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 sticky top-0 bg-white">
              Return Items
            </h3>

            <div className="space-y-3 mb-4">
              {sale.sale_items.map((item, idx) => (
                <label key={idx} className="flex items-center p-3 border rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedItems.includes(idx)}
                    onChange={() => toggleItemSelection(idx)}
                    className="w-4 h-4 text-orange-600 rounded focus:ring-orange-500"
                  />
                  <div className="ml-3 flex-1">
                    <p className="font-medium text-gray-900">
                      Product {item.product_id}
                    </p>
                    <p className="text-sm text-gray-600">
                      Qty: {item.quantity} × {Number(item.unit_price).toFixed(2)}
                    </p>
                  </div>
                  <p className="font-semibold text-gray-900">
                    {Number(item.total_price ?? Number(item.unit_price) * item.quantity).toFixed(2)}
                  </p>
                </label>
              ))}
            </div>

            <div className="border-t pt-3 mb-4">
              <p className="text-sm text-gray-700">
                <span className="font-semibold">Return Amount:</span>
              </p>
              <p className="text-lg font-bold text-orange-600">
                {calculateReturnAmount().toFixed(2)}
              </p>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Reason for Return *
              </label>
              <select
                value={returnReason}
                onChange={(e) => setReturnReason(e.target.value)}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500"
              >
                <option value="">Select a reason...</option>
                <option value="defective">Defective/Damaged</option>
                <option value="wrong_item">Wrong Item</option>
                <option value="expired">Expired</option>
                <option value="customer_change_mind">Customer Changed Mind</option>
                <option value="other">Other</option>
              </select>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowReturnModal(false)
                  setSelectedItems([])
                  setReturnReason('')
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReturnItems}
                disabled={selectedItems.length === 0 || !returnReason.trim()}
                className="flex-1 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Return Items
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
