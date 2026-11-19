import { apiGet, apiPost } from './client'
import type { DepositCreate, DepositSummary } from './types'

export function createDeposit(payload: DepositCreate, token: string): Promise<DepositSummary> {
  return apiPost<DepositSummary, DepositCreate>('/deposits', payload, token)
}

export function getMyDeposits(token: string, signal?: AbortSignal): Promise<DepositSummary[]> {
  return apiGet<DepositSummary[]>('/deposits/me', token, signal)
}
