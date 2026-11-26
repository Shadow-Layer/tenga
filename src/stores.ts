import { create } from 'zustand'
import type { User, Organization, Location, Till } from './api'

interface AuthStore {
  user: User | null
  token: string | null
  isLoading: boolean
  setAuth: (user: User, token: string) => void
  logout: () => void
  setLoading: (loading: boolean) => void
  initFromStorage: () => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  setAuth: (user, token) => {
    localStorage.setItem('access_token', token)
    localStorage.setItem('user', JSON.stringify(user))
    set({ user, token })
  },
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },
  setLoading: (loading) => set({ isLoading: loading }),
  initFromStorage: () => {
    const token = localStorage.getItem('access_token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        set({ user, token })
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
      }
    }
  },
}))

interface AppContextStore {
  selectedOrganization: Organization | null
  selectedLocation: Location | null
  selectedTill: Till | null
  setSelectedOrganization: (org: Organization | null) => void
  setSelectedLocation: (loc: Location | null) => void
  setSelectedTill: (till: Till | null) => void
  clearContext: () => void
}

export const useAppContextStore = create<AppContextStore>((set) => ({
  selectedOrganization: null,
  selectedLocation: null,
  selectedTill: null,
  setSelectedOrganization: (org) => set({ selectedOrganization: org }),
  setSelectedLocation: (loc) => set({ selectedLocation: loc }),
  setSelectedTill: (till) => set({ selectedTill: till }),
  clearContext: () =>
    set({
      selectedOrganization: null,
      selectedLocation: null,
      selectedTill: null,
    }),
}))

interface POSStore {
  cartItems: Array<{
    productId: number
    quantity: number
    unitPrice: number
    name: string
    taxRate: string | null
    taxInclusive: boolean
  }>
  selectedCustomerId: number | null
  paymentMethod: string
  isProcessing: boolean
  error: string | null
  addToCart: (
    productId: number,
    quantity: number,
    unitPrice: number,
    name: string,
    taxRate: string | null,
    taxInclusive: boolean,
  ) => void
  removeFromCart: (productId: number) => void
  updateQuantity: (productId: number, quantity: number) => void
  clearCart: () => void
  setPaymentMethod: (method: string) => void
  setIsProcessing: (processing: boolean) => void
  setError: (error: string | null) => void
  setSelectedCustomer: (customerId: number | null) => void
}

export const usePOSStore = create<POSStore>((set) => ({
  cartItems: [],
  selectedCustomerId: null,
  paymentMethod: 'CASH',
  isProcessing: false,
  error: null,
  addToCart: (productId, quantity, unitPrice, name, taxRate, taxInclusive) =>
    set((state) => {
      const existing = state.cartItems.find((item) => item.productId === productId)
      if (existing) {
        return {
          cartItems: state.cartItems.map((item) =>
            item.productId === productId
              ? { ...item, quantity: item.quantity + quantity }
              : item,
          ),
        }
      }
      return {
        cartItems: [...state.cartItems, { productId, quantity, unitPrice, name, taxRate, taxInclusive }],
      }
    }),
  removeFromCart: (productId) =>
    set((state) => ({
      cartItems: state.cartItems.filter((item) => item.productId !== productId),
    })),
  updateQuantity: (productId, quantity) =>
    set((state) => ({
      cartItems:
        quantity <= 0
          ? state.cartItems.filter((item) => item.productId !== productId)
          : state.cartItems.map((item) =>
              item.productId === productId ? { ...item, quantity } : item,
            ),
    })),
  clearCart: () => set({ cartItems: [], error: null, selectedCustomerId: null }),
  setPaymentMethod: (method) => set({ paymentMethod: method }),
  setIsProcessing: (processing) => set({ isProcessing: processing }),
  setError: (error) => set({ error }),
  setSelectedCustomer: (customerId) => set({ selectedCustomerId: customerId }),
}))
