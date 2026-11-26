import React, { useState } from 'react'
import { usePOSStore } from '../stores'
import { formatMinorUnits } from '../money'

interface LineItemData {
  productId: number
  quantity: number
  unitPrice: number
  name: string
}

interface CheckoutLineItemProps {
  item: LineItemData
  disabled?: boolean
}

export default function CheckoutLineItem({ item, disabled = false }: CheckoutLineItemProps) {
  const { updateQuantity, removeFromCart } = usePOSStore()
  const [showRemoveConfirm, setShowRemoveConfirm] = useState(false)

  const lineTotal = item.quantity * item.unitPrice

  const handleQuantityChange = (newQty: number) => {
    if (newQty >= 1 && newQty <= 9999) {
      updateQuantity(item.productId, newQty)
    }
  }

  const handleRemove = () => {
    removeFromCart(item.productId)
    setShowRemoveConfirm(false)
  }

  return (
    <>
      <div className="bg-gray-50 border rounded-lg p-4 flex items-center justify-between gap-4">
        <div className="flex-1">
          <h3 className="font-medium text-gray-900">{item.name}</h3>
          <p className="text-sm text-gray-600">
            {formatMinorUnits(item.unitPrice)} × {item.quantity}
          </p>
        </div>

        {/* Quantity controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleQuantityChange(item.quantity - 1)}
            disabled={disabled || item.quantity === 1}
            className="px-2 py-1 border rounded text-gray-600 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed"
          >
            −
          </button>
          <input
            type="number"
            min="1"
            max="9999"
            value={item.quantity}
            onChange={(e) => handleQuantityChange(parseInt(e.target.value) || 1)}
            disabled={disabled}
            className="w-12 text-center border rounded py-1 text-sm"
          />
          <button
            onClick={() => handleQuantityChange(item.quantity + 1)}
            disabled={disabled}
            className="px-2 py-1 border rounded text-gray-600 hover:bg-white"
          >
            +
          </button>
        </div>

        {/* Line total */}
        <div className="text-right min-w-20">
          <p className="font-semibold text-gray-900">{formatMinorUnits(lineTotal)}</p>
        </div>

        {/* Remove button */}
        <button
          onClick={() => setShowRemoveConfirm(true)}
          disabled={disabled}
          className="px-3 py-1 text-red-600 hover:bg-red-50 rounded"
        >
          Remove
        </button>
      </div>

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
                disabled={disabled}
                className="flex-1 px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleRemove}
                disabled={disabled}
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
