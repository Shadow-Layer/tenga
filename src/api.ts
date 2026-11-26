import axios from 'axios'

const configuredApiUrl = typeof import.meta !== 'undefined' ? import.meta.env?.VITE_API_URL : undefined
const API_BASE_URL = configuredApiUrl || (import.meta.env?.DEV ? 'http://localhost:8000' : '')

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
  full_name?: string | null
  role: 'admin' | 'manager' | 'cashier' | 'operator'
  organization_id: number
  is_active: boolean
}

export interface Employee {
  id: number
  organization_id: number
  employee_number: string
  full_name: string
  email: string | null
  phone: string | null
  title: string | null
  user_id: number | null
  is_active: boolean
  archived_at: string | null
  location_ids: number[]
  till_ids: number[]
  created_at: string
  updated_at: string
}

export interface Organization {
  id: number
  name: string
  code: string
  description?: string
  phone?: string | null
  email?: string | null
  address?: string | null
  region?: string | null
  timezone?: string
  currency_code?: string | null
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
  price: number | string
  cost?: number | string | null
  barcode?: string | null
  unit_of_measure: string
  minimum_stock_level: number
  organization_id: number
  tax_rule_id?: number | null
  is_active: boolean
}

export interface TaxRule {
  id: number
  organization_id: number
  name: string
  rate: number | string
  tax_inclusive: boolean
  is_active: boolean
}

export interface Till {
  id: number
  location_id: number
  code: string
  name: string
  is_active: boolean
}

export interface TillSession {
  till_id: number
  session_id: number | null
  is_open: boolean
  opened_at: string | null
  closed_at: string | null
  opening_balance: number | null
  operator_id: number | null
  session_state: 'NO_SESSION' | 'OPEN' | 'CLOSED'
}

export interface TillSessionReconciliation {
  till_id: number
  session_id: number
  session_number: string
  closed_at: string
  closing_balance: number
  expected_closing_balance: number
  cash_variance: number
  currency_code: string
  status: string
  notes?: string | null
}

export interface SaleItem {
  product_id: number
  quantity: number
  unit_price: number | string
  id?: number
  discount_per_item?: number | string
  total_price?: number | string
  tax_rule_id?: number | null
  tax_rate?: number | string
  tax_inclusive?: boolean
  tax_amount?: number | string
}

export interface Sale {
  id: number
  till_id: number
  cashier_id: number
  payment_method: string
  sale_items: SaleItem[]
  total_amount: number | string
  discount_amount: number | string
  tax_amount: number | string
  amount_tendered: number | string
  change_given: number | string
  is_offline?: boolean
  status: 'PENDING' | 'COMPLETED' | 'pending' | 'completed'
  created_at: string
  notes?: string
}

export interface Stock {
  product_id: number
  product_name: string
  quantity: number
  last_movement_date: string | null
}

export interface InventoryMovement {
  id: number
  product_id: number
  location_id: number
  to_location_id: number | null
  movement_type: string
  quantity: number
  reason: string
  reference_type: string | null
  reference_id: number | null
  unit_cost: number | string | null
  currency_code: string | null
  device_id: string | null
  device_local_id: string | null
  recorded_by_id: number
  created_at: string
}

export interface InventoryCountLine {
  id: number
  product_id: number
  product_name: string
  expected_quantity: number
  observed_quantity: number | null
  difference: number | null
  reconciled_movement_id: number | null
}

export interface InventoryCount {
  id: number
  location_id: number
  status: string
  notes: string | null
  created_by_id: number
  reconciled_by_id: number | null
  started_at: string
  reconciled_at: string | null
  lines: InventoryCountLine[]
}

export interface CsvImportPreview {
  valid: boolean
  row_count: number
  valid_count: number
  errors: Array<{ row_number: number; field: string; message: string }>
  rows: Array<Record<string, unknown>>
  already_imported?: boolean
  batch_id?: number | null
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
    apiClient.get<{ items: Organization[]; total: number }>('/api/v1/organizations', {
      params: { skip, limit },
    }),
  get: (id: number) => apiClient.get<Organization>(`/api/v1/organizations/${id}`),
  update: (
    id: number,
    settings: Partial<Pick<Organization, 'name' | 'description' | 'phone' | 'email' | 'address' | 'region' | 'timezone' | 'currency_code'>>
      & { confirm_legacy_currency?: boolean },
  ) => apiClient.patch<Organization>(`/api/v1/organizations/${id}`, settings),
}

// Products API
export const productsAPI = {
  list: (organizationId: number, skip = 0, limit = 20) =>
    apiClient.get<{ items: Product[]; total: number }>('/api/v1/products', {
      params: { organization_id: organizationId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Product>(`/api/v1/products/${id}`),
  create: (product: Partial<Product>) =>
    apiClient.post<Product>('/api/v1/products', product),
  update: (id: number, product: Partial<Product>) =>
    apiClient.put<Product>(`/api/v1/products/${id}`, product),
  search: (organizationId: number, query: string) =>
    apiClient.get<{ items: Product[]; total: number }>('/api/v1/products', {
      params: { organization_id: organizationId, search: query },
    }),
}

// Locations API
export const locationsAPI = {
  list: (organizationId: number, skip = 0, limit = 10) =>
    apiClient.get<{ items: Location[]; total: number }>('/api/v1/locations', {
      params: { organization_id: organizationId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Location>(`/api/v1/locations/${id}`),
  create: (location: Partial<Location>) =>
    apiClient.post<Location>('/api/v1/locations', location),
}

// Tills API
export const tillsAPI = {
  list: (_organizationId: number, locationId?: number, skip = 0, limit = 10) =>
    apiClient.get<{ items: Till[]; total: number }>('/api/v1/tills/', {
      params: { location_id: locationId, skip, limit },
    }),
  assigned: (skip = 0, limit = 100) =>
    apiClient.get<{ items: Till[]; total: number }>('/api/v1/tills/assigned', {
      params: { skip, limit },
    }),
  get: (id: number) => apiClient.get<Till>(`/api/v1/tills/${id}`),
  getStatus: (id: number) => apiClient.get<TillSession>(`/api/v1/tills/${id}/status`),
  openSession: (id: number, openingBalance: number) =>
    apiClient.post(`/api/v1/tills/${id}/open`, {
      opening_balance: openingBalance,
    }),
  closeSession: (id: number, sessionId: number, closingBalance: number, notes?: string) =>
    apiClient.post<TillSessionReconciliation>(`/api/v1/tills/${id}/close`, {
      session_id: sessionId,
      closing_balance: closingBalance,
      notes,
    }),
}

export const employeesAPI = {
    list: (organizationId: number, active = true) =>
      apiClient.get<{ items: Employee[]; total: number; skip: number; limit: number }>(
        `/api/v1/organizations/${organizationId}/employees`,
        { params: { active, limit: 100 } },
      ),
    create: (
      organizationId: number,
      employee: {
        employee_number: string
        full_name: string
        user_id?: number | null
        location_ids: number[]
        till_ids: number[]
      },
    ) => apiClient.post<Employee>(`/api/v1/organizations/${organizationId}/employees`, employee),
    update: (
      organizationId: number,
      employeeId: number,
      employee: {
        employee_number: string
        full_name: string
        user_id: number | null
        location_ids: number[]
        till_ids: number[]
      },
    ) => apiClient.patch<Employee>(
      `/api/v1/organizations/${organizationId}/employees/${employeeId}`,
      employee,
    ),
}

// Sales API
export const salesAPI = {
  create: (sale: {
    till_id: number
    till_session_id: number
    idempotency_key: string
    cashier_id?: number
    payment_method: string
    expected_total: number | string
    amount_tendered: number | string
    items: Array<{
      product_id: number
      quantity: number
      unit_price: number | string
      tax_rate: number | string
      tax_inclusive: boolean
    }>
    is_offline?: boolean
    notes?: string
  }) => apiClient.post<Sale>('/api/v1/sales', sale),
  list: (tillId: number, skip = 0, limit = 50) =>
    apiClient.get<{ items: Sale[]; total: number }>('/api/v1/sales', {
      params: { till_id: tillId, skip, limit },
    }),
  get: (id: number) => apiClient.get<Sale>(`/api/v1/sales/${id}`),
}

// Inventory API
export const inventoryAPI = {
  getStock: async (productId: number, locationId: number) => {
    const response = await apiClient.get<{ items: Stock[] }>(
      `/api/v1/stock/locations/${locationId}/stock`,
    )
    const item = response.data.items.find((stockItem) => stockItem.product_id === productId)
    if (!item) {
      throw new Error(`Stock record not found for product ${productId}`)
    }
    return { data: item }
  },
  getStockAtLocation: (locationId: number) =>
    apiClient.get<{ location_id: number; items: Stock[]; total_items: number }>(
      `/api/v1/stock/locations/${locationId}/stock`,
    ),
  recordMovement: (movement: {
    product_id: number
    location_id: number
    quantity: number
    reason: string
  }) => apiClient.post('/api/v1/stock/stock/adjust', movement),
  listMovements: (productId: number, locationId: number, skip = 0, limit = 50) =>
    apiClient.get(`/api/v1/stock/stock/movements`, {
      params: { product_id: productId, location_id: locationId, skip, limit },
    }),
  adjustStock: (adjustment: {
    product_id: number
    location_id: number
    quantity: number
    reason: string
    note?: string
  }) => apiClient.post('/api/v1/stock/stock/adjust', adjustment),
  receiveStock: (receipt: {
    product_id: number
    location_id: number
    quantity: number
    unit_cost?: number
    reason: string
  }) => apiClient.post<InventoryMovement>('/api/v1/stock/stock/receive', receipt),
  issueStock: (issue: {
    product_id: number
    location_id: number
    quantity: number
    reason: string
  }) => apiClient.post<InventoryMovement>('/api/v1/stock/stock/issue', issue),
  transferStock: (transfer: {
    source_location_id: number
    destination_location_id: number
    lines: Array<{ product_id: number; quantity: number }>
    reason: string
  }) => apiClient.post('/api/v1/stock/stock/transfer', transfer),
  createCount: (count: {
    location_id: number
    lines: Array<{ product_id: number; observed_quantity: number | null }>
    notes?: string
  }) => apiClient.post<InventoryCount>('/api/v1/stock/stock/counts', count),
  updateCountObservations: (
    countId: number,
    lines: Array<{ product_id: number; observed_quantity: number | null }>,
  ) => apiClient.patch<InventoryCount>(`/api/v1/stock/stock/counts/${countId}`, { lines }),
  getCount: (countId: number) =>
    apiClient.get<InventoryCount>(`/api/v1/stock/stock/counts/${countId}`),
  reconcileCount: (
    countId: number,
    expectedObservations: Array<{ product_id: number; observed_quantity: number | null }>,
  ) => apiClient.post<InventoryCount>(
    `/api/v1/stock/stock/counts/${countId}/reconcile`,
    { expected_observations: expectedObservations },
  ),
  listMovementHistory: (params: { product_id?: number; location_id?: number; skip?: number; limit?: number }) =>
    apiClient.get<{ items: InventoryMovement[]; total: number; skip: number; limit: number }>(
      '/api/v1/stock/stock/movements',
      { params },
    ),
  getValuation: (locationId?: number) =>
    apiClient.get<{ currency_code: string | null; total_value: number | string | null; items: Array<{
      product_id: number
      product_name: string
      location_id: number
      quantity: number
      weighted_average_cost: number | string | null
      inventory_value: number | string | null
      currency_code: string | null
    }> }>('/api/v1/stock/stock/valuation', { params: { location_id: locationId } }),
  getLowStock: (locationId?: number) =>
    apiClient.get<{ total_items: number; items: Array<{
      product_id: number
      product_name: string
      location_id: number
      quantity: number
      minimum_stock_level: number
    }> }>('/api/v1/stock/stock/low-stock', { params: { location_id: locationId } }),
  getLocationReport: (locationId: number) =>
    apiClient.get(`/api/v1/stock/locations/${locationId}/report`),
}

// Enhanced Products API with search and pagination
export const productsAPI_v2 = {
  list: (params?: { search?: string; skip?: number; limit?: number; organization_id?: number; include_inactive?: boolean }) =>
    apiClient.get<{ items: Product[]; total: number }>('/api/v1/products', {
      params,
    }),
  create: (product: {
    sku: string
    name: string
    price: number
    cost?: number
    barcode?: string
    unit_of_measure?: string
    minimum_stock_level?: number
    description?: string
    category?: string
    organization_id: number
    tax_rule_id?: number | null
  }) => apiClient.post<Product>('/api/v1/products', product),
}

export const catalogImportAPI = {
  getProductTemplate: () =>
    apiClient.get<Blob>('/api/v1/products/imports/template', { responseType: 'blob' }),
  getOpeningStockTemplate: () =>
    apiClient.get<Blob>('/api/v1/products/imports/opening-stock/template', { responseType: 'blob' }),
  previewProducts: (csv_text: string) =>
    apiClient.post<CsvImportPreview>('/api/v1/products/imports/products/preview', { csv_text }),
  commitProducts: (csv_text: string) =>
    apiClient.post('/api/v1/products/imports/products/commit', { csv_text }),
  previewOpeningStock: (csv_text: string) =>
    apiClient.post<CsvImportPreview>('/api/v1/products/imports/opening-stock/preview', { csv_text }),
  commitOpeningStock: (csv_text: string) =>
    apiClient.post('/api/v1/products/imports/opening-stock/commit', { csv_text }),
  exportProducts: () =>
    apiClient.get<Blob>('/api/v1/products/export', { responseType: 'blob' }),
}

export const taxRulesAPI = {
  list: () => apiClient.get<TaxRule[]>('/api/v1/tax-rules'),
  create: (rule: { name: string; rate: number; tax_inclusive: boolean }) =>
    apiClient.post<TaxRule>('/api/v1/tax-rules', rule),
  update: (
    id: number,
    rule: Partial<Pick<TaxRule, 'name' | 'rate' | 'tax_inclusive' | 'is_active'>>,
  ) => apiClient.patch<TaxRule>(`/api/v1/tax-rules/${id}`, rule),
}

// Subscriptions API
export const subscriptionsAPI = {
  get: (organizationId: number) =>
    apiClient.get<Subscription>(`/api/v1/subscriptions/${organizationId}`),
  getState: (organizationId: number) =>
    apiClient.get<{ state: string }>(`/api/v1/subscriptions/${organizationId}/state`),
}
