import { apiClient } from '../api'
import type { OfflineSyncRequest, OfflineSyncResponse, SyncSubmitter } from './syncService'

export const submitOfflineSyncBatch: SyncSubmitter = async (
  request: OfflineSyncRequest,
): Promise<OfflineSyncResponse> => {
  const response = await apiClient.post<OfflineSyncResponse>('/api/v1/sync/batch', request)
  return response.data
}
