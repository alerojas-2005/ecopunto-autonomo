import { apiGet } from './client'
import type { BalanceSummary, PointTransactionSummary } from './types'

export function getPointsBalance(token: string, signal?: AbortSignal): Promise<BalanceSummary> {
  return apiGet<BalanceSummary>('/points/balance', token, signal)
}

export function getPointTransactions(token: string, signal?: AbortSignal): Promise<PointTransactionSummary[]> {
  return apiGet<PointTransactionSummary[]>('/points/transactions', token, signal)
}
