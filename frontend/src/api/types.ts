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

export interface AuthSession {
  token: string
  user: UserProfile
}
