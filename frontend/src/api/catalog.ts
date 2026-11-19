import { apiGet } from './client'
import type { CompartmentSummary, EcoPointSummary, MaterialSummary } from './types'

export function getEcoPoints(token: string, signal?: AbortSignal): Promise<EcoPointSummary[]> {
  return apiGet<EcoPointSummary[]>('/ecopoints', token, signal)
}

export function getMaterials(token: string, signal?: AbortSignal): Promise<MaterialSummary[]> {
  return apiGet<MaterialSummary[]>('/materials', token, signal)
}

export function getEcoPointCompartments(ecopointId: string, token: string, signal?: AbortSignal): Promise<CompartmentSummary[]> {
  return apiGet<CompartmentSummary[]>(`/ecopoints/${encodeURIComponent(ecopointId)}/compartments`, token, signal)
}
