import {
  IndexedDbOfflineOperationQueue,
  type OfflineOperation,
  type OperationAcknowledgement,
  type ServerAcknowledgementStatus,
} from './operationQueue'

export interface SyncOperationRequest {
  operation_id: string
  operation_type: OfflineOperation['operationType']
  payload: Record<string, unknown>
}

export interface OfflineSyncRequest {
  device_id: string
  organization_id: number
  operations: SyncOperationRequest[]
}

export interface ServerOperationAcknowledgement {
  operation_id: string
  status: ServerAcknowledgementStatus
  applied_entity_type?: string | null
  applied_entity_id?: string | number | null
  error_code?: string | null
  error_message?: string | null
}

export interface OfflineSyncResponse {
  device_id: string
  organization_id: number
  acknowledgements: ServerOperationAcknowledgement[]
}

export type SyncSubmitter = (request: OfflineSyncRequest) => Promise<OfflineSyncResponse>

export interface SyncResult {
  attempted: number
  synced: number
  retryable: number
  terminal: number
  reconciliationRequired: number
}

const validStatuses = new Set<ServerAcknowledgementStatus>([
  'APPLIED',
  'RETRYABLE_FAILURE',
  'TERMINAL_FAILURE',
  'RECONCILIATION_REQUIRED',
])

function acknowledgementForQueue(
  acknowledgement: ServerOperationAcknowledgement,
): OperationAcknowledgement {
  if (!validStatuses.has(acknowledgement.status)) {
    throw new Error(`Unknown acknowledgment status for ${acknowledgement.operation_id}`)
  }
  return {
    status: acknowledgement.status,
    appliedEntityType: acknowledgement.applied_entity_type,
    appliedEntityId: acknowledgement.applied_entity_id,
    errorCode: acknowledgement.error_code,
    errorMessage: acknowledgement.error_message,
  }
}

function errorMessage(error: unknown): string {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof error.response === 'object' &&
    error.response !== null &&
    'data' in error.response &&
    typeof error.response.data === 'object' &&
    error.response.data !== null &&
    'detail' in error.response.data &&
    typeof error.response.data.detail === 'string'
  ) {
    return error.response.data.detail
  }
  return error instanceof Error ? error.message : 'Sync transport failed'
}

export async function syncQueuedOperations(
  queue: IndexedDbOfflineOperationQueue,
  organizationId: number,
  submit: SyncSubmitter,
  limit = 100,
): Promise<SyncResult> {
  const operations = await queue.listSyncable(organizationId, limit)
  const result: SyncResult = {
    attempted: operations.length,
    synced: 0,
    retryable: 0,
    terminal: 0,
    reconciliationRequired: 0,
  }
  if (operations.length === 0) return result

  const deviceId = await queue.getDeviceId()
  const request: OfflineSyncRequest = {
    device_id: deviceId,
    organization_id: organizationId,
    operations: operations.map((operation) => ({
      operation_id: operation.operationId,
      operation_type: operation.operationType,
      payload: operation.payload,
    })),
  }

  let response: OfflineSyncResponse
  try {
    response = await submit(request)
  } catch (error) {
    await queue.markBatchRetryable(organizationId, operations, errorMessage(error))
    result.retryable = operations.length
    return result
  }

  if (response.device_id !== deviceId || response.organization_id !== organizationId) {
    await queue.markBatchRetryable(
      organizationId,
      operations,
      'Sync response organization or device did not match the request.',
    )
    result.retryable = operations.length
    return result
  }

  const acknowledgements = new Map<string, ServerOperationAcknowledgement[]>()
  for (const acknowledgement of response.acknowledgements ?? []) {
    const matches = acknowledgements.get(acknowledgement.operation_id) ?? []
    matches.push(acknowledgement)
    acknowledgements.set(acknowledgement.operation_id, matches)
  }

  for (const operation of operations) {
    const matching = acknowledgements.get(operation.operationId) ?? []
    if (matching.length !== 1) {
      await queue.acknowledge(organizationId, operation.operationId, {
        status: 'RETRYABLE_FAILURE',
        errorCode: 'MISSING_OR_DUPLICATE_ACK',
        errorMessage: 'The server did not return exactly one acknowledgment for this operation.',
      })
      result.retryable += 1
      continue
    }

    try {
      const acknowledgement = acknowledgementForQueue(matching[0])
      await queue.acknowledge(organizationId, operation.operationId, acknowledgement)
      switch (acknowledgement.status) {
        case 'APPLIED':
          result.synced += 1
          break
        case 'RETRYABLE_FAILURE':
          result.retryable += 1
          break
        case 'TERMINAL_FAILURE':
          result.terminal += 1
          break
        case 'RECONCILIATION_REQUIRED':
          result.reconciliationRequired += 1
          break
      }
    } catch (error) {
      await queue.acknowledge(organizationId, operation.operationId, {
        status: 'RETRYABLE_FAILURE',
        errorCode: 'INVALID_ACKNOWLEDGEMENT',
        errorMessage: errorMessage(error),
      })
      result.retryable += 1
    }
  }
  return result
}
