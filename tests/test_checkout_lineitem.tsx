import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import CheckoutLineItem from '../src/components/CheckoutLineItem'

describe('CheckoutLineItem', () => {
  const mockItem = {
    productId: 1,
    quantity: 2,
    unitPrice: 1000, // $10.00 in cents
    name: 'Test Product',
  }

  test('renders line item with product details', () => {
    render(<CheckoutLineItem item={mockItem} />)
    
    expect(screen.getByText('Test Product')).toBeInTheDocument()
    expect(screen.getByText(/\$10\.00 × 2/)).toBeInTheDocument()
    expect(screen.getByText('$20.00')).toBeInTheDocument()
  })

  test('quantity buttons work correctly', () => {
    const { getByDisplayValue } = render(<CheckoutLineItem item={mockItem} />)
    
    const quantityInput = getByDisplayValue('2') as HTMLInputElement
    expect(quantityInput).toBeInTheDocument()
    
    // Decrease button should be enabled
    const decreaseBtn = screen.getAllByText('−')[0]
    expect(decreaseBtn).not.toBeDisabled()
    
    // Increase button should be enabled
    const increaseBtn = screen.getAllByText('+')[0]
    expect(increaseBtn).not.toBeDisabled()
  })

  test('remove button shows confirmation dialog', async () => {
    render(<CheckoutLineItem item={mockItem} />)
    
    const removeBtn = screen.getByText('Remove')
    fireEvent.click(removeBtn)
    
    await waitFor(() => {
      expect(screen.getByText('Remove item?')).toBeInTheDocument()
    })
  })

  test('line total is calculated correctly', () => {
    const itemWithQuantity = { ...mockItem, quantity: 3, unitPrice: 2500 }
    render(<CheckoutLineItem item={itemWithQuantity} />)
    
    // 3 * 2500 cents = 75.00
    expect(screen.getByText('$75.00')).toBeInTheDocument()
  })
})
