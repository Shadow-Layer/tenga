import React from 'react'
import './index.css'

export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Tenga Inventory POS
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Point of Sale System for Inventory Management
          </p>
          <div className="bg-white rounded-lg shadow-lg p-8">
            <p className="text-gray-700 mb-4">
              Application is loading...
            </p>
            <div className="animate-spin inline-block">
              <div className="border-4 border-indigo-200 border-t-indigo-600 rounded-full h-8 w-8"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
