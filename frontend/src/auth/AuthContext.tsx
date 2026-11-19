import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { ApiError } from '../api/client'
import { getCurrentUser, login as loginRequest, registerCitizen } from '../api/auth'
import type { AuthSession, LoginCredentials, RegisterData } from '../api/types'
import { AuthContext } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [loading, setLoading] = useState(false)

  const establishSession = useCallback(async (credentials: LoginCredentials) => {
    const tokenResponse = await loginRequest(credentials)
    if (tokenResponse.token_type.toLowerCase() !== 'bearer') {
      throw new Error('El servidor devolvió un tipo de token no compatible.')
    }
    const user = await getCurrentUser(tokenResponse.access_token)
    setSession({ token: tokenResponse.access_token, user })
  }, [])

  const login = useCallback(async (credentials: LoginCredentials) => {
    setLoading(true)
    try {
      await establishSession(credentials)
    } catch (error) {
      setSession(null)
      throw error
    } finally {
      setLoading(false)
    }
  }, [establishSession])

  const register = useCallback(async (data: RegisterData) => {
    setLoading(true)
    try {
      await registerCitizen(data)
      await establishSession({ email: data.email, password: data.password })
    } catch (error) {
      setSession(null)
      if (error instanceof ApiError && error.status === 401) {
        throw new Error('La cuenta se creó, pero no se pudo iniciar la sesión. Intenta ingresar con tus datos.', { cause: error })
      }
      throw error
    } finally {
      setLoading(false)
    }
  }, [establishSession])

  const logout = useCallback(() => setSession(null), [])

  const refreshProfile = useCallback(async () => {
    if (!session) return null
    setLoading(true)
    try {
      const user = await getCurrentUser(session.token)
      setSession(current => current ? { ...current, user } : null)
      return user
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) setSession(null)
      throw error
    } finally {
      setLoading(false)
    }
  }, [session])

  const value = useMemo(() => ({ session, loading, login, register, logout, refreshProfile }), [session, loading, login, register, logout, refreshProfile])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
