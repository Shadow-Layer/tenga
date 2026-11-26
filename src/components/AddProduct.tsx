import React, { useEffect, useState } from 'react'
import { ChevronLeft } from 'lucide-react'
import { useAuthStore } from '../stores'
import { productsAPI_v2, taxRulesAPI, type TaxRule } from '../api'

/**
 * Add/Edit Product Screen
 * 
 * Form for creating or updating products.
 * Fields:
 * - Basic info: Name, SKU, category, description
 * - Pricing: Selling price, cost price
 * - Barcode: For scanning (optional)
 * 
 * Validation: SKU must be unique. Prices required.
 * Success: Redirects to product detail or inventory list.
 */

interface ProductFormData {
  name: string
  sku: string
  category: string
  description: string
  price: number | ''
  cost: number | ''
  barcode: string
  unit_of_measure: string
  minimum_stock_level: number | ''
  tax_rule_id: number | ''
}

const initialFormData: ProductFormData = {
  name: '',
  sku: '',
  category: '',
  description: '',
  price: '',
  cost: '',
  barcode: '',
  unit_of_measure: 'each',
  minimum_stock_level: 0,
  tax_rule_id: '',
}

const categories = [
  'Beverages',
  'Snacks',
  'Groceries',
  'Electronics',
  'Clothing',
  'Health & Beauty',
  'Home & Garden',
  'Other',
]

type Props = {
  onCancel?: () => void
  onCreated?: () => void
}

export function AddProduct({ onCancel, onCreated }: Props) {
  const user = useAuthStore((state) => state.user)
  
  const [formData, setFormData] = useState<ProductFormData>(initialFormData)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [lastSubmitTime, setLastSubmitTime] = useState(0)
  const [taxRules, setTaxRules] = useState<TaxRule[]>([])

  useEffect(() => {
    taxRulesAPI.list()
      .then((response) => setTaxRules(response.data))
      .catch(() => setError('Tax rules could not be loaded. Product tax will remain unassigned.'))
  }, [])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]:
        name === 'price' || name === 'cost' || name === 'tax_rule_id' || name === 'minimum_stock_level'
          ? value
            ? Number(value)
            : ''
          : value,
    }))
    if (errors[name]) {
      setErrors((prev) => ({ ...prev, [name]: '' }))
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) newErrors.name = 'Product name is required'
    if (!formData.sku.trim()) newErrors.sku = 'SKU is required'
    if (formData.price === '' || formData.price <= 0) newErrors.price = 'Selling price must be greater than zero'
    if (formData.cost !== '' && formData.cost < 0) newErrors.cost = 'Cost price cannot be negative'
    if (!formData.unit_of_measure.trim() || formData.unit_of_measure.trim().length > 50) {
      newErrors.unit_of_measure = 'Unit of measure is required (maximum 50 characters)'
    }
    if (
      formData.minimum_stock_level === ''
      || !Number.isInteger(formData.minimum_stock_level)
      || formData.minimum_stock_level < 0
    ) {
      newErrors.minimum_stock_level = 'Minimum stock level must be a whole non-negative number'
    }
    if (formData.price !== '' && formData.cost !== '' && formData.price < formData.cost) {
      newErrors.price = 'Selling price must be greater than cost price'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    // Prevent duplicate submissions
    const now = Date.now()
    if (now - lastSubmitTime < 1000) return
    setLastSubmitTime(now)

    if (!user) {
      setError('Authentication required. Please log in.')
      return
    }

    setLoading(true)
    setError(null)

    try {
      await productsAPI_v2.create({
        sku: formData.sku,
        name: formData.name,
        price: formData.price as number,
        cost: formData.cost === '' ? undefined : formData.cost,
        barcode: formData.barcode || undefined,
        unit_of_measure: formData.unit_of_measure.trim(),
        minimum_stock_level: formData.minimum_stock_level as number,
        description: formData.description || undefined,
        category: formData.category || undefined,
        organization_id: user.organization_id,
        tax_rule_id: formData.tax_rule_id || null,
      })

      setSuccess(true)
      if (onCreated) {
        onCreated()
      } else {
        setTimeout(() => {
        setFormData(initialFormData)
        setSuccess(false)
        }, 3000)
      }
    } catch (err: any) {
      const status = err.response?.status
      const errorData = err.response?.data

      if (status === 400) {
        if (errorData.detail && typeof errorData.detail === 'object') {
          setErrors(errorData.detail)
        } else {
          setError(errorData.detail || 'Invalid input. Please check your values.')
        }
      } else if (status === 409) {
        setError('Product with this SKU already exists.')
      } else if (status === 403) {
        setError('Access denied. You do not have permission.')
      } else if (status === 500) {
        setError('Failed to create product. Please try again.')
      } else {
        setError(errorData?.detail || 'An error occurred. Please try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const margin = formData.price !== '' && formData.cost !== '' ? Math.round(((formData.price - formData.cost) / formData.price) * 100) : 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <button type="button" onClick={onCancel} aria-label="Back to inventory" className="p-1.5 rounded-lg hover:bg-gray-100 transition">
              <ChevronLeft size={20} className="text-gray-600" />
            </button>
            <h1 className="text-2xl font-bold text-gray-900">Add New Product</h1>
          </div>
        </div>
      </div>

      {/* Form Container */}
      <div className="max-w-3xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <span className="text-red-600 text-lg">⚠</span>
            <div>
              <p className="text-sm font-medium text-red-700">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center gap-3">
            <span className="text-green-600 text-lg">✓</span>
            <div>
              <p className="text-sm font-medium text-green-700">Product created successfully</p>
              <p className="text-xs text-green-600 mt-0.5">Redirecting...</p>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Basic Information Section */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-6">Basic Information</h2>
            <div className="space-y-5">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-900 mb-2">
                  Product Name *
                </label>
               <input
                  id="name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  placeholder="E.g., Premium Coffee"
                  className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 h-12 text-base ${
                    errors.name ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                  }`}
                />
                {errors.name && <p className="text-sm text-red-600 mt-1">{errors.name}</p>}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="sku" className="block text-sm font-medium text-gray-900 mb-2">
                    SKU *
                  </label>
                  <input
                    id="sku"
                    type="text"
                    name="sku"
                    value={formData.sku}
                    onChange={handleChange}
                    placeholder="E.g., COFFEE-001"
                   className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 font-mono h-12 text-base ${
                      errors.sku ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                  {errors.sku && <p className="text-sm text-red-600 mt-1">{errors.sku}</p>}
                </div>

                <div>
                  <label htmlFor="category" className="block text-sm font-medium text-gray-900 mb-2">
                    Category
                  </label>
                  <select
                    id="category"
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 h-12 text-base"
                  >
                    <option value="">— Select category —</option>
                    {categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label htmlFor="description" className="block text-sm font-medium text-gray-900 mb-2">
                  Description
                </label>
                 <textarea
                  id="description"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  placeholder="Product details, origin, ingredients, etc."
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
                />
              </div>
            </div>
          </div>

          {/* Pricing Section */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-6">Pricing</h2>
            <div className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="price" className="block text-sm font-medium text-gray-900 mb-2">
                    Selling Price (major units) *
                  </label>
                  <input
                    id="price"
                    type="number"
                    name="price"
                    value={formData.price}
                    onChange={handleChange}
                    placeholder="0"
                    min="0.01"
                    step="0.01"
                   className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 h-12 text-base ${
                      errors.price ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                  {errors.price && <p className="text-sm text-red-600 mt-1">{errors.price}</p>}
                </div>

                <div>
                  <label htmlFor="cost" className="block text-sm font-medium text-gray-900 mb-2">
                    Cost Price (major units)
                  </label>
                  <input
                    id="cost"
                    type="number"
                    name="cost"
                    value={formData.cost}
                    onChange={handleChange}
                    placeholder="0"
                    min="0"
                    step="0.01"
                   className={`w-full px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 h-12 text-base ${
                      errors.cost ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 focus:ring-blue-500'
                    }`}
                  />
                  {errors.cost && <p className="text-sm text-red-600 mt-1">{errors.cost}</p>}
                </div>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h2 className="text-lg font-bold text-gray-900 mb-2">Tax</h2>
                <label htmlFor="tax_rule_id" className="block text-sm font-medium text-gray-900 mb-2">
                  Product tax rule
                </label>
                <select
                  id="tax_rule_id"
                  name="tax_rule_id"
                  value={formData.tax_rule_id}
                  onChange={handleChange}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg"
                >
                  <option value="">No tax rule (tax omitted)</option>
                  {taxRules.map((rule) => (
                    <option key={rule.id} value={rule.id}>
                      {rule.name} — {rule.rate}% {rule.tax_inclusive ? 'inclusive' : 'exclusive'}
                    </option>
                  ))}
                </select>
              </div>

              {formData.price !== '' && formData.cost !== '' && (
                <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-600 font-medium mb-1">Gross Margin</p>
                  <p className="text-2xl font-bold text-blue-700">{margin}%</p>
                </div>
              )}
            </div>
          </div>

          {/* Inventory Section */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-6">Inventory</h2>
            <div className="space-y-5">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="unit_of_measure" className="block text-sm font-medium text-gray-900 mb-2">
                    Unit of measure *
                  </label>
                  <input
                    id="unit_of_measure"
                    type="text"
                    name="unit_of_measure"
                    value={formData.unit_of_measure}
                    onChange={handleChange}
                    maxLength={50}
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg h-12 text-base"
                  />
                  {errors.unit_of_measure && <p className="text-sm text-red-600 mt-1">{errors.unit_of_measure}</p>}
                </div>
                <div>
                  <label htmlFor="minimum_stock_level" className="block text-sm font-medium text-gray-900 mb-2">
                    Low-stock threshold *
                  </label>
                  <input
                    id="minimum_stock_level"
                    type="number"
                    name="minimum_stock_level"
                    value={formData.minimum_stock_level}
                    onChange={handleChange}
                    min="0"
                    step="1"
                    required
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg h-12 text-base"
                  />
                  {errors.minimum_stock_level && <p className="text-sm text-red-600 mt-1">{errors.minimum_stock_level}</p>}
                </div>
                <div>
                  <label htmlFor="barcode" className="block text-sm font-medium text-gray-900 mb-2">
                    Barcode
                  </label>
                  <input
                    id="barcode"
                    type="text"
                    name="barcode"
                    value={formData.barcode}
                    onChange={handleChange}
                    placeholder="E.g., 8472015928344"
                   className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono h-12 text-base"
                  />
                  <p className="text-xs text-gray-500 mt-1">Optional. Used for barcode scanning at checkout.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-4 flex-col sm:flex-row">
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition font-medium h-12 text-base"
            >
              Cancel
            </button>
             <button
               type="submit"
               disabled={loading || Object.keys(errors).length > 0}
               className="flex-1 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition font-medium h-12 text-base"
             >
               {loading ? 'Creating...' : 'Create Product'}
             </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default AddProduct
