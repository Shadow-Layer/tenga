import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import {
  apiClient,
  employeesAPI,
  locationsAPI,
  tillsAPI,
  type Employee,
  type Location,
  type Till,
  type User,
} from '../api'

type Props = { user: User }

function errorMessage(error: unknown): string {
  if (typeof error === 'object' && error && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string') return detail
    if (detail) return JSON.stringify(detail)
  }
  return error instanceof Error ? error.message : 'The request failed. Please try again.'
}

export default function EmployeeTillAssignments({ user }: Props) {
  const [employees, setEmployees] = useState<Employee[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [locations, setLocations] = useState<Location[]>([])
  const [tills, setTills] = useState<Till[]>([])
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<number | ''>('')
  const [employeeNumber, setEmployeeNumber] = useState('')
  const [fullName, setFullName] = useState('')
  const [linkedUserId, setLinkedUserId] = useState<number | ''>('')
  const [locationIds, setLocationIds] = useState<number[]>([])
  const [tillIds, setTillIds] = useState<number[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selectedEmployee = useMemo(
    () => employees.find((employee) => employee.id === selectedEmployeeId) ?? null,
    [employees, selectedEmployeeId],
  )

  const loadRecords = useCallback(async () => {
    setLoading(true)
    setLoadError('')
    try {
      const [employeeResponse, userResponse, locationResponse, tillResponse] = await Promise.all([
        employeesAPI.list(user.organization_id),
        apiClient.get<{ items: User[]; total: number }>(`/api/v1/organizations/${user.organization_id}/users`),
        locationsAPI.list(user.organization_id, 0, 100),
        tillsAPI.list(user.organization_id, undefined, 0, 100),
      ])
      setEmployees(employeeResponse.data.items.filter((employee) => employee.is_active))
      setUsers(userResponse.data.items.filter((account) => account.is_active))
      setLocations(locationResponse.data.items)
      setTills(tillResponse.data.items)
    } catch (loadFailure) {
      setLoadError(errorMessage(loadFailure))
    } finally {
      setLoading(false)
    }
  }, [user.organization_id])

  useEffect(() => {
    void loadRecords()
  }, [loadRecords])

  useEffect(() => {
    if (!selectedEmployee) {
      setEmployeeNumber('')
      setFullName('')
      setLinkedUserId('')
      setLocationIds([])
      setTillIds([])
      return
    }
    setEmployeeNumber(selectedEmployee.employee_number)
    setFullName(selectedEmployee.full_name)
    setLinkedUserId(selectedEmployee.user_id ?? '')
    setLocationIds(selectedEmployee.location_ids)
    setTillIds(selectedEmployee.till_ids)
  }, [selectedEmployee])

  function toggleId(value: number, values: number[], setValues: (next: number[]) => void) {
    setValues(values.includes(value) ? values.filter((id) => id !== value) : [...values, value])
  }

  async function saveEmployee(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')

    const unassignedLocations = tills
      .filter((till) => tillIds.includes(till.id) && !locationIds.includes(till.location_id))
      .map((till) => till.name)
    if (unassignedLocations.length > 0) {
      setError(`Assign the location for each selected till before saving: ${unassignedLocations.join(', ')}.`)
      return
    }

    const payload = {
      employee_number: employeeNumber.trim(),
      full_name: fullName.trim(),
      user_id: linkedUserId === '' ? null : Number(linkedUserId),
      location_ids: locationIds,
      till_ids: tillIds,
    }
    if (!payload.employee_number || !payload.full_name) {
      setError('Employee number and full name are required.')
      return
    }

    setSaving(true)
    try {
      const response = selectedEmployee
        ? await employeesAPI.update(user.organization_id, selectedEmployee.id, payload)
        : await employeesAPI.create(user.organization_id, payload)
      setSelectedEmployeeId(response.data.id)
      setEmployeeNumber(response.data.employee_number)
      setFullName(response.data.full_name)
      setLinkedUserId(response.data.user_id ?? '')
      setLocationIds(response.data.location_ids)
      setTillIds(response.data.till_ids)
      setNotice(`Employee ${response.data.full_name} saved with the selected user, location, and till assignments.`)
      await loadRecords()
    } catch (saveFailure) {
      setError(errorMessage(saveFailure))
      await loadRecords()
    } finally {
      setSaving(false)
    }
  }

  if (user.role !== 'admin' && user.role !== 'manager') {
    return <p role="alert" className="m-4 rounded border border-red-200 bg-red-50 p-4 text-red-800">Only an administrator or manager can manage employee assignments.</p>
  }

  return (
    <section className="mx-auto max-w-5xl space-y-5 px-4 py-6">
      <header>
        <h2 className="text-2xl font-bold text-gray-900">Employee and till assignments</h2>
        <p className="mt-1 text-sm text-gray-600">
          Employee profiles are separate from login accounts. Link an existing account explicitly, then assign the employee to the locations and tills they may operate.
        </p>
      </header>

      {loadError && (
        <div role="alert" className="rounded border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <p>Employee assignments could not be loaded: {loadError}</p>
          <button type="button" className="mt-2 font-semibold underline" onClick={() => void loadRecords()} disabled={loading}>
            {loading ? 'Retrying…' : 'Retry loading'}
          </button>
        </div>
      )}
      {error && <p role="alert" className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {notice && <p role="status" className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-800">{notice}</p>}

      {loading ? (
        <p role="status" className="rounded border bg-white p-6 text-gray-600">Loading users, employees, locations, and tills…</p>
      ) : !loadError ? (
        <>
          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <label className="block text-sm font-medium text-gray-700">
              Employee profile
              <select
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
                value={selectedEmployeeId}
                onChange={(event) => {
                  setSelectedEmployeeId(event.target.value ? Number(event.target.value) : '')
                  setError('')
                  setNotice('')
                }}
              >
                <option value="">Create a new employee profile</option>
                {employees.map((employee) => (
                  <option key={employee.id} value={employee.id}>
                    {employee.full_name} · {employee.employee_number}
                  </option>
                ))}
              </select>
            </label>
            {employees.length === 0 && <p className="mt-2 text-sm text-gray-600">No active employee profiles exist yet. Create one below.</p>}
          </div>

          <form onSubmit={saveEmployee} className="space-y-5 rounded-lg border border-gray-200 bg-white p-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block text-sm font-medium text-gray-700">
                Employee number
                <input required value={employeeNumber} onChange={(event) => setEmployeeNumber(event.target.value)} className="mt-1 w-full rounded border border-gray-300 px-3 py-2" />
              </label>
              <label className="block text-sm font-medium text-gray-700">
                Employee full name
                <input required value={fullName} onChange={(event) => setFullName(event.target.value)} className="mt-1 w-full rounded border border-gray-300 px-3 py-2" />
              </label>
            </div>

            <label className="block text-sm font-medium text-gray-700">
              Link login account (optional)
              <select
                value={linkedUserId}
                onChange={(event) => setLinkedUserId(event.target.value ? Number(event.target.value) : '')}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              >
                <option value="">No login account linked</option>
                {users.map((account) => {
                  const linkedElsewhere = employees.some(
                    (employee) => employee.id !== selectedEmployee?.id && employee.user_id === account.id,
                  )
                  return (
                    <option key={account.id} value={account.id} disabled={linkedElsewhere}>
                      {account.full_name || account.username} · {account.email}{linkedElsewhere ? ' · linked to another employee' : ''}
                    </option>
                  )
                })}
              </select>
              <span className="mt-1 block text-xs text-gray-500">A user account is never created or linked automatically.</span>
            </label>

            <fieldset>
              <legend className="text-sm font-semibold text-gray-800">Assigned locations</legend>
              {locations.length === 0 ? <p className="mt-1 text-sm text-gray-600">Create a location before assigning employee access.</p> : (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {locations.map((location) => (
                    <label key={location.id} className="flex items-center gap-2 text-sm text-gray-700">
                      <input type="checkbox" checked={locationIds.includes(location.id)} onChange={() => toggleId(location.id, locationIds, setLocationIds)} />
                      {location.name} · {location.code}
                    </label>
                  ))}
                </div>
              )}
            </fieldset>

            <fieldset>
              <legend className="text-sm font-semibold text-gray-800">Assigned tills</legend>
              {tills.length === 0 ? <p className="mt-1 text-sm text-gray-600">Create a till before assigning employee access.</p> : (
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {tills.map((till) => {
                    const location = locations.find((item) => item.id === till.location_id)
                    return (
                      <label key={till.id} className="flex items-center gap-2 text-sm text-gray-700">
                        <input type="checkbox" checked={tillIds.includes(till.id)} onChange={() => toggleId(till.id, tillIds, setTillIds)} />
                        {till.name} · {till.code} ({location?.name ?? 'Unknown location'})
                      </label>
                    )
                  })}
                </div>
              )}
              <p className="mt-1 text-xs text-gray-500">The till’s location must also be assigned. Saving replaces this employee’s current assignment sets.</p>
            </fieldset>

            <button type="submit" disabled={saving || loading} className="rounded bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50">
              {saving ? 'Saving assignments…' : selectedEmployee ? 'Save employee and assignments' : 'Create employee and assignments'}
            </button>
          </form>
        </>
      ) : null}
    </section>
  )
}
