import { apiGet, apiPatch } from './client'
import type { UniversityPatch, UniversityRegistrationOption, UniversitySummary } from './types'

export function getUniversities(token: string, signal?: AbortSignal): Promise<UniversitySummary[]> {
  return apiGet<UniversitySummary[]>('/universities', token, signal)
}

export function getRegistrationOptions(signal?: AbortSignal): Promise<UniversityRegistrationOption[]> {
  return apiGet<UniversityRegistrationOption[]>('/universities/registration-options', undefined, signal)
}

export function updateUniversity(id: string, patch: UniversityPatch, token: string): Promise<UniversitySummary> {
  return apiPatch<UniversitySummary, UniversityPatch>(`/universities/${encodeURIComponent(id)}`, patch, token)
}
