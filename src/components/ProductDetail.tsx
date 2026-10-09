import React, { useState } from 'react'
import { ChevronLeft, Edit, Trash2, MoreVertical, Copy, AlertCircle } from 'lucide-react'

/**
 * Product Detail Screen
 * 
 * Shows comprehensive product information:
 * - Product name, SKU, category, pricing
 * - Current stock at selected location
 * - Stock history timeline
 * - Quick actions (edit, adjust, delete)
 * 
 * Interaction: View-only by default. Edit mode triggered by Edit button.
 */

interface StockEvent {
  id: number
  type: 'sale' | 'adjustment' | 'count' | 'return'
  quantity: number
  reason?: string
  user: string
  timestamp: string
}

const mockStockHistory: StockEvent[] = [
  {
    id: 1,
    type: 'sale',
    quantity: -2,
    user: 'John Cashier',
    timestamp: '2 hours ago',
  },
  {
    id: 2,
    type: 'adjustment',
    quantity: 10,
    reason: 'Manual restock',
    user: 'Manager Alice',
    timestamp: '1 day ago',
  },
  {
    id: 3,
    type: 'count',
    quantity: 0,
    reason: 'Physical count',
    user: 'Manager Alice',
    timestamp: '3 days ago',
  },
  {
    id: 4,
    type: 'sale',
    quantity: -5,
    user: 'Jane Cashier',
    timestamp: '5 days ago',
  },
]

function EventTypeIcon({ type }: { type: string }) {
  switch (type) {
    case 'sale':
      return <span className="text-blue-600">🛒</span>
    case 'adjustment':
      return <span className="text-purple-600">📝</span>
    case 'count':
      return <span className="text-orange-600">📊</span>
    case 'return':
      return <span className="text-green-600">↩️</span>
    default:
      return null
  }
}

export function ProductDetail() {
  const [isEditing, setIsEditing] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  const product = {
    id: 1,
    name: 'Premium Coffee',
    sku: 'COFFEE-001',
    category: 'Beverages',
    description: 'Single-origin arabica beans from Ethiopia',
    price: 450,
    cost: 200,
    stock: 15,
    reorderPoint: 5,
    barcode: '8472015928344',
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header with Back button */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3 mb-4">
            <button className="p-1.5 rounded-lg hover:bg-gray-100 transition">
              <ChevronLeft size={20} className="text-gray-600" />
            </button>
            <h1 className="text-2xl font-bold text-gray-900">Product Details</h1>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm"
            >
              <Edit size={16} />
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm">
              <Copy size={16} />
              Duplicate
            </button>
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-red-700 rounded-lg hover:bg-red-50 transition font-medium text-sm"
            >
              <Trash2 size={16} />
            </button>
          </div>
        </div>
      </div>

      {isEditing ? (
        <ProductEditForm product={product} onSave={() => setIsEditing(false)} />
      ) : (
        <>
          {/* Product Information Card */}
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left column */}
                <div>
                  <h2 className="text-xl font-bold text-gray-900 mb-4">{product.name}</h2>
                  <div className="space-y-4">
                    <div>
                      <p className="text-sm text-gray-600 font-medium uppercase tracking-wide mb-1">SKU</p>
                      <p className="text-base font-mono text-gray-900">{product.sku}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium uppercase tracking-wide mb-1">Barcode</p>
                      <p className="text-base font-mono text-gray-900">{product.barcode}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium uppercase tracking-wide mb-1">Category</p>
                      <p className="text-base text-gray-900">{product.category}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 font-medium uppercase tracking-wide mb-1">Description</p>
                      <p className="text-base text-gray-700">{product.description}</p>
                    </div>
                  </div>
                </div>

                {/* Right column - Pricing & Stock */}
                <div>
                  <div className="bg-blue-50 rounded-lg p-4 mb-4 border border-blue-200">
                    <p className="text-sm text-blue-600 font-medium uppercase tracking-wide mb-2">Selling Price</p>
                    <p className="text-3xl font-bold text-blue-700">{product.price} ZWD</p>
                    <p className="text-xs text-blue-600 mt-1">Gross margin: {Math.round((product.price - product.cost) / product.price * 100)}%</p>
                  </div>

                  <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                    <p className="text-sm text-gray-600 font-medium uppercase tracking-wide mb-1">Cost Price</p>
                    <p className="text-2xl font-bold text-gray-900">{product.cost} ZWD</p>
                  </div>

                  <div className="mt-4 bg-green-50 rounded-lg p-4 border border-green-200">
                    <p className="text-sm text-green-600 font-medium uppercase tracking-wide mb-1">Current Stock</p>
                    <p className="text-3xl font-bold text-green-700">{product.stock}</p>
                    <p className="text-xs text-green-600 mt-1">Reorder at: {product.reorderPoint}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Stock History */}
          <div className="max-w-4xl mx-auto px-4 pb-8">
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">Stock History</h3>
              <div className="space-y-3">
                {mockStockHistory.map((event) => (
                  <div key={event.id} className="flex items-start gap-3 pb-3 border-b border-gray-200 last:border-b-0">
                    <div className="mt-1 text-lg">
                      <EventTypeIcon type={event.type} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900 capitalize">
                          {event.type === 'sale' ? 'Sale' : event.type === 'adjustment' ? 'Adjustment' : event.type === 'count' ? 'Stock Count' : 'Return'}
                        </p>
                        <span className={`text-sm font-bold ${event.quantity < 0 ? 'text-red-600' : 'text-green-600'}`}>
                          {event.quantity > 0 ? '+' : ''}{event.quantity}
                        </span>
                      </div>
                      {event.reason && <p className="text-xs text-gray-500 mt-0.5">{event.reason}</p>}
                      <p className="text-xs text-gray-500 mt-1">
                        {event.user} • {event.timestamp}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Delete Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-sm">
            <div className="flex items-center gap-3 mb-4">
              <AlertCircle size={24} className="text-red-600" />
              <h3 className="text-lg font-bold text-gray-900">Delete Product</h3>
            </div>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete <strong>{product.name}</strong>? This action cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 transition font-medium"
              >
                Cancel
              </button>
              <button className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ProductEditForm({ product, onSave }: { product: any; onSave: () => void }) {
  const [formData, setFormData] = useState(product)

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-6">Edit Product</h3>
        <form className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Product Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">SKU *</label>
              <input
                type="text"
                value={formData.sku}
                onChange={(e) => setFormData({ ...formData, sku: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Barcode</label>
              <input
                type="text"
                value={formData.barcode}
                onChange={(e) => setFormData({ ...formData, barcode: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Selling Price (ZWD) *</label>
              <input
                type="number"
                value={formData.price}
                onChange={(e) => setFormData({ ...formData, price: Number(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Cost Price (ZWD) *</label>
              <input
                type="number"
                value={formData.cost}
                onChange={(e) => setFormData({ ...formData, cost: Number(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onSave}
              className="flex-1 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium"
            >
              Cancel
            </button>
            <button type="submit" className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default ProductDetail
