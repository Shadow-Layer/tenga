import React, { useState, useEffect } from 'react'
import './index.css'

export default function App() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState<string | null>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [user, setUser] = useState<any>(null)

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
        <div className="max-w-4xl mx-auto px-4 py-12">
          {/* Header */}
          <div className="flex justify-between items-center mb-8">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Tenga Inventory POS</h1>
              <p className="text-sm text-gray-600">Point of Sale System for Inventory Management</p>
            </div>
            <button
              onClick={handleLogout}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              Logout
            </button>
          </div>

          {/* Dashboard */}
          <div className="bg-white rounded-lg shadow-lg p-8 space-y-6">
            <div className="border-b pb-4">
              <h2 className="text-lg font-semibold mb-2">Welcome, {user.username}!</h2>
              <p className="text-gray-600 text-sm">
                You are logged in as <strong>{user.role}</strong> in organization <strong>Test Store</strong>
              </p>
            </div>

            {/* User Info */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Email</p>
                <p className="text-sm font-medium">{user.email}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Role</p>
                <p className="text-sm font-medium">{user.role.toUpperCase()}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">User ID</p>
                <p className="text-sm font-medium">{user.id}</p>
              </div>
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Organization</p>
                <p className="text-sm font-medium">Test Store (ID: {user.organization_id})</p>
              </div>
            </div>

            {/* Next Steps */}
            <div className="bg-blue-50 border-l-4 border-blue-600 p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Next Steps</h3>
              <ul className="text-sm text-blue-800 space-y-1 list-disc list-inside">
                <li>API endpoint documentation: <a href="/docs" target="_blank" rel="noreferrer" className="underline">Swagger UI</a></li>
                <li>Create products and locations via the API</li>
                <li>Set up till sessions</li>
                <li>Start processing sales</li>
              </ul>
            </div>

            {/* API Base URL Info */}
            <div className="bg-gray-50 p-4 rounded text-xs text-gray-600 font-mono overflow-auto">
              <p className="mb-2"><strong>API Base URL:</strong> http://localhost:8000/api/v1/</p>
              <p><strong>Authorization:</strong> Bearer {localStorage.getItem('access_token')?.substring(0, 20)}...</p>
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
