import React, { useRef } from 'react'
import { usePOSStore, useAppContextStore, useAuthStore } from '../stores'

interface ReceiptProps {
  saleId: number
  items: Array<{ name: string; quantity: number; unitPrice: number }>
  subtotal: number
  tax: number
  total: number
  paymentMethod: string
  amountPaid: number
  customerName?: string
  onClose: () => void
}

export default function CheckoutReceipt({
  saleId,
  items,
  subtotal,
  tax,
  total,
  paymentMethod,
  amountPaid,
  customerName,
  onClose,
}: ReceiptProps) {
  const { selectedTill } = useAppContextStore()
  const { user } = useAuthStore()
  const receiptRef = useRef<HTMLDivElement>(null)
  const change = amountPaid - total

  const handlePrint = () => {
    if (!receiptRef.current) return
    const printWindow = window.open('', '', 'height=600,width=800')
    if (printWindow) {
      printWindow.document.write(receiptRef.current.innerHTML)
      printWindow.document.close()
      printWindow.print()
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-lg w-full mx-4 max-h-96 overflow-y-auto">
        {/* Receipt content */}
        <div
          ref={receiptRef}
          className="p-8 font-mono text-sm bg-white"
          style={{ width: '80mm' }}
        >
          {/* Header */}
          <div className="text-center mb-4 pb-4 border-b border-gray-800">
            <p className="font-bold text-lg">{selectedTill?.name || 'TILL'}</p>
            <p className="text-xs">
              {new Date().toLocaleDateString()} {new Date().toLocaleTimeString()}
            </p>
            <p className="text-xs mt-1">Receipt #{saleId}</p>
          </div>

          {/* Line items */}
          <div className="mb-4 pb-4 border-b border-gray-800">
            <div className="grid grid-cols-12 gap-1 text-xs mb-2">
              <div className="col-span-6">PRODUCT</div>
              <div className="col-span-2 text-right">QTY</div>
              <div className="col-span-2 text-right">PRICE</div>
              <div className="col-span-2 text-right">TOTAL</div>
            </div>
            <div className="border-b border-gray-300 mb-2" />
            {items.map((item, idx) => (
              <div key={idx} className="grid grid-cols-12 gap-1 text-xs mb-1">
                <div className="col-span-6 truncate">{item.name}</div>
                <div className="col-span-2 text-right">{item.quantity}</div>
                <div className="col-span-2 text-right">
                  ${(item.unitPrice / 100).toFixed(2)}
                </div>
                <div className="col-span-2 text-right font-semibold">
                  ${((item.quantity * item.unitPrice) / 100).toFixed(2)}
                </div>
              </div>
            ))}
          </div>

          {/* Totals */}
          <div className="mb-4 pb-4 border-b border-gray-800 space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Subtotal:</span>
              <span>${(subtotal / 100).toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Tax (15%):</span>
              <span>${(tax / 100).toFixed(2)}</span>
            </div>
            <div className="flex justify-between font-bold text-base pt-2">
              <span>TOTAL:</span>
              <span>${(total / 100).toFixed(2)}</span>
            </div>
          </div>

          {/* Payment info */}
          <div className="mb-4 pb-4 border-b border-gray-800 space-y-1 text-sm">
            <div className="flex justify-between">
              <span>Payment:</span>
              <span className="font-semibold">{paymentMethod}</span>
            </div>
            <div className="flex justify-between">
              <span>Amount Tendered:</span>
              <span>${(amountPaid / 100).toFixed(2)}</span>
            </div>
            {change > 0 && (
              <div className="flex justify-between font-semibold text-green-600">
                <span>Change:</span>
                <span>${(change / 100).toFixed(2)}</span>
              </div>
            )}
          </div>

          {/* Customer info */}
          {customerName && (
            <div className="mb-4 pb-4 border-b border-gray-800 text-sm">
              <p>Customer: {customerName}</p>
            </div>
          )}

          {/* Fiscal status */}
          <div className="mb-4 pb-4 border-b border-gray-800 text-sm">
            <p className="text-center">
              Fiscal #: <span className="font-semibold">pending</span>
            </p>
          </div>

          {/* Footer */}
          <div className="text-center text-xs space-y-1">
            <p className="font-semibold">Thank you for your purchase</p>
            <p>Return within 30 days with receipt</p>
            <div className="mt-3 h-16 bg-gray-100 flex items-center justify-center text-xs text-gray-500">
              [QR Code: {saleId}]
            </div>
          </div>

          {/* Cashier info */}
          <div className="text-center text-xs mt-4 pt-4 border-t border-gray-800">
            <p>Cashier: {user?.username || 'N/A'}</p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="bg-gray-50 border-t p-4 flex gap-3">
          <button
            onClick={handlePrint}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
          >
            Print
          </button>
          <button
            onClick={() => {
              // Email functionality would go here
              alert('Email feature not yet implemented')
            }}
            disabled
            className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-lg cursor-not-allowed font-medium"
          >
            Email
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
