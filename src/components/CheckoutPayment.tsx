import React, { useState, useEffect } from 'react'
import { usePOSStore, useAuthStore, useAppContextStore } from '../stores'
import { salesAPI } from '../api'

interface CheckoutPaymentProps {
  total: number
  onCompleted?: () => void
}

type PaymentMethod = 'cash' | 'card' | 'mobile'

export default function CheckoutPayment({ total, onCompleted }: CheckoutPaymentProps) {
  const { cartItems, setIsProcessing, setError, clearCart } = usePOSStore()
  const { user } = useAuthStore()
  const { selectedTill } = useAppContextStore()
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>('cash')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Cash payment state
  const [cashAmount, setCashAmount] = useState('')

  // Card payment state
  const [cardNumber, setCardNumber] = useState('')
  const [cardholderName, setCardholderName] = useState('')
  const [cardExpiry, setCardExpiry] = useState('')

  // Mobile money state
  const [phoneNumber, setPhoneNumber] = useState('')
  const [mobileOperator, setMobileOperator] = useState('econet')

  const cashChange = parseFloat(cashAmount || '0') * 100 - total
  const isValidPayment = getIsValidPayment()

  function getIsValidPayment(): boolean {
    switch (paymentMethod) {
      case 'cash':
        return parseFloat(cashAmount || '0') * 100 >= total && parseFloat(cashAmount || '0') > 0
      case 'card':
        return (
          cardNumber.length >= 13 &&
          cardholderName.trim().length > 0 &&
          !!cardExpiry.match(/^\d{2}\/\d{2}$/)
        )
      case 'mobile':
        return phoneNumber.trim().length >= 10 && mobileOperator.length > 0
      default:
        return false
    }
  }

  const handleCompleteSale = async () => {
    if (!user || !selectedTill) {
      setError('Missing user or till information')
      return
    }

    if (!isValidPayment) {
      setError('Invalid payment information')
      return
    }

    setIsSubmitting(true)
    setIsProcessing(true)

    try {
      const salePayload = {
        till_id: selectedTill.id,
        cashier_id: user.id,
        payment_method: paymentMethod.toUpperCase(),
        items: cartItems.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
          unit_price: item.unitPrice,
        })),
        is_offline: false,
        notes: `Payment via ${paymentMethod}`,
      }

      const response = await salesAPI.create(salePayload)

      // Mock payment success (in real system, would process payment)
      await new Promise((resolve) => setTimeout(resolve, 500))

      // Show receipt (in T5, this will be a proper receipt modal)
      console.log('Sale completed:', response.data)
      
      // Success feedback
      alert(`Sale completed! Sale ID: ${response.data.id}`)
      clearCart()
      
      if (onCompleted) {
        onCompleted()
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to complete sale')
    } finally {
      setIsSubmitting(false)
      setIsProcessing(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Payment</h2>

      {/* Payment method tabs */}
      <div className="flex gap-2 mb-6 border-b">
        {(['cash', 'card', 'mobile'] as const).map((method) => (
          <button
            key={method}
            onClick={() => setPaymentMethod(method)}
            className={`px-4 py-2 font-medium border-b-2 transition-colors ${
              paymentMethod === method
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            {method === 'cash' ? 'Cash' : method === 'card' ? 'Card' : 'Mobile Money'}
          </button>
        ))}
      </div>

      {/* Cash tab */}
      {paymentMethod === 'cash' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Amount Paid
            </label>
            <input
              type="number"
              step="0.01"
              value={cashAmount}
              onChange={(e) => setCashAmount(e.target.value)}
              placeholder="0.00"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Change
            </label>
            <div className={`px-3 py-2 border rounded-lg text-right font-semibold ${
              cashChange > 0 ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'
            }`}>
              ${(cashChange / 100).toFixed(2)}
            </div>
          </div>
        </div>
      )}

      {/* Card tab */}
      {paymentMethod === 'card' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Card Number
            </label>
            <input
              type="text"
              value={cardNumber}
              onChange={(e) => setCardNumber(e.target.value.replace(/\D/g, '').slice(0, 19))}
              placeholder="1234 5678 9012 3456"
              maxLength={19}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 font-mono"
            />
            {cardNumber && (
              <p className="text-xs text-gray-600 mt-1">
                ••••••••••••{cardNumber.slice(-4)}
              </p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Cardholder Name
            </label>
            <input
              type="text"
              value={cardholderName}
              onChange={(e) => setCardholderName(e.target.value)}
              placeholder="John Doe"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Expiry (MM/YY)
            </label>
            <input
              type="text"
              value={cardExpiry}
              onChange={(e) => {
                let val = e.target.value.replace(/\D/g, '')
                if (val.length >= 2) {
                  val = val.slice(0, 2) + '/' + val.slice(2, 4)
                }
                setCardExpiry(val)
              }}
              placeholder="MM/YY"
              maxLength={5}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
      )}

      {/* Mobile Money tab */}
      {paymentMethod === 'mobile' && (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Phone Number
            </label>
            <input
              type="tel"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="+263712345678"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Operator
            </label>
            <select
              value={mobileOperator}
              onChange={(e) => setMobileOperator(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              <option value="econet">Econet</option>
              <option value="telecash">Telecash</option>
              <option value="zipit">ZipIt</option>
              <option value="oneash">OneASH</option>
            </select>
          </div>
        </div>
      )}

      {/* Complete sale button */}
      <button
        onClick={handleCompleteSale}
        disabled={!isValidPayment || isSubmitting}
        className="w-full mt-6 px-4 py-3 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isSubmitting ? 'Processing...' : `Complete Sale - ${(total / 100).toFixed(2)} ZWL`}
      </button>
    </div>
  )
}
