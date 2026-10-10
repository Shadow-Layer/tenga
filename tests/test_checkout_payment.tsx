import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import CheckoutPayment from '../src/components/CheckoutPayment'

// Mock the API and stores
jest.mock('../src/api', () => ({
  salesAPI: {
    create: jest.fn(),
  },
}))

jest.mock('../src/stores', () => ({
  usePOSStore: () => ({
    cartItems: [{ productId: 1, quantity: 1, unitPrice: 1000, name: 'Product' }],
    setIsProcessing: jest.fn(),
    setError: jest.fn(),
    clearCart: jest.fn(),
  }),
  useAuthStore: () => ({
    user: { id: 1, username: 'cashier', role: 'cashier' },
  }),
  useAppContextStore: () => ({
    selectedTill: { id: 1, name: 'Till 1' },
  }),
}))

describe('CheckoutPayment', () => {
  const mockTotal = 1000 // $10.00 in cents

  test('renders payment tabs', () => {
    render(<CheckoutPayment total={mockTotal} />)
    
    expect(screen.getByText('Cash')).toBeInTheDocument()
    expect(screen.getByText('Card')).toBeInTheDocument()
    expect(screen.getByText('Mobile Money')).toBeInTheDocument()
  })

  test('cash tab shows amount paid and change calculation', () => {
    render(<CheckoutPayment total={mockTotal} />)
    
    const cashTab = screen.getByText('Cash').parentElement
    if (cashTab) {
      fireEvent.click(cashTab)
    }
    
    expect(screen.getByPlaceholderText('0.00')).toBeInTheDocument()
    expect(screen.getByText('Change')).toBeInTheDocument()
  })

  test('card tab shows card fields', () => {
    render(<CheckoutPayment total={mockTotal} />)
    
    const cardTab = screen.getByText('Card').parentElement
    if (cardTab) {
      fireEvent.click(cardTab)
    }
    
    expect(screen.getByPlaceholderText('1234 5678 9012 3456')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('John Doe')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('MM/YY')).toBeInTheDocument()
  })

  test('mobile money tab shows operator dropdown', () => {
    render(<CheckoutPayment total={mockTotal} />)
    
    const mobileTab = screen.getByText('Mobile Money').parentElement
    if (mobileTab) {
      fireEvent.click(mobileTab)
    }
    
    expect(screen.getByDisplayValue('econet')).toBeInTheDocument()
    expect(screen.getByText('Econet')).toBeInTheDocument()
  })

  test('complete sale button is disabled when payment is invalid', () => {
    render(<CheckoutPayment total={mockTotal} />)
    
    const completeBtn = screen.getByText(/Complete Sale/)
    expect(completeBtn).toBeDisabled()
  })

  test('displays total amount on button', () => {
    render(<CheckoutPayment total={mockTotal} />)
    
    expect(screen.getByText(/Complete Sale - 10\.00 ZWL/)).toBeInTheDocument()
  })
})
