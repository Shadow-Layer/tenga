import React, { useState, useRef, useEffect } from 'react'
import { usePOSStore, useAuthStore } from '../stores'
import { useAppContextStore } from '../stores'
import { productsAPI, taxRulesAPI } from '../api'
import { calculateTaxMinorUnits, formatMinorUnits, parseMinorUnits } from '../money'
import { pendingCashSales } from '../pos/pendingCashSale'
import { getOfflineOperationQueue } from '../offline/runtime'
import type { OfflinePosCatalog } from '../offline/operationQueue'
import CheckoutLineItem from './CheckoutLineItem'
import CheckoutPayment from './CheckoutPayment'
import CheckoutCustomer from './CheckoutCustomer'

interface CheckoutProps {
  onClose?: () => void
  tillSessionId: number
}

export default function Checkout({ onClose, tillSessionId }: CheckoutProps) {
  const { cartItems, clearCart, addToCart } = usePOSStore()
  const { user } = useAuthStore()
  const { selectedTill } = useAppContextStore()
  const [showPayment, setShowPayment] = useState(false)
  const [hasUnresolvedSale, setHasUnresolvedSale] = useState(false)
  const [saleRejectionNotice, setSaleRejectionNotice] = useState('')
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [barcodeError, setBarcodeError] = useState('')
  const [lastScannedTime, setLastScannedTime] = useState(0)
  const [taxRules, setTaxRules] = useState<OfflinePosCatalog['taxRules']>([])
  const [taxRulesLoaded, setTaxRulesLoaded] = useState(false)
  const [taxRulesError, setTaxRulesError] = useState('')
  const [offlineCatalog, setOfflineCatalog] = useState<OfflinePosCatalog | null>(null)
  const [offlineCatalogNotice, setOfflineCatalogNotice] = useState('')
  const barcodeInputRef = useRef<HTMLInputElement>(null)
  const unresolvedSaleRef = useRef(false)

  useEffect(() => {
    if (!user) return
    let active = true
    pendingCashSales.has(user.id)
      .then((hasPending) => {
        if (!active) return
        unresolvedSaleRef.current = hasPending
        setHasUnresolvedSale(hasPending)
        if (hasPending) setShowPayment(true)
      })
      .catch(() => {
        if (!active) return
        unresolvedSaleRef.current = true
        setHasUnresolvedSale(true)
        setShowPayment(true)
      })
    return () => {
      active = false
    }
  }, [user?.id])

  useEffect(() => {
    if (!user) return
    const organizationId = user.organization_id
    let active = true
    async function loadCheckoutCatalog() {
      let cached: OfflinePosCatalog | undefined
      try {
        cached = await getOfflineOperationQueue().getPosCatalog(organizationId)
        if (active) setOfflineCatalog(cached ?? null)
      } catch (error) {
        if (active) setOfflineCatalogNotice(
          error instanceof Error ? error.message : 'Saved checkout data could not be read.',
        )
      }

      try {
        const [taxResponse, firstPage] = await Promise.all([
          taxRulesAPI.list(),
          productsAPI.list(organizationId, 0, 100),
        ])
        const products = [...firstPage.data.items]
        for (let skip = firstPage.data.items.length; skip < firstPage.data.total; skip += 100) {
          const page = await productsAPI.list(organizationId, skip, 100)
          products.push(...page.data.items)
        }
        const catalog: OfflinePosCatalog = {
          organizationId,
          cachedAt: Date.now(),
          products: products.map((product) => ({
            id: product.id,
            name: product.name,
            sku: product.sku,
            barcode: product.barcode ?? null,
            price: String(product.price),
            tax_rule_id: product.tax_rule_id ?? null,
          })),
          taxRules: taxResponse.data.map((rule) => ({
            id: rule.id,
            rate: String(rule.rate),
            tax_inclusive: rule.tax_inclusive,
          })),
        }
        if (!active) return
        setOfflineCatalog(catalog)
        setTaxRules(catalog.taxRules)
        setTaxRulesLoaded(true)
        setTaxRulesError('')
        try {
          await getOfflineOperationQueue().savePosCatalog(catalog)
          setOfflineCatalogNotice('')
        } catch (error) {
          setOfflineCatalogNotice(
            error instanceof Error
              ? `Checkout is online, but its catalog could not be saved for offline use: ${error.message}`
              : 'Checkout is online, but its catalog could not be saved for offline use.',
          )
        }
      } catch {
        if (!active) return
        if (cached) {
          setOfflineCatalog(cached)
          setTaxRules(cached.taxRules)
          setTaxRulesLoaded(true)
          setTaxRulesError('')
          setOfflineCatalogNotice(
            `Using checkout catalog cached ${new Date(cached.cachedAt).toLocaleString()}. Server validation is required before a sale is confirmed.`,
          )
        } else {
          setTaxRulesLoaded(false)
          setTaxRulesError('Tax rules and product details are unavailable. Connect once to load checkout data before taking a sale.')
        }
      }
    }
    void loadCheckoutCatalog()
    return () => { active = false }
  }, [user?.id, user?.organization_id])

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
    if (!barcode.trim() || unresolvedSaleRef.current) return

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
      if (!user) {
        setBarcodeError('Please sign in before scanning products')
        return
      }
      if (!taxRulesLoaded) {
        setBarcodeError(taxRulesError || 'Tax configuration is still loading')
        return
      }
      let product: {
        id: number
        name: string
        price: string | number
        tax_rule_id?: number | null
      } | undefined
      if (navigator.onLine) {
        try {
          const response = await productsAPI.search(user.organization_id, barcode)
          product = response.data.items.find((item) => item.barcode === barcode)
        } catch {
          product = offlineCatalog?.products.find((item) => item.barcode === barcode)
        }
      } else {
        product = offlineCatalog?.products.find((item) => item.barcode === barcode)
      }
      if (product) {
        if (unresolvedSaleRef.current) return
        const rule = product.tax_rule_id
          ? taxRules.find((candidate) => candidate.id === product.tax_rule_id)
          : undefined
        if (product.tax_rule_id && !rule) {
          setBarcodeError('The product tax rule is unavailable. Contact a manager.')
          return
        }
        
        // Add to cart (qty=1)
        addToCart(
          product.id,
          1,
          parseMinorUnits(product.price),
          product.name,
          rule ? String(rule.rate) : null,
          rule?.tax_inclusive ?? false,
        )
        
        // Clear input and show success feedback
        if (barcodeInputRef.current) {
          barcodeInputRef.current.value = ''
          barcodeInputRef.current.focus()
        }
      } else {
        setBarcodeError(
          navigator.onLine
            ? `Product not found: ${barcode}`
            : `Product not found in the saved offline catalog: ${barcode}`,
        )
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

  const subtotal = cartItems.reduce((sum, item) => sum + item.quantity * item.unitPrice, 0)
  const inclusiveTax = cartItems.reduce(
    (sum, item) => sum + calculateTaxMinorUnits(
      item.unitPrice * item.quantity,
      item.taxInclusive ? item.taxRate : null,
      true,
    ),
    0,
  )
  const exclusiveTax = cartItems.reduce(
    (sum, item) => sum + calculateTaxMinorUnits(
      item.unitPrice * item.quantity,
      item.taxInclusive ? null : item.taxRate,
      false,
    ),
    0,
  )
  const total = subtotal + exclusiveTax

  const handleCancel = () => {
    if (hasUnresolvedSale) return
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
            {isOnline ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>
      {!isOnline && (
        <p role="status" className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Offline cash checkout is provisional. Product and till details come from this device; the sale is not recorded until the server confirms it after reconnection.
        </p>
      )}
      {offlineCatalogNotice && (
        <p role="status" className="border-b border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {offlineCatalogNotice}
        </p>
      )}
      {saleRejectionNotice && (
        <p role="alert" className="border-b border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {saleRejectionNotice}
        </p>
      )}

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
                disabled={hasUnresolvedSale}
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
                    disabled={hasUnresolvedSale}
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
                <span className="font-medium">{formatMinorUnits(subtotal)}</span>
              </div>
              <div className="flex justify-between text-gray-700">
                <span>Tax included:</span>
                <span className="font-medium">{formatMinorUnits(inclusiveTax)}</span>
              </div>
              <div className="flex justify-between text-gray-700">
                <span>Tax added:</span>
                <span className="font-medium">{formatMinorUnits(exclusiveTax)}</span>
              </div>
              <div className="flex justify-between text-lg font-bold text-gray-900 pt-2 border-t">
                <span>Total:</span>
                <span>{formatMinorUnits(total)}</span>
              </div>
            </div>
          </div>

          {/* Customer section */}
          <CheckoutCustomer />

          {/* Payment section */}
          {showPayment ? (
            <CheckoutPayment
              total={total}
              tillSessionId={tillSessionId}
              isOnline={isOnline}
              onPending={() => {
                unresolvedSaleRef.current = true
                setHasUnresolvedSale(true)
              }}
              onCompleted={() => {
                // Receipt will be shown in a modal after payment
                unresolvedSaleRef.current = false
                setHasUnresolvedSale(false)
                setShowPayment(false)
              }}
              onRejected={() => {
                unresolvedSaleRef.current = false
                setHasUnresolvedSale(false)
                setShowPayment(false)
                setSaleRejectionNotice('The server confirmed that no sale was created. Review the cart and remove/rescan items if their prices or tax rules changed.')
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
                  disabled={cartItems.length === 0 || !taxRulesLoaded || !!taxRulesError}
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
