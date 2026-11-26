import type { Employee } from '../api'

export type EmployeeTillAccess = 'ready' | 'missing-employee' | 'missing-till-assignment'

export function getEmployeeTillAccess(
  employees: Employee[],
  userId: number,
  tillId: number | null,
): EmployeeTillAccess {
  if (!tillId) return 'missing-till-assignment'
  const employee = employees.find(
    (item) => item.user_id === userId && item.is_active && item.archived_at === null,
  )
  if (!employee) return 'missing-employee'
  return employee.till_ids.includes(tillId) ? 'ready' : 'missing-till-assignment'
}
