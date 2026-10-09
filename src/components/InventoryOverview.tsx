import React, { useState } from 'react'
import { ChevronDown, Search, Plus, AlertCircle, TrendingDown, Package, Eye } from 'lucide-react'

/**
 * Inventory Overview Screen
 * 
 * Primary entry point for inventory management.
 * Shows:
 * - Location selector
 * - Summary stats (total products, low stock, out of stock)
 * - Quick actions (add product, count stock, import)
 * - Product list with search and filter
 * 
 * Design principle: Simple, at-a-glance view. No administrative complexity exposed.
 */

interface Product {
  id: number
  name: string
  sku: string
  category: string
  price: number
  stock: number
  status: 'available' | 'low' | 'out'
  lastUpdated: string
}

const mockProducts: Product[] = [
  {
    id: 1,
    name: 'Premium Coffee',
    sku: 'COFFEE-001',
    category: 'Beverages',
    price: 450,
    stock: 15,
    status: 'available',
    lastUpdated: '2 hours ago',
  },
  {
    id: 2,
    name: 'Black Tea',
    sku: 'TEA-001',
    category: 'Beverages',
    price: 250,
    stock: 3,
    status: 'low',
    lastUpdated: 'Just now',
  },
  {
    id: 3,
    name: 'Herbal Tea Mix',
    sku: 'TEA-002',
    category: 'Beverages',
    price: 300,
    stock: 0,
    status: 'out',
    lastUpdated: '30 min ago',
  },
]

function StatusBadge({ status }: { status: 'available' | 'low' | 'out' }) {
  const colors = {
    available: 'bg-green-50 text-green-700 border-green-200',
    low: 'bg-yellow-50 text-yellow-700 border-yellow-200',
    out: 'bg-red-50 text-red-700 border-red-200',
  }

  const labels = {
    available: 'In Stock',
    low: 'Low Stock',
    out: 'Out of Stock',
  }

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors[status]}`}>
      {status === 'out' && <AlertCircle size={12} />}
      {status === 'low' && <TrendingDown size={12} />}
      {labels[status]}
    </span>
  )
}

export function InventoryOverview() {
  const [selectedLocation, setSelectedLocation] = useState('Downtown Store')
  const [searchQuery, setSearchQuery] = useState('')
  const [products, setProducts] = useState(mockProducts)

  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.sku.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const stats = {
    total: products.length,
    lowStock: products.filter((p) => p.status === 'low').length,
    outOfStock: products.filter((p) => p.status === 'out').length,
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
            <div className="text-sm text-gray-500">
              Synced • 2 min ago
            </div>
          </div>

          {/* Location Selector */}
          <div className="flex gap-2 items-center">
            <label className="text-sm font-medium text-gray-700">Location:</label>
            <button className="flex items-center gap-2 px-3 py-2 bg-white border border-gray-300 rounded-md hover:border-gray-400 transition">
              <Package size={16} className="text-gray-600" />
              <span className="text-sm font-medium">{selectedLocation}</span>
              <ChevronDown size={16} className="text-gray-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-sm text-gray-600 mb-1">Total Products</p>
            <p className="text-3xl font-bold text-gray-900">{stats.total}</p>
          </div>
          <div className="bg-white rounded-lg border border-yellow-200 bg-yellow-50 p-4">
            <p className="text-sm text-yellow-700 font-medium mb-1">⚠ Low Stock</p>
            <p className="text-3xl font-bold text-yellow-700">{stats.lowStock}</p>
          </div>
          <div className="bg-white rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700 font-medium mb-1">🚫 Out of Stock</p>
            <p className="text-3xl font-bold text-red-700">{stats.outOfStock}</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex gap-3">
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium text-sm">
            <Plus size={18} />
            Add Product
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm">
            Count Stock
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm">
            Import CSV
          </button>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="relative">
          <Search className="absolute left-3 top-3 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search by product name or SKU..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Product List */}
      <div className="max-w-6xl mx-auto px-4 pb-8">
        {filteredProducts.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Package size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-600 font-medium">No products found</p>
            <p className="text-gray-500 text-sm mt-1">Try a different search or add a new product.</p>
          </div>
        ) : (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Product</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">SKU</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Category</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-gray-900">Price</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-900">Stock</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-900">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Last Updated</th>
                    <th className="px-4 py-3 text-center text-sm font-semibold text-gray-900">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredProducts.map((product) => (
                    <tr key={product.id} className="border-b border-gray-200 hover:bg-gray-50 transition">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{product.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600 font-mono">{product.sku}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{product.category}</td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-right">{product.price} ZWD</td>
                      <td className="px-4 py-3 text-sm font-bold text-center text-gray-900">{product.stock}</td>
                      <td className="px-4 py-3 text-center">
                        <StatusBadge status={product.status} />
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{product.lastUpdated}</td>
                      <td className="px-4 py-3 text-center">
                        <button className="inline-flex items-center gap-1 px-3 py-1.5 rounded hover:bg-gray-100 transition">
                          <Eye size={16} className="text-gray-600" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default InventoryOverview
