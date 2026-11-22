import { apiGet, apiPost } from './client'
import type { DepositCreate, DepositSummary } from './types'

export type DepositFilters = {
  university_id?: string
  user_id?: string
  material_id?: string
  from_date?: string
  to_date?: string
}

export function createDeposit(payload: DepositCreate, token: string): Promise<DepositSummary> {
  return apiPost<DepositSummary, DepositCreate>('/deposits', payload, token)
}

export function getMyDeposits(token: string, signal?: AbortSignal): Promise<DepositSummary[]> {
  return apiGet<DepositSummary[]>('/deposits/me', token, signal)
}

export function getDeposits(token: string, filters: DepositFilters = {}, signal?: AbortSignal): Promise<DepositSummary[]> {
  const params = new URLSearchParams({ limit: '500' })
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  return apiGet<DepositSummary[]>(`/deposits?${params.toString()}`, token, signal)
}
