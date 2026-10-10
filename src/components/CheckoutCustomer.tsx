import React, { useState, useRef, useEffect } from 'react'

interface Customer {
  id: number
  name: string
  phone: string
  email?: string
  loyalty_balance?: number
}

export default function CheckoutCustomer() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [searchResults, setSearchResults] = useState<Customer[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showNewCustomerModal, setShowNewCustomerModal] = useState(false)
  const searchTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // New customer form state
  const [newCustomerName, setNewCustomerName] = useState('')
  const [newCustomerPhone, setNewCustomerPhone] = useState('')
  const [newCustomerEmail, setNewCustomerEmail] = useState('')

  // Mock customer database (in real app, this would be an API call)
  const mockCustomers: Customer[] = [
    { id: 1, name: 'John Doe', phone: '+263712345678', email: 'john@example.com', loyalty_balance: 5000 },
    { id: 2, name: 'Jane Smith', phone: '+263712345679', email: 'jane@example.com', loyalty_balance: 2500 },
    { id: 3, name: 'Bob Johnson', phone: '+263712345680', loyalty_balance: 0 },
  ]

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    
    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    if (query.trim().length === 0) {
      setSearchResults([])
      setIsSearching(false)
      return
    }

    setIsSearching(true)

    // Simulate API debounce (500ms)
    searchTimeoutRef.current = setTimeout(() => {
      // Mock search: filter customers by name or phone
      const query_lower = query.toLowerCase()
      const results = mockCustomers.filter(
        (c) =>
          c.name.toLowerCase().includes(query_lower) ||
          c.phone.includes(query)
      ).slice(0, 5)
      
      setSearchResults(results)
      setIsSearching(false)
    }, 500)
  }

  const handleSelectCustomer = (customer: Customer) => {
    setSelectedCustomer(customer)
    setSearchQuery('')
    setSearchResults([])
  }

  const handleAddNewCustomer = async () => {
    if (!newCustomerName.trim() || !newCustomerPhone.trim()) {
      alert('Please fill in required fields')
      return
    }

    // Mock: In real app, would POST to /customers
    const newCustomer: Customer = {
      id: Math.max(...mockCustomers.map(c => c.id), 0) + 1,
      name: newCustomerName,
      phone: newCustomerPhone,
      email: newCustomerEmail || undefined,
      loyalty_balance: 0,
    }

    setSelectedCustomer(newCustomer)
    setNewCustomerName('')
    setNewCustomerPhone('')
    setNewCustomerEmail('')
    setShowNewCustomerModal(false)
  }

  const handleClearCustomer = () => {
    setSelectedCustomer(null)
    setSearchQuery('')
    setSearchResults([])
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-4">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Customer</h2>

      {selectedCustomer ? (
        <div className="bg-indigo-50 p-4 rounded-lg mb-4">
          <h3 className="font-semibold text-gray-900">{selectedCustomer.name}</h3>
          <p className="text-sm text-gray-600">{selectedCustomer.phone}</p>
          {selectedCustomer.email && (
            <p className="text-sm text-gray-600">{selectedCustomer.email}</p>
          )}
          {selectedCustomer.loyalty_balance !== undefined && (
            <p className="text-sm font-medium text-indigo-600 mt-2">
              Loyalty Balance: {selectedCustomer.loyalty_balance} pts
            </p>
          )}
          <div className="flex gap-2 mt-4">
            <button
              onClick={() => setSelectedCustomer(null)}
              className="flex-1 px-3 py-1 text-sm bg-white border border-indigo-300 text-indigo-600 rounded hover:bg-indigo-50"
            >
              Change
            </button>
            <button
              onClick={handleClearCustomer}
              className="flex-1 px-3 py-1 text-sm bg-white border border-gray-300 text-gray-600 rounded hover:bg-gray-50"
            >
              Clear
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Search input */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search by name or phone..."
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            />
            
            {/* Search results dropdown */}
            {searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 border rounded-lg bg-white shadow-lg z-10">
                {searchResults.map((customer) => (
                  <button
                    key={customer.id}
                    onClick={() => handleSelectCustomer(customer)}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b last:border-b-0"
                  >
                    <div className="font-medium text-gray-900">{customer.name}</div>
                    <div className="text-sm text-gray-600">{customer.phone}</div>
                  </button>
                ))}
              </div>
            )}

            {isSearching && (
              <div className="absolute top-full left-0 right-0 mt-1 border rounded-lg bg-white shadow-lg z-10 p-4 text-center text-gray-600">
                Searching...
              </div>
            )}
          </div>

          {/* New customer button */}
          <button
            onClick={() => setShowNewCustomerModal(true)}
            className="w-full px-4 py-2 border border-indigo-600 text-indigo-600 rounded-lg hover:bg-indigo-50 font-medium text-sm"
          >
            + New Customer
          </button>

          <p className="text-xs text-gray-500 text-center">
            Customer is optional
          </p>
        </div>
      )}

      {/* New customer modal */}
      {showNewCustomerModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Add New Customer
            </h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Name *
                </label>
                <input
                  type="text"
                  value={newCustomerName}
                  onChange={(e) => setNewCustomerName(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone *
                </label>
                <input
                  type="tel"
                  value={newCustomerPhone}
                  onChange={(e) => setNewCustomerPhone(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={newCustomerEmail}
                  onChange={(e) => setNewCustomerEmail(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowNewCustomerModal(false)}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleAddNewCustomer}
                className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
