import { describe, expect, it } from 'vitest'
import type { Employee } from '../api'
import { getEmployeeTillAccess } from './employeeAssignmentLogic'

const linkedEmployee: Employee = {
  id: 8,
  organization_id: 21,
  employee_number: 'CASH-08',
  full_name: 'Till Operator',
  email: null,
  phone: null,
  title: null,
  user_id: 13,
  is_active: true,
  archived_at: null,
  location_ids: [5],
  till_ids: [34],
  created_at: '',
  updated_at: '',
}

describe('employee access required for a till', () => {
  it('does not treat a login as an employee unless the active profile links it', () => {
    expect(getEmployeeTillAccess([], 13, 34)).toBe('missing-employee')
    expect(getEmployeeTillAccess([{ ...linkedEmployee, user_id: null }], 13, 34)).toBe('missing-employee')
    expect(getEmployeeTillAccess([{ ...linkedEmployee, is_active: false }], 13, 34)).toBe('missing-employee')
    expect(getEmployeeTillAccess([{ ...linkedEmployee, archived_at: '2026-01-01' }], 13, 34)).toBe('missing-employee')
  })

  it('requires an assigned till before an employee can operate it', () => {
    expect(getEmployeeTillAccess([linkedEmployee], 13, 0)).toBe('missing-till-assignment')
    expect(getEmployeeTillAccess([linkedEmployee], 13, 35)).toBe('missing-till-assignment')
  })

  it('accepts the authenticated employee when they are assigned to the selected till', () => {
    expect(getEmployeeTillAccess([linkedEmployee], 13, 34)).toBe('ready')
  })
})
