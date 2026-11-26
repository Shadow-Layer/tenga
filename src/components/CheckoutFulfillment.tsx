import React, { useState, useEffect } from 'react'

interface FulfillmentItem {
  id: string
  productId: number
  productName: string
  quantity: number
  quantityPicked: number
  status: 'pending' | 'picked' | 'packed' | 'ready' | 'dispatched'
}

interface FulfillmentOrder {
  id: string
  saleId: number
  status: 'new' | 'picking' | 'packing' | 'ready' | 'dispatched'
  items: FulfillmentItem[]
  createdAt: Date
  pickedAt?: Date
  packedAt?: Date
  readyAt?: Date
  dispatchedAt?: Date
}

interface CheckoutFulfillmentProps {
  saleId: number
  items: Array<{ productId: number; name: string; quantity: number }>
  onStatusChange?: (orderId: string, status: FulfillmentOrder['status']) => void
}

export default function CheckoutFulfillment({
  saleId,
  items,
  onStatusChange,
}: CheckoutFulfillmentProps) {
  const [fulfillmentOrder, setFulfillmentOrder] = useState<FulfillmentOrder | null>(null)
  const [showFulfillmentModal, setShowFulfillmentModal] = useState(false)
  const [currentStep, setCurrentStep] = useState<'picking' | 'packing' | 'ready'>('picking')

  useEffect(() => {
    // Initialize fulfillment order
    const order: FulfillmentOrder = {
      id: `fulfillment-${Date.now()}`,
      saleId,
      status: 'new',
      items: items.map((item, idx) => ({
        id: `item-${idx}`,
        productId: item.productId,
        productName: item.name,
        quantity: item.quantity,
        quantityPicked: 0,
        status: 'pending',
      })),
      createdAt: new Date(),
    }
    setFulfillmentOrder(order)
  }, [saleId, items])

  const handlePickItem = (itemId: string, quantity: number) => {
    if (!fulfillmentOrder) return

    const updatedItems = fulfillmentOrder.items.map((item) => {
      if (item.id === itemId) {
        const newQuantityPicked = Math.min(item.quantity, quantity)
        return {
          ...item,
          quantityPicked: newQuantityPicked,
          status: newQuantityPicked === item.quantity ? 'picked' as const : 'pending' as const,
        }
      }
      return item
    })

    const allPicked = updatedItems.every((item) => item.quantityPicked === item.quantity)

    setFulfillmentOrder({
      ...fulfillmentOrder,
      items: updatedItems,
      status: allPicked ? 'picking' : 'picking',
      pickedAt: allPicked ? new Date() : undefined,
    })
  }

  const handleProceedToPacking = () => {
    if (!fulfillmentOrder) return

    const allPicked = fulfillmentOrder.items.every(
      (item) => item.quantityPicked === item.quantity
    )

    if (!allPicked) {
      alert('Please pick all items before proceeding to packing')
      return
    }

    const packedItems = fulfillmentOrder.items.map((item) => ({
      ...item,
      status: 'packed' as const,
    }))

    setFulfillmentOrder({
      ...fulfillmentOrder,
      items: packedItems,
      status: 'packing',
      packedAt: new Date(),
    })

    setCurrentStep('packing')

    if (onStatusChange) {
      onStatusChange(fulfillmentOrder.id, 'packing')
    }
  }

  const handleProceedToReady = () => {
    if (!fulfillmentOrder) return

    const readyItems = fulfillmentOrder.items.map((item) => ({
      ...item,
      status: 'ready' as const,
    }))

    setFulfillmentOrder({
      ...fulfillmentOrder,
      items: readyItems,
      status: 'ready',
      readyAt: new Date(),
    })

    setCurrentStep('ready')

    if (onStatusChange) {
      onStatusChange(fulfillmentOrder.id, 'ready')
    }
  }

  const handleDispatch = () => {
    if (!fulfillmentOrder) return

    const dispatchedItems = fulfillmentOrder.items.map((item) => ({
      ...item,
      status: 'dispatched' as const,
    }))

    setFulfillmentOrder({
      ...fulfillmentOrder,
      items: dispatchedItems,
      status: 'dispatched',
      dispatchedAt: new Date(),
    })

    if (onStatusChange) {
      onStatusChange(fulfillmentOrder.id, 'dispatched')
    }

    alert('Order dispatched successfully!')
    setShowFulfillmentModal(false)
  }

  const getProgressPercentage = () => {
    if (!fulfillmentOrder) return 0

    const completed = fulfillmentOrder.items.filter(
      (item) => item.status === 'dispatched'
    ).length

    return (completed / fulfillmentOrder.items.length) * 100
  }

  const getStepIndicator = (step: string, completed: boolean) => {
    return (
      <div className={`flex items-center ${completed ? 'text-green-600' : 'text-gray-400'}`}>
        <div
          className={`w-8 h-8 rounded-full border-2 flex items-center justify-center ${
            completed ? 'bg-green-600 border-green-600 text-white' : 'border-gray-300'
          }`}
        >
          {completed ? '✓' : step[0].toUpperCase()}
        </div>
        <span className="ml-2 text-sm font-medium">{step}</span>
      </div>
    )
  }

  if (!fulfillmentOrder) return null

  return (
    <div className="space-y-3">
      <button
        onClick={() => setShowFulfillmentModal(true)}
        className="w-full px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium text-sm"
      >
        📦 View Fulfillment
      </button>

      {/* Fulfillment modal */}
      {showFulfillmentModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Fulfillment Workflow - Sale #{fulfillmentOrder.saleId}
            </h3>

            {/* Progress bar */}
            <div className="mb-6">
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Progress</span>
                <span className="text-sm font-medium text-gray-700">
                  {Math.round(getProgressPercentage())}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{ width: `${getProgressPercentage()}%` }}
                />
              </div>
            </div>

            {/* Workflow steps */}
            <div className="grid grid-cols-4 gap-4 mb-6">
              {getStepIndicator('Picking', fulfillmentOrder.status !== 'new')}
              {getStepIndicator('Packing', ['packing', 'ready', 'dispatched'].includes(fulfillmentOrder.status))}
              {getStepIndicator('Ready', ['ready', 'dispatched'].includes(fulfillmentOrder.status))}
              {getStepIndicator('Dispatched', fulfillmentOrder.status === 'dispatched')}
            </div>

            {/* Items list */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <h4 className="font-medium text-gray-900 mb-3">Items to Fulfill</h4>
              <div className="space-y-2">
                {fulfillmentOrder.items.map((item) => (
                  <div
                    key={item.id}
                    className={`flex items-center justify-between p-3 border rounded ${
                      item.status === 'dispatched'
                        ? 'bg-green-50 border-green-200'
                        : 'bg-white border-gray-200'
                    }`}
                  >
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{item.productName}</p>
                      <p className="text-sm text-gray-600">
                        Required: {item.quantity} | Picked: {item.quantityPicked}
                      </p>
                    </div>
                    <div className="text-right">
                      <p
                        className={`text-sm font-semibold ${
                          item.status === 'picked' ? 'text-green-600' : 'text-gray-600'
                        }`}
                      >
                        {item.status === 'dispatched' ? '✓ Done' : item.status}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Action buttons */}
            {fulfillmentOrder.status === 'new' && (
              <div className="flex gap-3">
                <button
                  onClick={() => setShowFulfillmentModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
                <button
                  onClick={handleProceedToPacking}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Start Picking
                </button>
              </div>
            )}

            {fulfillmentOrder.status === 'picking' && (
              <div className="flex gap-3">
                <button
                  onClick={() => setShowFulfillmentModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
                <button
                  onClick={handleProceedToPacking}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Proceed to Packing
                </button>
              </div>
            )}

            {fulfillmentOrder.status === 'packing' && (
              <div className="flex gap-3">
                <button
                  onClick={() => setShowFulfillmentModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
                <button
                  onClick={handleProceedToReady}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Ready for Dispatch
                </button>
              </div>
            )}

            {fulfillmentOrder.status === 'ready' && (
              <div className="flex gap-3">
                <button
                  onClick={() => setShowFulfillmentModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
                <button
                  onClick={handleDispatch}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Dispatch Order
                </button>
              </div>
            )}

            {fulfillmentOrder.status === 'dispatched' && (
              <div className="flex justify-center">
                <button
                  onClick={() => setShowFulfillmentModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
