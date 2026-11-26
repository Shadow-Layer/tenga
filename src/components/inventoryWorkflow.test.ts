import { describe, expect, it } from 'vitest'
import {
  buildCountLines,
  operationStatusLabel,
  provisionalStockDelta,
  toQueuedInventoryOperation,
} from './inventoryWorkflow'
import type { OfflineOperation } from '../offline/operationQueue'

function operation(
  operationType: OfflineOperation['operationType'],
  payload: Record<string, unknown>,
  status: OfflineOperation['status'] = 'PENDING',
): OfflineOperation {
  return {
    operationId: 'local-1',
    organizationId: 1,
    deviceId: 'device-1',
    operationType,
    payload,
    sequence: 1,
    createdAt: 1,
    status,
    attemptCount: 0,
    lastError: null,
    acknowledgement: null,
  }
}

describe('inventory workflow transitions', () => {
  it('builds a receipt payload with no client-supplied tenant, actor, or device identity', () => {
    expect(toQueuedInventoryOperation({
      operationType: 'INVENTORY_RECEIPT',
      product_id: 8,
      location_id: 2,
      quantity: 5,
      unit_cost: 3.25,
      reason: 'Supplier delivery',
    })).toEqual({
      operationType: 'INVENTORY_RECEIPT',
      payload: {
        product_id: 8,
        location_id: 2,
        quantity: 5,
        unit_cost: 3.25,
        reason: 'Supplier delivery',
      },
    })
  })

  it('preserves unobserved products as null, distinct from a counted zero', () => {
    expect(buildCountLines([1, 2, 3], { 1: '4', 2: '', 3: '0' })).toEqual([
      { product_id: 1, observed_quantity: 4 },
      { product_id: 2, observed_quantity: null },
      { product_id: 3, observed_quantity: 0 },
    ])
  })

  it('shows only unapplied receipt, issue, adjustment, and transfer deltas as provisional', () => {
    expect(provisionalStockDelta(operation('INVENTORY_RECEIPT', {
      product_id: 5, location_id: 2, quantity: 7,
    }), 5, 2)).toBe(7)
    expect(provisionalStockDelta(operation('INVENTORY_ISSUE', {
      product_id: 5, location_id: 2, quantity: 3,
    }), 5, 2)).toBe(-3)
    expect(provisionalStockDelta(operation('INVENTORY_ADJUSTMENT', {
      product_id: 5, location_id: 2, quantity: -2,
    }), 5, 2)).toBe(-2)
    const transfer = operation('INVENTORY_TRANSFER', {
      source_location_id: 2,
      destination_location_id: 3,
      lines: [{ product_id: 5, quantity: 4 }],
    })
    expect(provisionalStockDelta(transfer, 5, 2)).toBe(-4)
    expect(provisionalStockDelta(transfer, 5, 3)).toBe(4)
    expect(provisionalStockDelta(operation('INVENTORY_COUNT', {
      location_id: 2, lines: [{ product_id: 5, observed_quantity: 1 }],
    }), 5, 2)).toBe(0)
    expect(provisionalStockDelta(operation('INVENTORY_RECEIPT', {
      product_id: 5, location_id: 2, quantity: 7,
    }, 'SYNCED'), 5, 2)).toBe(0)
  })

  it('distinguishes reconciliation-required from explicitly reconciled local history', () => {
    const count = operation('INVENTORY_COUNT', {}, 'RECONCILIATION_REQUIRED')
    count.acknowledgement = { status: 'RECONCILIATION_REQUIRED' }
    expect(operationStatusLabel(count)).toBe('Reconciliation required')
    count.acknowledgement.reconciliationResolvedAt = '2026-01-01T00:00:00.000Z'
    expect(operationStatusLabel(count)).toBe('Reconciled')
    const terminal = operation('INVENTORY_ISSUE', {}, 'TERMINAL_FAILURE')
    expect(operationStatusLabel(terminal)).toBe('Terminal failure')
  })
})
