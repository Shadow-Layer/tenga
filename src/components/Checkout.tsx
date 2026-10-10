import React, { useState, useRef, useEffect } from 'react'
import { usePOSStore } from '../stores'
import { useAppContextStore } from '../stores'
import { productsAPI } from '../api'
import CheckoutLineItem from './CheckoutLineItem'
import CheckoutPayment from './CheckoutPayment'
import CheckoutCustomer from './CheckoutCustomer'

interface CheckoutProps {
  onClose?: () => void
}

export default function Checkout({ onClose }: CheckoutProps) {
  const { cartItems, clearCart, addToCart } = usePOSStore()
  const { selectedTill } = useAppContextStore()
  const [showPayment, setShowPayment] = useState(false)
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [barcodeError, setBarcodeError] = useState('')
  const [lastScannedTime, setLastScannedTime] = useState(0)
  const barcodeInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  const handleBarcodeScan = async (barcode: string) => {
    if (!barcode.trim()) return

    const now = Date.now()
    const timeSinceLastScan = now - lastScannedTime

    // Debounce rapid scans (prevent double-adds within 300ms)
    if (timeSinceLastScan < 300) {
      setBarcodeError('Scanning too fast - please wait')
      setTimeout(() => setBarcodeError(''), 2000)
      return
    }

    setLastScannedTime(now)
    setBarcodeError('')

    try {
      // Search for product by barcode
      const response = await productsAPI.search(1, barcode) // organizationId = 1 (hardcoded for MVP)
      
      if (response.data.data && response.data.data.length > 0) {
        const product = response.data.data[0]
        
        // Add to cart (qty=1)
        addToCart(product.id, 1, product.price, product.name)
        
        // Clear input and show success feedback
        if (barcodeInputRef.current) {
          barcodeInputRef.current.value = ''
          barcodeInputRef.current.focus()
        }
      } else {
        setBarcodeError(`Product not found: ${barcode}`)
        setTimeout(() => setBarcodeError(''), 3000)
      }
    } catch (error: any) {
      setBarcodeError('Failed to scan product - check connection')
      setTimeout(() => setBarcodeError(''), 3000)
    }
  }

  const handleBarcodeKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      const barcode = (e.target as HTMLInputElement).value.trim()
      handleBarcodeScan(barcode)
    }
  }

  // Calculate totals
  const subtotal = cartItems.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0)
  const tax = subtotal * 0.15 // 15% tax (placeholder, to be refined in T9)
  const total = subtotal + tax

  const handleCancel = () => {
    clearCart()
    setShowPayment(false)
    if (onClose) onClose()
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with sync status */}
      <div className="bg-white border-b p-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Checkout</h1>
          {selectedTill && <p className="text-sm text-gray-600">Till: {selectedTill.name}</p>}
        </div>
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium ${
            isOnline
              ? 'bg-green-100 text-green-800'
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-green-600' : 'bg-yellow-600'}`} />
            {isOnline ? 'Online' : 'Offline'}
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="flex gap-4 p-4">
        {/* Left side: Barcode scanner & line items */}
        <div className="flex-1">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Scan Items</h2>
            
            {/* Barcode scanner input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Scan Barcode (Press Enter to add)
              </label>
              <input
                ref={barcodeInputRef}
                type="text"
                onKeyDown={handleBarcodeKeyDown}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="Scan or type product barcode..."
                autoFocus
              />
              {barcodeError && (
                <p className="text-red-600 text-sm mt-2">{barcodeError}</p>
              )}
            </div>

            {/* Line items */}
            <div className="space-y-2">
              {cartItems.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>No items in cart</p>
                  <p className="text-sm">Scan a product barcode to get started</p>
                </div>
              ) : (
                cartItems.map((item) => (
                  <CheckoutLineItem
                    key={item.productId}
                    item={item}
                  />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right side: Order summary & payment */}
        <div className="w-96">
          {/* Order summary panel */}
          <div className="bg-white rounded-lg shadow p-6 mb-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Order Summary</h2>
            
            {/* Item count */}
            <div className="flex justify-between items-center mb-4 pb-4 border-b">
              <span className="text-gray-600">Items in cart:</span>
              <span className="text-lg font-semibold text-gray-900">
                {cartItems.length}
              </span>
            </div>

            {/* Totals */}
            <div className="space-y-2">
              <div className="flex justify-between text-gray-700">
                <span>Subtotal:</span>
                <span className="font-medium">${(subtotal / 100).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-700">
                <span>Tax (15%):</span>
                <span className="font-medium">${(tax / 100).toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold text-gray-900 pt-2 border-t">
                <span>Total:</span>
                <span>${(total / 100).toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Customer section */}
          <CheckoutCustomer />

          {/* Payment section */}
          {showPayment ? (
            <CheckoutPayment
              total={total}
              onCompleted={() => {
                // Receipt will be shown in a modal after payment
                clearCart()
                setShowPayment(false)
              }}
            />
          ) : (
            <>
              {/* Action buttons */}
              <div className="flex gap-3">
                <button
                  onClick={handleCancel}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => setShowPayment(true)}
                  disabled={cartItems.length === 0}
                  className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Proceed to Payment
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
