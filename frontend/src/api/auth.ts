import { apiGet, apiPost, apiPatch } from './client'
import type { LoginCredentials, RegisterData, TokenResponse, UserAdminCreate, UserPatch, UserProfile } from './types'

export function registerCitizen(data: RegisterData): Promise<UserProfile> {
  return apiPost<UserProfile, RegisterData>('/auth/register', data)
}

export function login(credentials: LoginCredentials): Promise<TokenResponse> {
  return apiPost<TokenResponse, LoginCredentials>('/auth/login', credentials)
}

export function getCurrentUser(token: string): Promise<UserProfile> {
  return apiGet<UserProfile>('/users/me', token)
}

export function getUsers(token: string, signal?: AbortSignal): Promise<UserProfile[]> {
  return apiGet<UserProfile[]>('/users?limit=500', token, signal)
}

export function createUser(data: UserAdminCreate, token: string): Promise<UserProfile> {
  return apiPost<UserProfile, UserAdminCreate>('/users', data, token)
}

export function updateUser(id: string, patch: UserPatch, token: string): Promise<UserProfile> {
  return apiPatch<UserProfile, UserPatch>(`/users/${encodeURIComponent(id)}`, patch, token)
}
