import { apiGet, apiPost } from './client'
import type { LoginCredentials, RegisterData, TokenResponse, UserProfile } from './types'

export function registerCitizen(data: RegisterData): Promise<UserProfile> {
  return apiPost<UserProfile, RegisterData>('/auth/register', data)
}

export function login(credentials: LoginCredentials): Promise<TokenResponse> {
  return apiPost<TokenResponse, LoginCredentials>('/auth/login', credentials)
}

export function getCurrentUser(token: string): Promise<UserProfile> {
  return apiGet<UserProfile>('/users/me', token)
}
