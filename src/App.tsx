import { useEffect, useState, type FormEvent } from 'react'
import axios from 'axios'
import './index.css'
import AddProduct from './components/AddProduct'
import Checkout from './components/Checkout'
import { InventoryOverview } from './components/InventoryOverview'
import InventoryOperations from './components/InventoryOperations'
import { OfflineSyncStatus } from './components/OfflineSyncStatus'
import EmployeeTillAssignments from './components/EmployeeTillAssignments'
import SetupWizard from './components/SetupWizard'
import {
  locationsAPI,
  productsAPI_v2,
  tillsAPI,
  type Till,
  type TillSession,
  type User,
} from './api'
import { useAppContextStore, useAuthStore } from './stores'
import { getOfflineOperationQueue } from './offline/runtime'

type Screen = 'setup' | 'employees' | 'inventory' | 'operations' | 'product' | 'pos'

const SCREENS: Array<{ id: Exclude<Screen, 'setup' | 'employees'>; label: string }> = [
  { id: 'inventory', label: 'Inventory' },
  { id: 'operations', label: 'Stock operations' },
  { id: 'product', label: 'Add product' },
  { id: 'pos', label: 'Point of sale' },
]

type TillAvailability = {
  assignedTills: Till[]
  openableTills: Till[]
  openTills: Till[]
  openSessionIds: Record<number, number>
  busyTills: Till[]
  managerOpenSessions: Array<{ till: Till; session: TillSession }>
  statusCheckFailed: boolean
}

async function fetchAllTills(
  fetchPage: (skip: number) => Promise<{ data: { items: Till[]; total: number } }>,
): Promise<Till[]> {
  const tills: Till[] = []
  let total = 0
  do {
    const response = await fetchPage(tills.length)
    if (response.data.items.length === 0 && tills.length < response.data.total) {
      throw new Error('Till list changed while loading. Refresh and retry.')
    }
    tills.push(...response.data.items)
    total = response.data.total
  } while (tills.length < total)
  return tills
}

async function fetchTillAvailability(user: User): Promise<TillAvailability> {
  const [assignedResponse, allTillsResponse] = await Promise.all([
    fetchAllTills((skip) => tillsAPI.assigned(skip, 100)),
    user.role === 'admin' || user.role === 'manager'
      ? fetchAllTills((skip) => tillsAPI.list(user.organization_id, undefined, skip, 100))
      : Promise.resolve(null),
  ])
  const assignedTills = assignedResponse
  const tillsToCheck = allTillsResponse ?? assignedTills
  const assignedTillIds = new Set(assignedTills.map((till) => till.id))
  const checks: Array<{
    till: Till
    status: TillSession | null
    failed: boolean
  }> = []
  for (let offset = 0; offset < tillsToCheck.length; offset += 20) {
    const batch = await Promise.all(tillsToCheck.slice(offset, offset + 20).map(async (till) => {
      try {
        return { till, status: (await tillsAPI.getStatus(till.id)).data, failed: false }
      } catch {
        return { till, status: null, failed: true }
      }
    }))
    checks.push(...batch)
  }
  const ownOpenSessions = checks.flatMap(({ till, status }) =>
    assignedTillIds.has(till.id)
    && status?.session_state === 'OPEN'
    && status.operator_id === user.id
    && status.session_id !== null
      ? [{ till, sessionId: status.session_id }]
      : [],
  )
  const openSessionIds: Record<number, number> = {}
  for (const { till, sessionId } of ownOpenSessions) {
    openSessionIds[till.id] = sessionId
  }

  return {
    assignedTills,
    openableTills: checks
      .filter(({ till, status }) =>
        assignedTillIds.has(till.id) && status !== null && status.session_state !== 'OPEN',
      )
      .map(({ till }) => till),
    openTills: ownOpenSessions.map(({ till }) => till),
    openSessionIds,
    busyTills: checks
      .filter(({ till, status }) =>
        assignedTillIds.has(till.id) && status?.session_state === 'OPEN' && status.operator_id !== user.id,
      )
      .map(({ till }) => till),
    managerOpenSessions: checks.flatMap(({ till, status }) =>
      status?.session_state === 'OPEN' && status.session_id !== null
        ? [{ till, session: status }]
        : [],
    ),
    statusCheckFailed: checks.some(({ failed, status }) =>
      failed || (status?.session_state === 'OPEN' && status.session_id === null),
    ),
  }
}

function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    return error.response?.data?.detail ?? error.message
  }
  return error instanceof Error ? error.message : 'The till operation failed.'
}

async function cacheOpenTillSession(user: User, availability: TillAvailability): Promise<void> {
  const queue = getOfflineOperationQueue()
  const entry = Object.entries(availability.openSessionIds).find(([tillId]) =>
    availability.openTills.some((till) => till.id === Number(tillId)),
  )
  if (!entry) {
    await queue.clearOpenTillSession(user.organization_id, user.id)
    return
  }
  const [tillId, sessionId] = entry
  const till = availability.openTills.find((item) => item.id === Number(tillId))
  if (!till) throw new Error('The active till session no longer matches an assigned till.')
  await queue.saveOpenTillSession({
    userId: user.id,
    organizationId: user.organization_id,
    sessionId,
    till,
    cachedAt: Date.now(),
  })
}

export default function App() {
  const user = useAuthStore((state) => state.user)
  const setAuth = useAuthStore((state) => state.setAuth)
  const logout = useAuthStore((state) => state.logout)
  const selectedTill = useAppContextStore((state) => state.selectedTill)
  const setSelectedTill = useAppContextStore((state) => state.setSelectedTill)
  const clearContext = useAppContextStore((state) => state.clearContext)
  const [authInitialized, setAuthInitialized] = useState(false)
  const [screen, setScreen] = useState<Screen>('inventory')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loginMessage, setLoginMessage] = useState('')
  const [loginError, setLoginError] = useState(false)
  const [loginLoading, setLoginLoading] = useState(false)
  const [assignedTills, setAssignedTills] = useState<Till[]>([])
  const [openableTills, setOpenableTills] = useState<Till[]>([])
  const [busyTills, setBusyTills] = useState<Till[]>([])
  const [availableTills, setAvailableTills] = useState<Till[]>([])
  const [openSessionIds, setOpenSessionIds] = useState<Record<number, number>>({})
  const [managerOpenSessions, setManagerOpenSessions] = useState<
    Array<{ till: Till; session: TillSession }>
  >([])
  const [managerCloseTillId, setManagerCloseTillId] = useState<number | ''>('')
  const [openTillId, setOpenTillId] = useState<number | ''>('')
  const [openingBalance, setOpeningBalance] = useState('0')
  const [closingBalance, setClosingBalance] = useState('0')
  const [closingNotes, setClosingNotes] = useState('')
  const [managerClosingBalance, setManagerClosingBalance] = useState('0')
  const [managerClosingNotes, setManagerClosingNotes] = useState('')
  const [tillActionMessage, setTillActionMessage] = useState('')
  const [tillActionError, setTillActionError] = useState('')
  const [tillActionLoading, setTillActionLoading] = useState(false)
  const [tillsLoading, setTillsLoading] = useState(false)
  const [tillsError, setTillsError] = useState('')
  const [usingCachedTillSession, setUsingCachedTillSession] = useState(false)
  const [operationsView, setOperationsView] = useState<'receipt' | 'count' | 'import' | 'history'>('receipt')
  const [operationsProductId, setOperationsProductId] = useState<number | undefined>()

  useEffect(() => {
    useAuthStore.getState().initFromStorage()
    setAuthInitialized(true)
  }, [])

  useEffect(() => {
    if (!user) {
      setAssignedTills([])
      setOpenableTills([])
      setBusyTills([])
      setAvailableTills([])
      setOpenSessionIds({})
      setManagerOpenSessions([])
      setManagerCloseTillId('')
      setSelectedTill(null)
      setTillsError('')
      setUsingCachedTillSession(false)
      return
    }

    const authenticatedUser = user
    let active = true
    setTillsLoading(true)
    setTillsError('')

    async function loadAvailableTills() {
      try {
        const availability = await fetchTillAvailability(authenticatedUser)
        if (!active) return
        setUsingCachedTillSession(false)
        setAssignedTills(availability.assignedTills)
        setOpenableTills(availability.openableTills)
        setBusyTills(availability.busyTills)
        setAvailableTills(availability.openTills)
        setOpenSessionIds(availability.openSessionIds)
        setManagerOpenSessions(availability.managerOpenSessions)
        setManagerCloseTillId((current) =>
          availability.managerOpenSessions.some(({ till }) => till.id === current)
            ? current
            : availability.managerOpenSessions[0]?.till.id ?? '',
        )
        setOpenTillId((current) =>
          availability.openableTills.some((till) => till.id === current)
            ? current
            : availability.openableTills[0]?.id ?? '',
        )
        const currentTill = useAppContextStore.getState().selectedTill
        setSelectedTill(
          availability.openTills.find((till) => till.id === currentTill?.id)
            ?? availability.openTills[0]
            ?? null,
        )
        if (availability.statusCheckFailed) {
          setTillsError('Some till sessions could not be verified. Only verified open sessions can be used.')
        }
        try {
          await cacheOpenTillSession(authenticatedUser, availability)
        } catch (error) {
          if (active) {
            setTillsError(`Till sessions loaded, but offline recovery could not be saved: ${getApiErrorMessage(error)}`)
          }
        }
      } catch {
        if (!active) return
        try {
          const cached = await getOfflineOperationQueue().getOpenTillSession(
            authenticatedUser.organization_id,
            authenticatedUser.id,
          )
          if (!active) return
          if (cached) {
            setUsingCachedTillSession(true)
            setAssignedTills([cached.till])
            setOpenableTills([])
            setBusyTills([])
            setAvailableTills([cached.till])
            setOpenSessionIds({ [cached.till.id]: cached.sessionId })
            setManagerOpenSessions([])
            setManagerCloseTillId('')
            setSelectedTill(cached.till)
            setTillsError('Using the last verified open till session from this device. The server must confirm any pending sale after reconnection.')
            return
          }
        } catch (error) {
          if (active) {
            setTillsError(`Till sessions and cached session recovery are unavailable: ${getApiErrorMessage(error)}`)
          }
          return
        }
        setAssignedTills([])
        setOpenableTills([])
        setBusyTills([])
        setAvailableTills([])
        setOpenSessionIds({})
        setManagerOpenSessions([])
        setManagerCloseTillId('')
        setSelectedTill(null)
        setTillsError('Till sessions could not be loaded and no verified session is cached on this device.')
      } finally {
        if (active) setTillsLoading(false)
      }
    }

    void loadAvailableTills()
    return () => {
      active = false
    }
  }, [user?.id, user?.organization_id, setSelectedTill])

  function applyTillAvailability(availability: TillAvailability) {
    setUsingCachedTillSession(false)
    setAssignedTills(availability.assignedTills)
    setOpenableTills(availability.openableTills)
    setBusyTills(availability.busyTills)
    setAvailableTills(availability.openTills)
    setOpenSessionIds(availability.openSessionIds)
    setManagerOpenSessions(availability.managerOpenSessions)
    setManagerCloseTillId((current) =>
      availability.managerOpenSessions.some(({ till }) => till.id === current)
        ? current
        : availability.managerOpenSessions[0]?.till.id ?? '',
    )
    setOpenTillId((current) =>
      availability.openableTills.some((till) => till.id === current)
        ? current
        : availability.openableTills[0]?.id ?? '',
    )
    const currentTill = useAppContextStore.getState().selectedTill
    setSelectedTill(
      availability.openTills.find((till) => till.id === currentTill?.id)
        ?? availability.openTills[0]
        ?? null,
    )
    setTillsError(
      availability.statusCheckFailed
        ? 'Some till sessions could not be verified. Only verified open sessions can be used.'
        : '',
    )
    if (user) {
      void cacheOpenTillSession(user, availability).catch((error) => {
        setTillsError(`Till state changed, but offline recovery could not be saved: ${getApiErrorMessage(error)}`)
      })
    }
  }

  async function refreshTillAvailabilitySafely(currentUser: User) {
    try {
      applyTillAvailability(await fetchTillAvailability(currentUser))
    } catch {
      setOpenableTills([])
      setBusyTills([])
      setAvailableTills([])
      setOpenSessionIds({})
      setManagerOpenSessions([])
      setManagerCloseTillId('')
      setOpenTillId('')
      setSelectedTill(null)
      setTillsError('Till session state could not be verified. Checkout is disabled until status can be refreshed.')
    }
  }

  async function handleOpenTill(event: FormEvent) {
    event.preventDefault()
    if (!user || openTillId === '') return

    setTillActionLoading(true)
    setTillActionError('')
    setTillActionMessage('')
    try {
      await tillsAPI.openSession(openTillId, Number(openingBalance))
      applyTillAvailability(await fetchTillAvailability(user))
      setOpeningBalance('0')
      setTillActionMessage('Till session opened. You can now complete sales.')
    } catch (error) {
      setTillActionError(getApiErrorMessage(error))
      await refreshTillAvailabilitySafely(user)
    } finally {
      setTillActionLoading(false)
    }
  }

  async function submitTillClose(
    tillId: number,
    sessionId: number,
    countedBalance: string,
    notes: string,
  ) {
    if (!user) return
    setTillActionLoading(true)
    setTillActionError('')
    setTillActionMessage('')
    try {
      const response = await tillsAPI.closeSession(
        tillId,
        sessionId,
        Number(countedBalance),
        notes.trim() || undefined,
      )
      const reconciliation = response.data
      applyTillAvailability(await fetchTillAvailability(user))
      setClosingBalance((current) => tillId === activeTill?.id ? '0' : current)
      setClosingNotes((current) => tillId === activeTill?.id ? '' : current)
      setManagerClosingBalance((current) => tillId === managerCloseTillId ? '0' : current)
      setManagerClosingNotes((current) => tillId === managerCloseTillId ? '' : current)
      setTillActionMessage(
        `Till closed. Expected ${reconciliation.currency_code} ${reconciliation.expected_closing_balance.toFixed(2)}, counted ${reconciliation.closing_balance.toFixed(2)}, variance ${reconciliation.cash_variance.toFixed(2)}.`,
      )
    } catch (error) {
      setTillActionError(getApiErrorMessage(error))
      await refreshTillAvailabilitySafely(user)
    } finally {
      setTillActionLoading(false)
    }
  }

  async function handleCloseTill(event: FormEvent) {
    event.preventDefault()
    if (!activeTill) return
    const sessionId = openSessionIds[activeTill.id]
    if (sessionId !== undefined) {
      await submitTillClose(activeTill.id, sessionId, closingBalance, closingNotes)
    }
  }

  async function handleManagerCloseTill(event: FormEvent) {
    event.preventDefault()
    const selectedSession = managerClosableSessions.find(
      ({ till }) => till.id === selectedManagerCloseTillId,
    )?.session
    if (selectedManagerCloseTillId === '' || selectedSession?.session_id == null) return
    await submitTillClose(
      selectedManagerCloseTillId,
      selectedSession.session_id,
      managerClosingBalance,
      managerClosingNotes,
    )
  }

  useEffect(() => {
    if (!user) return
    const organizationId = user.organization_id
    let active = true
    async function cacheOfflineChoices() {
      try {
        const [products, locations] = await Promise.all([
          (async () => {
            const result = []
            let skip = 0
            let total = 0
            do {
              const page = await productsAPI_v2.list({
                organization_id: organizationId,
                include_inactive: false,
                skip,
                limit: 100,
              })
              result.push(...page.data.items)
              total = page.data.total
              skip += page.data.items.length
            } while (skip < total && skip > 0)
            return result
          })(),
          (async () => {
            const page = await locationsAPI.list(organizationId, 0, 100)
            return page.data.items
          })(),
        ])
        if (!active) return
        await getOfflineOperationQueue().saveCatalog({
          organizationId,
          cachedAt: Date.now(),
          products: products.map(({ id, name, sku, unit_of_measure }) => ({
            id, name, sku, unit_of_measure: unit_of_measure || 'each',
          })),
          locations: locations.map(({ id, name, code }) => ({ id, name, code: code || '' })),
        })
      } catch {
        // Keep the last tenant-scoped catalog cache for offline inventory capture.
      }
    }
    void cacheOfflineChoices()
    return () => { active = false }
  }, [user?.id, user?.organization_id])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoginLoading(true)
    setLoginMessage('')
    setLoginError(false)

    try {
      const response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        const detail = typeof data.detail === 'string' ? data.detail : response.statusText
        throw new Error(detail || 'Unable to sign in.')
      }

      setAuth(data.user, data.access_token)
      setScreen('inventory')
      setLoginMessage('')
    } catch (error) {
      setLoginError(true)
      setLoginMessage(error instanceof Error ? error.message : 'Unable to sign in. Please try again.')
    } finally {
      setLoginLoading(false)
    }
  }

  function handleLogout() {
    logout()
    clearContext()
    setScreen('inventory')
    setEmail('')
    setPassword('')
  }

  if (!authInitialized) {
    return <main className="min-h-screen bg-gray-50 p-8 text-center text-gray-600">Restoring your session…</main>
  }

  if (!user) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 px-4 py-12">
        <div className="mx-auto max-w-md">
          <div className="mb-6 text-center">
            <h1 className="text-3xl font-bold text-gray-900">Tenga Inventory POS</h1>
            <p className="mt-2 text-sm text-gray-600">Sign in to manage inventory or use the point of sale.</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4 rounded-lg bg-white p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-gray-900">Sign in</h2>
            <label className="block text-sm font-medium text-gray-700">
              Email
              <input
                type="email"
                autoComplete="username"
                className="mt-1 w-full rounded border px-3 py-2"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Password
              <input
                type="password"
                autoComplete="current-password"
                className="mt-1 w-full rounded border px-3 py-2"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            <div className="flex items-center justify-between gap-4">
              <button
                type="submit"
                disabled={loginLoading}
                className="rounded bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
              >
                {loginLoading ? 'Signing in…' : 'Sign in'}
              </button>
              <a className="text-sm text-indigo-600 hover:underline" href="/docs" target="_blank" rel="noreferrer">
                API docs
              </a>
            </div>
            {loginMessage && (
              <p role={loginError ? 'alert' : 'status'} className={`text-sm ${loginError ? 'text-red-700' : 'text-green-700'}`}>
                {loginMessage}
              </p>
            )}
          </form>
        </div>
      </main>
    )
  }

  const canManageEmployees = user.role === 'admin' || user.role === 'manager'
  const navigation = [
    ...(user.role === 'admin' ? [{ id: 'setup' as const, label: 'Setup' }] : []),
    ...(canManageEmployees ? [{ id: 'employees' as const, label: 'Employees & tills' }] : []),
    ...SCREENS,
  ]
  const currentScreen = navigation.some((item) => item.id === screen) ? screen : 'inventory'
  const activeTill = availableTills.find((till) => till.id === selectedTill?.id) ?? null
  const managerClosableSessions = managerOpenSessions.filter(({ till, session }) =>
    !(session.operator_id === user.id && availableTills.some((item) => item.id === till.id)),
  )
  const selectedManagerCloseTillId = managerClosableSessions.some(
    ({ till }) => till.id === managerCloseTillId,
  )
    ? managerCloseTillId
    : managerClosableSessions[0]?.till.id ?? ''

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">Tenga Inventory POS</h1>
            <p className="text-sm text-gray-600">
              {user.username} · {user.role} · Organization {user.organization_id}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <OfflineSyncStatus organizationId={user.organization_id} compact />
            <nav aria-label="Main navigation" className="flex flex-wrap gap-2">
              {navigation.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-current={currentScreen === item.id ? 'page' : undefined}
                  onClick={() => setScreen(item.id)}
                  className={`rounded-md px-3 py-2 text-sm font-medium ${
                    currentScreen === item.id
                      ? 'bg-indigo-100 text-indigo-800'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </nav>
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-md border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main>
        {currentScreen === 'setup' && user.role === 'admin' && (
          <SetupWizard user={user} onManageEmployeeAssignments={() => setScreen('employees')} />
        )}
        {currentScreen === 'employees' && canManageEmployees && <EmployeeTillAssignments user={user} />}
        {currentScreen === 'inventory' && (
          <InventoryOverview
            onAddProduct={() => setScreen('product')}
            onCountStock={() => { setOperationsView('count'); setScreen('operations') }}
            onImportCsv={() => { setOperationsView('import'); setScreen('operations') }}
            onOpenOperations={() => { setOperationsView('receipt'); setScreen('operations') }}
            onManageProduct={(productId) => {
              setOperationsProductId(productId)
              setOperationsView('history')
              setScreen('operations')
            }}
          />
        )}
        {currentScreen === 'operations' && (
          <InventoryOperations initialView={operationsView} initialProductId={operationsProductId} />
        )}
        {currentScreen === 'product' && (
          <AddProduct onCancel={() => setScreen('inventory')} onCreated={() => setScreen('inventory')} />
        )}
        {currentScreen === 'pos' && (
          <section className="mx-auto max-w-7xl px-4 py-6">
            <div className="mb-4 flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-semibold text-gray-900">
                  {activeTill ? `Active till session · ${activeTill.name}` : 'Till session'}
                </h2>
                <p className="text-sm text-gray-600">
                  Checkout requires an open session assigned to your employee account.
                </p>
              </div>
              {availableTills.length > 0 && (
                <label className="text-sm font-medium text-gray-700">
                  Till
                  <select
                    value={activeTill?.id ?? ''}
                    onChange={(event) => {
                      const till = availableTills.find((item) => item.id === Number(event.target.value)) ?? null
                      setSelectedTill(till)
                    }}
                    className="ml-2 min-w-48 rounded-md border border-gray-300 bg-white px-3 py-2"
                  >
                    {availableTills.map((till) => (
                      <option key={till.id} value={till.id}>{till.name}</option>
                    ))}
                  </select>
                </label>
              )}
            </div>
            {tillsLoading && <p role="status" className="mb-4 text-sm text-gray-600">Checking till sessions…</p>}
            {tillsError && (
              <p role="alert" className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                {tillsError}
              </p>
            )}
            {tillActionMessage && (
              <p role="status" className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-900">
                {tillActionMessage}
              </p>
            )}
            {tillActionError && (
              <p role="alert" className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
                {tillActionError}
              </p>
            )}
            {!tillsLoading && !activeTill ? (
              <div className="rounded-lg border border-gray-200 bg-white p-6">
                {assignedTills.length === 0 ? (
                  <div className="text-center">
                    <h3 className="font-semibold text-gray-900">No tills assigned</h3>
                    <p className="mt-2 text-sm text-gray-600">
                      Ask an administrator to assign an active till to your employee account.
                    </p>
                  </div>
                ) : openableTills.length > 0 ? (
                  <>
                    <h3 className="font-semibold text-gray-900">Open a till session</h3>
                    <p className="mt-1 text-sm text-gray-600">
                      Choose one of your assigned tills and enter its opening cash balance.
                    </p>
                    <form onSubmit={handleOpenTill} className="mt-4 flex flex-col gap-4 sm:max-w-xl">
                      <label className="text-sm font-medium text-gray-700">
                        Assigned till
                        <select
                          required
                          value={openTillId}
                          onChange={(event) => setOpenTillId(Number(event.target.value))}
                          className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2"
                        >
                          {openableTills.map((till) => (
                            <option key={till.id} value={till.id}>{till.name}</option>
                          ))}
                        </select>
                      </label>
                      <label className="text-sm font-medium text-gray-700">
                        Opening cash balance
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          required
                          value={openingBalance}
                          onChange={(event) => setOpeningBalance(event.target.value)}
                          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                        />
                      </label>
                      <button
                        type="submit"
                        disabled={tillActionLoading || openTillId === ''}
                        className="self-start rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-wait disabled:opacity-60"
                      >
                        {tillActionLoading ? 'Opening session…' : 'Open till session'}
                      </button>
                    </form>
                    {busyTills.length > 0 && (
                      <p className="mt-4 text-sm text-amber-800">
                        Already in use by another operator: {busyTills.map((till) => till.name).join(', ')}.
                      </p>
                    )}
                  </>
                ) : (
                  <div className="text-center">
                    <h3 className="font-semibold text-gray-900">No till available to open</h3>
                    <p className="mt-2 text-sm text-gray-600">
                      {busyTills.length > 0
                        ? `Your assigned tills are already open for another operator: ${busyTills.map((till) => till.name).join(', ')}.`
                        : 'Till sessions could not be verified. Reload the page or contact an administrator.'}
                    </p>
                  </div>
                )}
              </div>
            ) : activeTill ? (
              <>
                <form onSubmit={handleCloseTill} className="mb-4 flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4 sm:flex-row sm:items-end">
                  <label className="text-sm font-medium text-gray-700">
                    Closing cash counted
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      required
                      value={closingBalance}
                      onChange={(event) => setClosingBalance(event.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                    />
                  </label>
                  <label className="text-sm font-medium text-gray-700 sm:flex-1">
                    Closing notes (optional)
                    <input
                      type="text"
                      maxLength={500}
                      value={closingNotes}
                      onChange={(event) => setClosingNotes(event.target.value)}
                      className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                    />
                  </label>
                  <button
                    type="submit"
                    disabled={tillActionLoading || usingCachedTillSession || !navigator.onLine}
                    className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-wait disabled:opacity-60"
                  >
                    {tillActionLoading ? 'Closing session…' : 'Close and reconcile till'}
                  </button>
                </form>
                <Checkout tillSessionId={openSessionIds[activeTill.id]} />
              </>
            ) : null}
            {(user.role === 'admin' || user.role === 'manager')
              && managerClosableSessions.length > 0 && (
                <section className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <h3 className="font-semibold text-amber-950">Supervisor session closure</h3>
                  <p className="mt-1 text-sm text-amber-900">
                    Close and reconcile another open till session in this organization. This does not enable checkout as that operator.
                  </p>
                  <form
                    onSubmit={handleManagerCloseTill}
                    className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end"
                  >
                    <label className="text-sm font-medium text-gray-700">
                      Open till session
                      <select
                        required
                        value={selectedManagerCloseTillId}
                        onChange={(event) => setManagerCloseTillId(Number(event.target.value))}
                        className="mt-1 block w-full rounded-md border border-gray-300 bg-white px-3 py-2"
                      >
                        {managerClosableSessions.map(({ till, session }) => (
                          <option key={till.id} value={till.id}>
                            {till.name} · operator #{session.operator_id}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="text-sm font-medium text-gray-700">
                      Closing cash counted
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        required
                        value={managerClosingBalance}
                        onChange={(event) => setManagerClosingBalance(event.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                      />
                    </label>
                    <label className="text-sm font-medium text-gray-700 sm:flex-1">
                      Closing notes (optional)
                      <input
                        type="text"
                        maxLength={500}
                        value={managerClosingNotes}
                        onChange={(event) => setManagerClosingNotes(event.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
                      />
                    </label>
                    <button
                      type="submit"
                      disabled={tillActionLoading || selectedManagerCloseTillId === ''}
                      className="rounded-md border border-amber-300 bg-white px-4 py-2 text-sm font-medium text-amber-950 hover:bg-amber-100 disabled:cursor-wait disabled:opacity-60"
                    >
                      {tillActionLoading ? 'Closing session…' : 'Close and reconcile'}
                    </button>
                  </form>
                </section>
              )}
          </section>
        )}
      </main>
    </div>
  )
}
