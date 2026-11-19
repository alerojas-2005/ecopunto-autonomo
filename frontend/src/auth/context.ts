import { createContext } from 'react'
import type { AuthSession, LoginCredentials, RegisterData, UserProfile } from '../api/types'

export interface AuthContextValue {
  session: AuthSession | null
  loading: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
  refreshProfile: () => Promise<UserProfile | null>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
