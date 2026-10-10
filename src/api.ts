import axios from 'axios'

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) || 'http://localhost:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// API Types
export interface User {
  id: number
  username: string
  email: string
  role: 'admin' | 'manager' | 'cashier'
  organization_id: number
  is_active: boolean
}

export interface Organization {
  id: number
  name: string
  code: string
  description?: string
}

export interface Location {
  id: number
  name: string
  code: string
  description?: string
  organization_id: number
}

export interface Product {
  id: number
  name: string
  sku: string
  description?: string
  category?: string
  price: number
  cost: number
  organization_id: number
}

export interface Till {
  id: number
  location_id: number
  code: string
  name: string
  is_online: boolean
}

export interface TillSession {
  id: number
  till_id: number
  user_id: number
  opened_at: string
  closed_at?: string
  opening_balance_cents: number
  closing_amount_cents?: number
  status: 'open' | 'closed'
}

export interface SaleItem {
  product_id: number
  quantity: number
  unit_price: number
}

export interface Sale {
  id: number
  till_id: number
  cashier_id: number
  payment_method: string
  items: SaleItem[]
  total_amount_cents: number
  is_offline: boolean
  status: 'pending' | 'completed'
  created_at: string
  notes?: string
}

export interface Stock {
  product_id: number
  location_id: number
  quantity: number
  last_counted_at?: string
}

export interface Subscription {
  id: number
  organization_id: number
  plan: string
  status: 'active' | 'grace' | 'limited' | 'inactive'
  expires_at: string
  grace_until?: string
}

// Auth API
export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post('/api/v1/auth/login', { email, password }),
  getCurrentUser: () => apiClient.get('/api/v1/auth/me'),
}

// Organizations API
export const organizationsAPI = {
  list: (skip = 0, limit = 10) =>
    apiClient.get<{ data: Organization[] }>('/organizations', {
      params: { skip, limit },
    }),
  get: (id: number) => apiClient.get<Organization>(`/organizations/${id}`),
}

// Products API
export const productsAPI = {
  list: (organizationId: number, skip = 0, limit = 20) =>
    apiClient.get<{ data: Product[] }>('/api/v1/products', {
      params: { organization_id: organizationId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Product>(`/api/v1/products/${id}`),
  create: (product: Partial<Product>) =>
    apiClient.post<Product>('/api/v1/products', product),
  update: (id: number, product: Partial<Product>) =>
    apiClient.put<Product>(`/api/v1/products/${id}`, product),
  search: (organizationId: number, query: string) =>
    apiClient.get<{ data: Product[] }>('/api/v1/products', {
      params: { organization_id: organizationId, q: query },
    }),
}

// Locations API
export const locationsAPI = {
  list: (organizationId: number, skip = 0, limit = 10) =>
    apiClient.get<{ data: Location[] }>('/api/v1/locations', {
      params: { organization_id: organizationId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Location>(`/api/v1/locations/${id}`),
  create: (location: Partial<Location>) =>
    apiClient.post<Location>('/api/v1/locations', location),
}

// Tills API
export const tillsAPI = {
  list: (organizationId: number, locationId?: number, skip = 0, limit = 10) =>
    apiClient.get<{ data: Till[] }>('/api/v1/tills/', {
      params: { organization_id: organizationId, location_id: locationId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Till>(`/api/v1/tills/${id}`),
  getStatus: (id: number) => apiClient.get<TillSession>(`/api/v1/tills/${id}/status`),
  openSession: (id: number, userId: number, openingBalance: number) =>
    apiClient.post(`/api/v1/tills/${id}/open`, {
      user_id: userId,
      opening_balance: openingBalance,
    }),
  closeSession: (id: number, userId: number, closingAmount: number, notes?: string) =>
    apiClient.post(`/api/v1/tills/${id}/close`, {
      user_id: userId,
      closing_amount_cents: closingAmount,
      notes,
    }),
}

// Sales API
export const salesAPI = {
  create: (sale: {
    till_id: number
    cashier_id: number
    payment_method: string
    items: SaleItem[]
    is_offline: boolean
    notes?: string
  }) => apiClient.post<Sale>('/api/v1/sales', sale),
  list: (tillId: number, skip = 0, limit = 50) =>
    apiClient.get<{ data: Sale[] }>('/api/v1/sales', {
      params: { till_id: tillId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Sale>(`/api/v1/sales/${id}`),
}

// Inventory API
export const inventoryAPI = {
  getStock: (productId: number, locationId: number) =>
    apiClient.get<Stock>(`/api/v1/stock/${productId}/location/${locationId}`),
  getStockAtLocation: (locationId: number) =>
    apiClient.get<{ data: Stock[] }>(`/api/v1/stock/location/${locationId}`),
  recordMovement: (movement: {
    product_id: number
    location_id: number
    quantity: number
    reason: string
    recorded_by_id: number
  }) => apiClient.post('/api/v1/stock/movements', movement),
  listMovements: (productId: number, locationId: number, skip = 0, limit = 50) =>
    apiClient.get(`/api/v1/stock/movements`, {
      params: { product_id: productId, location_id: locationId, skip, limit },
    }),
  adjustStock: (adjustment: {
    product_id: number
    location_id: number
    quantity: number
    reason: string
    note?: string
  }) => apiClient.post('/api/v1/stock/adjust', adjustment),
}

// Enhanced Products API with search and pagination
export const productsAPI_v2 = {
  list: (params?: { search?: string; skip?: number; limit?: number; organization_id?: number }) =>
    apiClient.get<{ data: Product[]; total?: number }>('/api/v1/products', {
      params,
    }),
  create: (product: {
    sku: string
    name: string
    price: number
    cost?: number
    barcode?: string
    description?: string
    category?: string
    organization_id: number
  }) => apiClient.post<Product>('/api/v1/products', product),
}

// Subscriptions API
export const subscriptionsAPI = {
  get: (organizationId: number) =>
    apiClient.get<Subscription>(`/subscriptions/${organizationId}`),
  getState: (organizationId: number) =>
    apiClient.get<{ state: string }>(`/subscriptions/${organizationId}/state`),
}
