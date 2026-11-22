import { apiGet } from './client'
import type { UniversityRegistrationOption } from './types'

export function getRegistrationOptions(signal?: AbortSignal): Promise<UniversityRegistrationOption[]> {
  return apiGet<UniversityRegistrationOption[]>('/universities/registration-options', undefined, signal)
}
