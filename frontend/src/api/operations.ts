import { apiGet, apiPatch, apiPost } from './client'
import type { AlertSummary, CollectionCreate, CollectionSummary } from './types'

export function getAlerts(token: string, signal?: AbortSignal): Promise<AlertSummary[]> {
  return apiGet<AlertSummary[]>('/alerts', token, signal)
}

export function resolveAlert(id: string, token: string): Promise<AlertSummary> {
  return apiPatch<AlertSummary, Record<string, never>>(`/alerts/${encodeURIComponent(id)}/resolve`, {}, token)
}

export function getCollections(token: string, signal?: AbortSignal): Promise<CollectionSummary[]> {
  return apiGet<CollectionSummary[]>('/collections', token, signal)
}

export function createCollection(payload: CollectionCreate, token: string): Promise<CollectionSummary> {
  return apiPost<CollectionSummary, CollectionCreate>('/collections', payload, token)
}
