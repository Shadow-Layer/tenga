import React, { useState, useEffect, useRef } from 'react'
import { ChevronDown, Search, Plus, AlertCircle, TrendingDown, Package, Eye } from 'lucide-react'
import { useAuthStore } from '../stores'
import { productsAPI_v2 } from '../api'

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
  category?: string
  price: number
  cost?: number
  description?: string
  organization_id: number
}

interface DisplayProduct extends Product {
  stock: number
  status: 'available' | 'low' | 'out'
  lastUpdated: string
}

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
  const token = useAuthStore((state) => state.token)
  const user = useAuthStore((state) => state.user)
  
  const [selectedLocation, setSelectedLocation] = useState('Downtown Store')
  const [searchQuery, setSearchQuery] = useState('')
  const [products, setProducts] = useState<DisplayProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [limit] = useState(10)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const filteredProducts = products.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.sku.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  // Fetch products from API
  useEffect(() => {
    if (!token || !user) {
      setError('Not authenticated')
      setLoading(false)
      return
    }

    const fetchProducts = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await productsAPI_v2.list({
          skip,
          limit,
          search: searchQuery || undefined,
          organization_id: user.organization_id,
        })
        
        const apiProducts: DisplayProduct[] = (response.data.data || []).map((p: Product) => ({
          ...p,
          stock: Math.floor(Math.random() * 20), // Mock stock for display
          status: (Math.random() > 0.6 ? 'low' : Math.random() > 0.3 ? 'available' : 'out') as 'available' | 'low' | 'out',
          lastUpdated: 'Just now',
        }))
        
        setProducts(apiProducts)
        setTotal(response.data.total || apiProducts.length)
      } catch (err: any) {
        if (err.response?.status === 401) {
          setError('Session expired. Please log in again.')
        } else if (err.response?.status === 403) {
          setError('Access denied')
        } else if (err.response?.status === 404) {
          setError('Products not found')
        } else if (err.response?.status === 500) {
          setError('Server error. Please try again.')
        } else {
          setError('Failed to load products')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchProducts()
  }, [token, user, skip, searchQuery])

  const handleSearchChange = (query: string) => {
    setSearchQuery(query)
    setSkip(0) // Reset pagination on search
    
    // Debounce search requests
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">Inventory</h1>
            <div className="text-sm text-gray-500">
              {loading ? 'Loading...' : 'Ready'}
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

      {/* Error Banner */}
      {error && (
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle size={20} className="text-red-600" />
            <p className="text-sm font-medium text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Summary Cards */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg border border-gray-200 p-4">
            <p className="text-sm text-gray-600 mb-1">Total Products</p>
            <p className="text-3xl font-bold text-gray-900">{loading ? '—' : total}</p>
          </div>
          <div className="bg-white rounded-lg border border-yellow-200 bg-yellow-50 p-4">
            <p className="text-sm text-yellow-700 font-medium mb-1">⚠ Low Stock</p>
            <p className="text-3xl font-bold text-yellow-700">{loading ? '—' : products.filter((p) => p.status === 'low').length}</p>
          </div>
          <div className="bg-white rounded-lg border border-red-200 bg-red-50 p-4">
            <p className="text-sm text-red-700 font-medium mb-1">🚫 Out of Stock</p>
            <p className="text-3xl font-bold text-red-700">{loading ? '—' : products.filter((p) => p.status === 'out').length}</p>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex gap-3 flex-wrap sm:flex-nowrap">
          <button className="flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium text-sm h-12 flex-1 sm:flex-initial">
            <Plus size={18} />
            <span className="hidden sm:inline">Add Product</span>
            <span className="sm:hidden">Add</span>
          </button>
          <button className="flex items-center justify-center gap-2 px-4 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm h-12 flex-1 sm:flex-initial">
            Count Stock
          </button>
          <button className="flex items-center justify-center gap-2 px-4 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium text-sm h-12 flex-1 sm:flex-initial">
            Import CSV
          </button>
        </div>
      </div>

      {/* Search & Filter */}
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="relative">
         <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search by product name or SKU..."
            value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
           className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent h-12"
          />
        </div>
      </div>

      {/* Product List */}
      <div className="max-w-6xl mx-auto px-4 pb-8">
        {loading ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <p className="text-gray-600 font-medium">Loading products...</p>
          </div>
        ) : filteredProducts.length === 0 ? (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <Package size={48} className="mx-auto text-gray-300 mb-4" />
            <p className="text-gray-600 font-medium">
              {searchQuery ? 'No products match your search' : 'No products found'}
            </p>
            <p className="text-gray-500 text-sm mt-1">
              {searchQuery ? 'Try a different search term or add a new product.' : 'Get started by adding your first product.'}
            </p>
          </div>
        ) : (
          <>
           {/* Desktop Table View (hidden on tablet/mobile) */}
           <div className="hidden md:block bg-white rounded-lg border border-gray-200 overflow-hidden">
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
                       <td className="px-4 py-3 text-sm text-gray-600">{product.category || '—'}</td>
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

           {/* Mobile/Tablet Card View (visible on small screens) */}
           <div className="md:hidden space-y-3">
             {filteredProducts.map((product) => (
               <div key={product.id} className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
                 <div className="flex items-start justify-between gap-2">
                   <div className="flex-1">
                     <h3 className="font-medium text-gray-900 text-sm">{product.name}</h3>
                     <p className="text-xs text-gray-500 font-mono mt-0.5">{product.sku}</p>
                   </div>
                   <StatusBadge status={product.status} />
                 </div>
                 <div className="grid grid-cols-2 gap-2 text-xs">
                   <div>
                     <p className="text-gray-500">Price</p>
                     <p className="font-semibold text-gray-900">{product.price} ZWD</p>
                   </div>
                   <div>
                     <p className="text-gray-500">Stock</p>
                     <p className="font-semibold text-gray-900">{product.stock} units</p>
                   </div>
                   {product.category && (
                     <div>
                       <p className="text-gray-500">Category</p>
                       <p className="font-semibold text-gray-900">{product.category}</p>
                     </div>
                   )}
                   <div>
                     <p className="text-gray-500">Updated</p>
                     <p className="font-semibold text-gray-900">{product.lastUpdated}</p>
                   </div>
                 </div>
                 <button className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-blue-300 text-blue-600 hover:bg-blue-50 transition font-medium text-sm h-10">
                   <Eye size={16} />
                   View Details
                 </button>
               </div>
             ))}
           </div>

           {/* Pagination */}
           <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
             <p className="text-sm text-gray-600">
               Page {Math.floor(skip / limit) + 1} of {Math.ceil(total / limit)}
             </p>
             <div className="flex gap-2 w-full sm:w-auto">
               <button
                 onClick={() => setSkip(Math.max(0, skip - limit))}
                 disabled={skip === 0}
                 className="flex-1 sm:flex-initial px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition font-medium text-sm h-12"
               >
                 Previous
               </button>
               <button
                 onClick={() => setSkip(skip + limit)}
                 disabled={skip + limit >= total}
                 className="flex-1 sm:flex-initial px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition font-medium text-sm h-12"
               >
                 Next
               </button>
             </div>
           </div>
         </>
       )}
      </div>
    </div>
  )
}

export default InventoryOverview
