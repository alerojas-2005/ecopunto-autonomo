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
  university_id: string
}

export interface UniversityRegistrationOption {
  id: string
  name: string
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

export interface EcoPointCreate {
  code: string
  name: string
  address: string
  active: boolean
}

export type EcoPointPatch = Partial<EcoPointCreate>

export interface MaterialCreate {
  name: string
  description: string | null
  points_per_gram: ApiDecimal
  active: boolean
}

export type MaterialPatch = Partial<MaterialCreate>

export interface CompartmentCreate {
  material_id: string
  label: string
  capacity_kg: ApiDecimal
  current_kg: ApiDecimal
  fill_threshold_pct: number
  active: boolean
}

export interface CompartmentPatch {
  label?: string
  capacity_kg?: ApiDecimal
  fill_threshold_pct?: number
  active?: boolean
}

export interface DepositCreate {
  ecopoint_id: string
  compartment_id: string
  material_id: string
  weight_g: number
}

export interface DepositSummary extends DepositCreate {
  id: string
  citizen_id: string
  factor_applied: ApiDecimal
  points_awarded: ApiDecimal
  created_at: string
}

export interface BalanceSummary {
  balance: ApiDecimal
}

export interface PointTransactionSummary {
  id: string
  user_id: string
  deposit_id: string | null
  type: 'EARN' | 'REDEEM' | string
  amount: ApiDecimal
  description: string
  created_at: string
}

export interface AuthSession {
  token: string
  user: UserProfile
}
