import React, { useState, useEffect } from 'react'
import './index.css'

interface Step {
  number: number
  title: string
  description: string
  action?: {
    text: string
    href: string
    target?: string
  }
  example?: {
    endpoint: string
    method: string
    body?: string
  }
}

const QUICK_START_STEPS: Step[] = [
  {
    number: 1,
    title: 'Create a Location',
    description: 'Set up a physical store location where you\'ll manage inventory and tills.',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Locations/add_location_api_v1_locations_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/locations',
      method: 'POST',
      body: JSON.stringify({
        name: 'Downtown Store',
        code: 'LOC001',
        description: 'Main retail location',
        organization_id: 1
      }, null, 2)
    }
  },
  {
    number: 2,
    title: 'Create Products',
    description: 'Add items you want to sell (Coffee, Tea, etc.).',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Products/add_product_api_v1_products_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/products',
      method: 'POST',
      body: JSON.stringify({
        name: 'Premium Coffee',
        sku: 'COFFEE-001',
        category: 'Beverages',
        price: 450,
        cost: 200,
        organization_id: 1
      }, null, 2)
    }
  },
  {
    number: 3,
    title: 'Add Stock to Location',
    description: 'Set initial inventory levels at your location.',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Inventory/adjust_stock_api_v1_stock_stock_adjust_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/stock/stock/adjust',
      method: 'POST',
      body: JSON.stringify({
        product_id: 1,
        location_id: 1,
        quantity: 100,
        reason: 'initial_stock',
        recorded_by_id: 2
      }, null, 2)
    }
  },
  {
    number: 4,
    title: 'Create a Till',
    description: 'Set up a cash register at your location.',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Tills/add_till_api_v1_tills_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/tills',
      method: 'POST',
      body: JSON.stringify({
        location_id: 1,
        code: 'TILL001',
        name: 'Front Register',
        is_online: true
      }, null, 2)
    }
  },
  {
    number: 5,
    title: 'Open Till Session',
    description: 'Start a till session with opening balance (in cents).',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Tills/open_till_session_api_v1_tills__till_id__open_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/tills/{till_id}/open',
      method: 'POST',
      body: JSON.stringify({
        user_id: 2,
        opening_balance_cents: 50000
      }, null, 2)
    }
  },
  {
    number: 6,
    title: 'Create a Sale',
    description: 'Process a transaction with items and payment method.',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Sales/add_sale_api_v1_sales_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/sales',
      method: 'POST',
      body: JSON.stringify({
        till_id: 1,
        cashier_id: 2,
        payment_method: 'cash',
        items: [
          {
            product_id: 1,
            quantity: 2,
            unit_price: 450
          }
        ],
        is_offline: false,
        notes: 'Customer purchase'
      }, null, 2)
    }
  },
  {
    number: 7,
    title: 'Verify Stock Deduction',
    description: 'Check that inventory was automatically updated after the sale.',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Inventory/get_location_stock_api_v1_stock_locations__location_id__stock_get',
      target: '_blank'
    },
    example: {
      endpoint: 'GET /api/v1/stock/locations/{location_id}/stock',
      method: 'GET'
    }
  },
  {
    number: 8,
    title: 'Close Till Session',
    description: 'Finalize till session with closing balance.',
    action: {
      text: 'Open in Swagger UI',
      href: '/docs#/Tills/close_till_session_api_v1_tills__till_id__close_post',
      target: '_blank'
    },
    example: {
      endpoint: 'POST /api/v1/tills/{till_id}/close',
      method: 'POST',
      body: JSON.stringify({
        user_id: 2,
        closing_amount_cents: 51250,
        notes: 'End of shift'
      }, null, 2)
    }
  }
]

function StepCard({ step, isExpanded, onToggle }: { step: Step; isExpanded: boolean; onToggle: () => void }) {
  return (
    <div className="border rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full p-4 bg-gray-50 hover:bg-gray-100 flex items-start justify-between text-left"
      >
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0">
            <div className="flex items-center justify-center h-10 w-10 rounded-full bg-indigo-600 text-white font-bold text-lg">
              {step.number}
            </div>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">{step.title}</h3>
            <p className="text-sm text-gray-600 mt-1">{step.description}</p>
          </div>
        </div>
        <span className="text-gray-400 text-2xl ml-4">{isExpanded ? '−' : '+'}</span>
      </button>

      {isExpanded && (
        <div className="border-t bg-white p-4 space-y-4">
          {step.example && (
            <div className="bg-gray-50 rounded p-3">
              <p className="text-sm font-mono text-gray-700 mb-2">
                {step.example.method} {step.example.endpoint}
              </p>
              {step.example.body && (
                <pre className="bg-white border rounded p-2 text-xs overflow-auto max-h-48">
                  <code>{step.example.body}</code>
                </pre>
              )}
            </div>
          )}

          {step.action && (
            <a
              href={step.action.href}
              target={step.action.target || '_self'}
              rel={step.action.target === '_blank' ? 'noopener noreferrer' : undefined}
              className="inline-block bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700 text-sm font-medium"
            >
              {step.action.text} →
            </a>
          )}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [expandedStep, setExpandedStep] = useState<number | null>(1)

  // Check if user is already logged in on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    const storedUser = localStorage.getItem('user')
    if (token && storedUser) {
      setIsLoggedIn(true)
      setUser(JSON.parse(storedUser))
    }
  }, [])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setStatus('Logging in...')
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const data = await res.json()
        setStatus(`Login failed: ${data.detail || res.statusText}`)
        return
      }
      const data = await res.json()
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      setUser(data.user)
      setIsLoggedIn(true)
      setStatus('Login successful!')
    } catch (err: any) {
      setStatus(`Login error: ${err.message}`)
    }
  }

  function handleLogout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    setIsLoggedIn(false)
    setUser(null)
    setEmail('')
    setPassword('')
    setStatus(null)
  }

  if (isLoggedIn && user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="max-w-6xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-4xl font-bold text-gray-900">Tenga Inventory POS</h1>
              <p className="text-sm text-gray-600">Point of Sale System for Inventory Management</p>
            </div>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              Logout
            </button>
          </div>

          {/* User Info Card */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-lg font-semibold mb-3">Welcome, {user.username}!</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="bg-gray-50 p-3 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Email</p>
                <p className="text-sm font-medium">{user.email}</p>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Role</p>
                <p className="text-sm font-medium">{user.role.toUpperCase()}</p>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">User ID</p>
                <p className="text-sm font-medium">{user.id}</p>
              </div>
              <div className="bg-gray-50 p-3 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Organization</p>
                <p className="text-sm font-medium">Test Store</p>
              </div>
            </div>
          </div>

          {/* Quick Start Guide */}
          <div className="bg-white rounded-lg shadow-lg p-8">
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Quick Start: Till & Inventory Testing</h2>
              <p className="text-gray-600">
                Follow these steps to set up your first location, add products, and process a sale.
                Each step includes the API endpoint and example request body.
              </p>
            </div>

            {/* Steps */}
            <div className="space-y-3">
              {QUICK_START_STEPS.map((step) => (
                <StepCard
                  key={step.number}
                  step={step}
                  isExpanded={expandedStep === step.number}
                  onToggle={() => setExpandedStep(expandedStep === step.number ? null : step.number)}
                />
              ))}
            </div>

            {/* Testing Checklist */}
            <div className="mt-8 pt-8 border-t">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Testing Checklist</h3>
              <div className="grid md:grid-cols-3 gap-6">
                <div className="bg-blue-50 p-4 rounded">
                  <p className="font-semibold text-blue-900 mb-3">✓ Setup Phase</p>
                  <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                    <li>Create Location</li>
                    <li>Create 2 Products</li>
                    <li>Add stock</li>
                    <li>Create Till</li>
                  </ul>
                </div>

                <div className="bg-green-50 p-4 rounded">
                  <p className="font-semibold text-green-900 mb-3">✓ Till Operations</p>
                  <ul className="text-sm text-green-800 space-y-1 list-disc list-inside">
                    <li>Open Till Session</li>
                    <li>Verify session open</li>
                    <li>Process Sales</li>
                    <li>Track inventory</li>
                  </ul>
                </div>

                <div className="bg-purple-50 p-4 rounded">
                  <p className="font-semibold text-purple-900 mb-3">✓ Verification</p>
                  <ul className="text-sm text-purple-800 space-y-1 list-disc list-inside">
                    <li>Stock deductions</li>
                    <li>Till reconciliation</li>
                    <li>Sale history</li>
                    <li>Close session</li>
                  </ul>
                </div>
              </div>
            </div>

            {/* Documentation Links */}
            <div className="mt-8 pt-8 border-t">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Resources</h3>
              <div className="grid md:grid-cols-3 gap-4">
                <a
                  href="/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 border rounded hover:bg-gray-50"
                >
                  <p className="font-semibold text-gray-900">Swagger UI</p>
                  <p className="text-sm text-gray-600">Interactive API documentation with try-it-out</p>
                </a>

                <a
                  href="/redoc"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 border rounded hover:bg-gray-50"
                >
                  <p className="font-semibold text-gray-900">ReDoc</p>
                  <p className="text-sm text-gray-600">Beautiful, easy-to-read API documentation</p>
                </a>

                <a
                  href="/openapi.json"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="p-4 border rounded hover:bg-gray-50"
                >
                  <p className="font-semibold text-gray-900">OpenAPI Spec</p>
                  <p className="text-sm text-gray-600">Full OpenAPI 3.0 specification JSON</p>
                </a>
              </div>
            </div>

            {/* Info Box */}
            <div className="mt-8 pt-8 border-t bg-blue-50 p-4 rounded">
              <p className="text-sm text-blue-900 mb-2">
                <strong>💡 Tip:</strong> Click on any step to expand it and see the API endpoint and example request body.
                Copy the example JSON and paste it into the Swagger UI to test the endpoint.
              </p>
              <p className="text-sm text-blue-900">
                <strong>Organization ID:</strong> 1 | <strong>Current User ID:</strong> {user.id}
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-md mx-auto px-4 py-12">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">Tenga Inventory POS</h1>
          <p className="text-sm text-gray-600 mb-6">Point of Sale System for Inventory Management</p>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Login</h2>
          <form onSubmit={handleLogin} className="space-y-3">
            <input
              type="email"
              className="w-full border rounded px-3 py-2"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <input
              type="password"
              className="w-full border rounded px-3 py-2"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <div className="flex items-center justify-between">
              <button type="submit" className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">Login</button>
              <a className="text-sm text-indigo-600 hover:underline" href="/docs" target="_blank" rel="noreferrer">API Docs</a>
            </div>
          </form>
          {status && <p className={`mt-3 text-sm ${status.includes('successful') ? 'text-green-700' : 'text-gray-700'}`}>{status}</p>}
        </div>

        <div className="text-center mt-6 text-sm text-gray-600 space-y-2">
          <p><strong>Demo Credentials:</strong></p>
          <div className="bg-gray-50 p-3 rounded text-xs font-mono">
            <p>Email: admin@teststore.com</p>
            <p>Password: Admin123!</p>
          </div>
        </div>
      </div>
    </div>
  )
}
