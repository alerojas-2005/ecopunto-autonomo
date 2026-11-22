export type UserRole = 'CITIZEN' | 'ADMIN' | 'RECYCLER'

export interface UserProfile {
  id: string
  full_name: string
  email: string
  role: UserRole
  university_id: string | null
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

export interface UniversitySummary extends UniversityRegistrationOption {
  slug: string
  city: string
  campus_name: string
  address: string | null
  active: boolean
  public_registration_enabled: boolean
  created_at: string
  updated_at: string
}

export interface UniversityPatch {
  name?: string
  slug?: string
  city?: string
  campus_name?: string
  address?: string | null
  active?: boolean
  public_registration_enabled?: boolean
}

export interface UserAdminCreate {
  email: string
  full_name: string
  password: string
  role: UserRole
  university_id?: string | null
}

export interface UserPatch {
  email?: string
  full_name?: string
  role?: UserRole
  university_id?: string | null
  is_active?: boolean
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
  university_id: string
  code: string
  name: string
  address: string
  active: boolean
}

export interface EcoPointPatch {
  code?: string
  name?: string
  address?: string
  active?: boolean
}

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

export interface DepositSummary {
  id: string
  citizen_id: string
  ecopoint_id: string
  compartment_id: string
  material_id: string | null
  weight_g: number
  factor_applied: ApiDecimal
  points_awarded: ApiDecimal
  created_at: string
}

export type AlertStatus = 'ACTIVE' | 'RESOLVED'

export interface AlertSummary {
  id: string
  compartment_id: string
  type: string
  status: AlertStatus
  message: string
  created_at: string
  resolved_at: string | null
}

export interface CollectionCreate {
  ecopoint_id: string
  compartment_id: string
  weight_kg: ApiDecimal
  notes?: string | null
}

export interface CollectionSummary extends CollectionCreate {
  id: string
  recycler_id: string
  status: string
  created_at: string
  notes: string | null
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
