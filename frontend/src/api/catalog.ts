import { apiGet, apiPatch, apiPost } from './client'
import type {
  CompartmentCreate,
  CompartmentPatch,
  CompartmentSummary,
  EcoPointCreate,
  EcoPointPatch,
  EcoPointSummary,
  MaterialCreate,
  MaterialPatch,
  MaterialSummary,
} from './types'

export function getEcoPoints(token: string, signal?: AbortSignal): Promise<EcoPointSummary[]> {
  return apiGet<EcoPointSummary[]>('/ecopoints', token, signal)
}

export function getMaterials(token: string, signal?: AbortSignal): Promise<MaterialSummary[]> {
  return apiGet<MaterialSummary[]>('/materials', token, signal)
}

export function getEcoPointCompartments(ecopointId: string, token: string, signal?: AbortSignal): Promise<CompartmentSummary[]> {
  return apiGet<CompartmentSummary[]>(`/ecopoints/${encodeURIComponent(ecopointId)}/compartments`, token, signal)
}

export function createEcoPoint(payload: EcoPointCreate, token: string): Promise<EcoPointSummary> {
  return apiPost<EcoPointSummary, EcoPointCreate>('/ecopoints', payload, token)
}

export function updateEcoPoint(ecopointId: string, payload: EcoPointPatch, token: string): Promise<EcoPointSummary> {
  return apiPatch<EcoPointSummary, EcoPointPatch>(`/ecopoints/${encodeURIComponent(ecopointId)}`, payload, token)
}

export function createMaterial(payload: MaterialCreate, token: string): Promise<MaterialSummary> {
  return apiPost<MaterialSummary, MaterialCreate>('/materials', payload, token)
}

export function updateMaterial(materialId: string, payload: MaterialPatch, token: string): Promise<MaterialSummary> {
  return apiPatch<MaterialSummary, MaterialPatch>(`/materials/${encodeURIComponent(materialId)}`, payload, token)
}

export function createCompartment(ecopointId: string, payload: CompartmentCreate, token: string): Promise<CompartmentSummary> {
  return apiPost<CompartmentSummary, CompartmentCreate>(`/ecopoints/${encodeURIComponent(ecopointId)}/compartments`, payload, token)
}

export function updateCompartment(compartmentId: string, payload: CompartmentPatch, token: string): Promise<CompartmentSummary> {
  return apiPatch<CompartmentSummary, CompartmentPatch>(`/compartments/${encodeURIComponent(compartmentId)}`, payload, token)
}
