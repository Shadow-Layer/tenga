import React, { useEffect, useState } from 'react'
import { usePOSStore, useAuthStore, useAppContextStore } from '../stores'
import { salesAPI } from '../api'
import { formatMinorUnits, parseMinorUnits } from '../money'
import { pendingCashSales, type PendingCashSale } from '../pos/pendingCashSale'

interface CheckoutPaymentProps {
  total: number
  tillSessionId: number
  isOnline: boolean
  onCompleted?: () => void
  onPending?: () => void
  onRejected?: () => void
}

export default function CheckoutPayment({
  total,
  tillSessionId,
  isOnline,
  onCompleted,
  onPending,
  onRejected,
}: CheckoutPaymentProps) {
  const { cartItems, setIsProcessing, setError, clearCart, error } = usePOSStore()
  const { user } = useAuthStore()
  const { selectedTill } = useAppContextStore()
  const [cashAmount, setCashAmount] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [pendingSale, setPendingSale] = useState<PendingCashSale | null>(null)
  const [pendingSaleLoadError, setPendingSaleLoadError] = useState('')
  const [localSaveNotice, setLocalSaveNotice] = useState('')

  useEffect(() => {
    if (!user) {
      setPendingSale(null)
      return
    }
    let active = true
    pendingCashSales.load(user.id)
      .then((sale) => {
        if (!active) return
        setPendingSale(sale)
        setPendingSaleLoadError('')
      })
      .catch((err) => {
        if (!active) return
        setPendingSale(null)
        setPendingSaleLoadError(err instanceof Error ? err.message : 'The pending sale could not be read.')
      })
    return () => {
      active = false
    }
  }, [user?.id])

  const enteredAmount = (() => {
    if (!/^(0|[1-9]\d*)(?:\.\d{0,2})?$/.test(cashAmount) || cashAmount.endsWith('.')) {
      return 0
    }
    return parseMinorUnits(cashAmount)
  })()
  const cashChange = enteredAmount - total

  const cartMatchesPendingSale = (sale: PendingCashSale) => {
    const currentItems = usePOSStore.getState().cartItems
      .map((item) => ({
        product_id: item.productId,
        quantity: item.quantity,
        unit_price: formatMinorUnits(item.unitPrice),
        tax_rate: item.taxRate ?? '0',
        tax_inclusive: item.taxInclusive,
      }))
      .sort((left, right) => left.product_id - right.product_id)
    const savedItems = [...sale.request.items].sort((left, right) => left.product_id - right.product_id)
    return currentItems.length === savedItems.length
      && currentItems.every((item, index) =>
        item.product_id === savedItems[index].product_id
        && item.quantity === savedItems[index].quantity
        && item.unit_price === savedItems[index].unit_price
        && item.tax_rate === savedItems[index].tax_rate
        && item.tax_inclusive === savedItems[index].tax_inclusive,
      )
  }

  const submitPendingSale = async (sale: PendingCashSale) => {
    if (!user) {
      setError('Sign in as the original cashier to retry the unresolved sale.')
      return
    }
    if (!isOnline) {
      setLocalSaveNotice('Saved on this device only. The server has not confirmed this sale; retry it after reconnection.')
      return
    }
    setIsSubmitting(true)
    setIsProcessing(true)
    setError(null)

    try {
      const response = await salesAPI.create({ ...sale.request, idempotency_key: sale.idempotency_key })
      if (parseMinorUnits(String(response.data.total_amount)) !== sale.sale_total_minor) {
        throw new Error('The server sale total does not match the saved checkout total.')
      }
      await pendingCashSales.clear(user.id)
      setPendingSale(null)
      setLocalSaveNotice('')
      if (cartMatchesPendingSale(sale)) clearCart()
      onCompleted?.()
    } catch (err) {
      const responseError = err as {
        response?: {
          data?: { detail?: string }
          headers?: Record<string, unknown>
        }
      }
      const detail = responseError.response?.data?.detail
      if (responseError.response?.headers?.['x-sale-outcome'] === 'NOT_CREATED') {
        try {
          await pendingCashSales.clear(user.id)
          setPendingSale(null)
          setLocalSaveNotice('')
          onRejected?.()
          setError('The server rejected this sale before creating it. Review the cart and start a new sale.')
          return
        } catch {
          setError('The server rejected this sale, but its local recovery record could not be cleared. Do not start another sale.')
          return
        }
      }
      setError(
        detail
          ? `The sale outcome is not confirmed (${detail}). Retry this same sale before starting another.`
          : 'The sale outcome is not confirmed. Retry this same sale before starting another.',
      )
      setLocalSaveNotice('The sale remains saved on this device. Retry the exact request after the connection is restored.')
    } finally {
      setIsSubmitting(false)
      setIsProcessing(false)
    }
  }

  const handleCompleteSale = async () => {
    if (!user) {
      setError('Sign in before completing a sale.')
      return
    }
    if (pendingSaleLoadError) {
      setError(pendingSaleLoadError)
      return
    }

    let existingPendingSale: PendingCashSale | null
    try {
      existingPendingSale = await pendingCashSales.load(user.id)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'The pending sale could not be read.'
      setPendingSaleLoadError(message)
      setError(message)
      return
    }
    if (existingPendingSale) {
      setPendingSale(existingPendingSale)
      await submitPendingSale(existingPendingSale)
      return
    }

    if (!selectedTill) {
      setError('Select a till before completing a sale.')
      return
    }
    if (!tillSessionId) {
      setError('The active till session could not be verified. Reload the POS before completing this sale.')
      return
    }
    if (enteredAmount < total || cartItems.length === 0) {
      setError('Cash tendered must cover the sale total.')
      return
    }
    if (!globalThis.crypto?.randomUUID) {
      setError('A secure sale identity could not be generated. The sale was not submitted.')
      return
    }

    const sale: PendingCashSale = {
      idempotency_key: globalThis.crypto.randomUUID(),
      sale_total_minor: total,
      request: {
        till_id: selectedTill.id,
        till_session_id: tillSessionId,
        payment_method: 'CASH',
        expected_total: formatMinorUnits(total),
        amount_tendered: formatMinorUnits(enteredAmount),
        items: cartItems.map((item) => ({
          product_id: item.productId,
          quantity: item.quantity,
          unit_price: formatMinorUnits(item.unitPrice),
          tax_rate: item.taxRate ?? '0',
          tax_inclusive: item.taxInclusive,
        })),
        notes: 'Cash payment',
      },
    }

    try {
      await pendingCashSales.save(user.id, sale)
    } catch (err) {
      try {
        const concurrentlyCreatedSale = await pendingCashSales.load(user.id)
        if (concurrentlyCreatedSale) {
          setPendingSale(concurrentlyCreatedSale)
          onPending?.()
          await submitPendingSale(concurrentlyCreatedSale)
          return
        }
      } catch (loadError) {
        const message = loadError instanceof Error ? loadError.message : 'The unresolved sale could not be loaded.'
        setPendingSaleLoadError(message)
        setError(message)
        return
      }
      setError(err instanceof Error ? err.message : 'The sale could not be saved locally and was not submitted.')
      return
    }
    setPendingSale(sale)
    onPending?.()
    await submitPendingSale(sale)
  }

  const amountDue = pendingSale?.sale_total_minor ?? total
  const pendingCash = pendingSale
    ? parseMinorUnits(pendingSale.request.amount_tendered)
    : enteredAmount
  const pendingChange = pendingCash - amountDue

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Cash payment</h2>
      {pendingSaleLoadError && (
        <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {pendingSaleLoadError}
        </p>
      )}
      {error && (
        <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}
      {pendingSale && (
        <p role="status" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          This cash sale is not confirmed by the server. Retry the exact saved request for till {pendingSale.request.till_id},
          session {pendingSale.request.till_session_id}; do not start another sale until its outcome is confirmed.
        </p>
      )}
      {localSaveNotice && (
        <p role="status" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          {localSaveNotice}
        </p>
      )}
      <div className="mb-4 flex justify-between font-semibold">
        <span>Total due</span>
        <span>{formatMinorUnits(amountDue)}</span>
      </div>
      {!pendingSale && <div className="space-y-4">
        <div>
          <label htmlFor="cash-amount" className="mb-1 block text-sm font-medium text-gray-700">
            Cash received (major units)
          </label>
          <input
            id="cash-amount"
            type="number"
            min="0"
            step="0.01"
            value={cashAmount}
            onChange={(event) => setCashAmount(event.target.value)}
            placeholder="0.00"
            className="w-full rounded-lg border px-3 py-2 focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div className="flex justify-between rounded-lg border bg-gray-50 px-3 py-2">
          <span>Change</span>
          <span className={cashChange >= 0 ? 'font-semibold text-green-700' : 'font-semibold text-red-700'}>
            {formatMinorUnits(Math.max(cashChange, 0))}
          </span>
        </div>
      </div>}
      {pendingSale && (
        <div className="flex justify-between rounded-lg border bg-gray-50 px-3 py-2">
          <span>Original change</span>
          <span className="font-semibold">{formatMinorUnits(Math.max(pendingChange, 0))}</span>
        </div>
      )}
      <button
        onClick={handleCompleteSale}
        disabled={
          isSubmitting
          || !!pendingSaleLoadError
          || (!!pendingSale && !isOnline)
          || (!pendingSale && (enteredAmount < total || cartItems.length === 0))
        }
        className="mt-6 w-full rounded-lg bg-indigo-600 px-4 py-3 font-bold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting
          ? 'Processing...'
          : pendingSale
            ? isOnline
              ? `Retry unconfirmed sale — ${formatMinorUnits(amountDue)}`
              : `Saved offline — ${formatMinorUnits(amountDue)}`
            : `Complete sale — ${formatMinorUnits(total)}`}
      </button>
    </div>
  )
}
