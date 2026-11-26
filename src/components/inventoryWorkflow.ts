import type { OfflineOperation, OfflineOperationType } from '../offline/operationQueue'

export type InventoryActionInput =
  | {
      operationType: 'INVENTORY_RECEIPT' | 'INVENTORY_ISSUE'
      product_id: number
      location_id: number
      quantity: number
      reason: string
      unit_cost?: number
    }
  | {
      operationType: 'INVENTORY_ADJUSTMENT'
      product_id: number
      location_id: number
      quantity: number
      reason: string
    }
  | {
      operationType: 'INVENTORY_TRANSFER'
      source_location_id: number
      destination_location_id: number
      lines: Array<{ product_id: number; quantity: number }>
      reason: string
    }
  | {
      operationType: 'INVENTORY_COUNT'
      location_id: number
      lines: Array<{ product_id: number; observed_quantity: number | null }>
      notes?: string
    }

export function toQueuedInventoryOperation(input: InventoryActionInput): {
  operationType: OfflineOperationType
  payload: Record<string, unknown>
} {
  const { operationType, ...payload } = input
  return { operationType, payload }
}

export function buildCountLines(
  productIds: number[],
  observedQuantities: Record<number, string>,
): Array<{ product_id: number; observed_quantity: number | null }> {
  return productIds.map((product_id) => {
    const raw = observedQuantities[product_id]?.trim() ?? ''
    return {
      product_id,
      observed_quantity: raw === '' ? null : Number(raw),
    }
  })
}

export function provisionalStockDelta(
  operation: OfflineOperation,
  productId: number,
  locationId: number,
): number {
  if (operation.status !== 'PENDING' && operation.status !== 'RETRYABLE_FAILURE') return 0
  const payload = operation.payload
  if (operation.operationType === 'INVENTORY_RECEIPT') {
    return payload.product_id === productId && payload.location_id === locationId
      ? Number(payload.quantity) || 0
      : 0
  }
  if (operation.operationType === 'INVENTORY_ISSUE') {
    return payload.product_id === productId && payload.location_id === locationId
      ? -(Number(payload.quantity) || 0)
      : 0
  }
  if (operation.operationType === 'INVENTORY_ADJUSTMENT') {
    return payload.product_id === productId && payload.location_id === locationId
      ? Number(payload.quantity) || 0
      : 0
  }
  if (operation.operationType === 'INVENTORY_TRANSFER') {
    const total = (payload.lines as Array<{ product_id: number; quantity: number }> | undefined)
      ?.filter((line) => line.product_id === productId)
      .reduce((sum, line) => sum + line.quantity, 0) ?? 0
    if (payload.source_location_id === locationId) return -total
    if (payload.destination_location_id === locationId) return total
  }
  return 0
}

export function operationStatusLabel(operation: OfflineOperation): string {
  if (operation.acknowledgement?.reconciliationResolvedAt) return 'Reconciled'
  switch (operation.status) {
    case 'PENDING': return 'Pending'
    case 'RETRYABLE_FAILURE': return 'Retryable failure'
    case 'SYNCED': return 'Applied'
    case 'TERMINAL_FAILURE': return 'Terminal failure'
    case 'RECONCILIATION_REQUIRED': return 'Reconciliation required'
  }
}
