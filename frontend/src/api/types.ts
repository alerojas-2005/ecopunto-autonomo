export type UserRole = 'CITIZEN' | 'ADMIN' | 'RECYCLER'

export interface UserProfile {
  id: string
  full_name: string
  email: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData extends LoginCredentials {
  full_name: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// Pydantic serializes Python Decimal values as JSON strings.
export type ApiDecimal = string

export interface EcoPointSummary {
  id: string
  code: string
  name: string
  address: string
  active: boolean
  created_at: string
}

export interface MaterialSummary {
  id: string
  name: string
  description: string | null
  points_per_gram: ApiDecimal
  active: boolean
}

export interface CompartmentSummary {
  id: string
  ecopoint_id: string
  material_id: string
  label: string
  capacity_kg: ApiDecimal
  current_kg: ApiDecimal
  fill_threshold_pct: number
  active: boolean
  fill_percentage: ApiDecimal
}

export interface AuthSession {
  token: string
  user: UserProfile
}
