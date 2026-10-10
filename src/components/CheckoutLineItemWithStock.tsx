import React, { useEffect, useState } from 'react'
import { inventoryAPI } from '../api'
import { useAppContextStore } from '../stores'

interface LineItemData {
  productId: number
  quantity: number
  unitPrice: number
  name: string
}

interface CheckoutLineItemWithStockProps {
  item: LineItemData
  onUpdateQuantity: (productId: number, quantity: number) => void
  onRemove: (productId: number) => void
}

export default function CheckoutLineItemWithStock({
  item,
  onUpdateQuantity,
  onRemove,
}: CheckoutLineItemWithStockProps) {
  const { selectedLocation } = useAppContextStore()
  const [availableStock, setAvailableStock] = useState<number | null>(null)
  const [isLoadingStock, setIsLoadingStock] = useState(true)
  const [stockError, setStockError] = useState('')
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false)

  useEffect(() => {
    const fetchStock = async () => {
      if (!selectedLocation) {
        setIsLoadingStock(false)
        return
      }

      try {
        const response = await inventoryAPI.getStock(item.productId, selectedLocation.id)
        setAvailableStock(response.data.quantity)
        setStockError('')
      } catch (error) {
        setStockError('Stock unavailable')
        setAvailableStock(0)
      } finally {
        setIsLoadingStock(false)
      }
    }

    fetchStock()
  }, [item.productId, selectedLocation])

  const handleQuantityChange = (newQty: number) => {
    // Prevent exceeding available stock
    if (availableStock !== null && newQty > availableStock) {
      setStockError(`Only ${availableStock} available`)
      return
    }

    if (newQty >= 1 && newQty <= 9999) {
      onUpdateQuantity(item.productId, newQty)
      setStockError('')
    }
  }

  const lineTotal = item.quantity * item.unitPrice
  const isStockLow = availableStock !== null && availableStock < 10
  const isOutOfStock = availableStock === 0

  return (
    <>
      <div className={`bg-gray-50 border rounded-lg p-4 flex items-center justify-between gap-4 ${
        isOutOfStock ? 'opacity-75 bg-red-50' : ''
      }`}>
        <div className="flex-1">
          <h3 className="font-medium text-gray-900">{item.name}</h3>
          <p className="text-sm text-gray-600">
            ${(item.unitPrice / 100).toFixed(2)} × {item.quantity}
          </p>
          {isLoadingStock ? (
            <p className="text-xs text-gray-500 mt-1">Checking stock...</p>
          ) : isOutOfStock ? (
            <p className="text-xs text-red-600 mt-1 font-medium">Out of stock</p>
          ) : isStockLow ? (
            <p className="text-xs text-yellow-600 mt-1">Only {availableStock} available</p>
          ) : (
            <p className="text-xs text-green-600 mt-1">{availableStock} available</p>
          )}
        </div>

        {/* Quantity controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleQuantityChange(item.quantity - 1)}
            disabled={item.quantity === 1 || isOutOfStock}
            className="px-2 py-1 border rounded text-gray-600 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            −
          </button>
          <input
            type="number"
            min="1"
            max={availableStock || 9999}
            value={item.quantity}
            onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 1)}
            disabled={isOutOfStock}
            className="w-12 text-center border rounded py-1 text-sm disabled:opacity-50"
          />
          <button
            onClick={() => handleQuantityChange(item.quantity + 1)}
            disabled={availableStock !== null && item.quantity >= availableStock}
            className="px-2 py-1 border rounded text-gray-600 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            +
          </button>
        </div>

        {/* Line total */}
        <div className="text-right min-w-20">
          <p className="font-semibold text-gray-900">${(lineTotal / 100).toFixed(2)}</p>
        </div>

        {/* Remove button */}
        <button
          onClick={() => setShowRemoveConfirm(true)}
          className="px-3 py-1 text-red-600 hover:bg-red-50 rounded"
        >
          Remove
        </button>
      </div>

      {/* Error message for stock */}
      {stockError && (
        <div className="text-red-600 text-sm mt-1">{stockError}</div>
      )}

      {/* Remove confirmation dialog */}
      {showRemoveConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">
              Remove item?
            </h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to remove {item.name} from the cart?
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowRemoveConfirm(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  onRemove(item.productId)
                  setShowRemoveConfirm(false)
                }}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
