import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import type { LoginCredentials, RegisterData } from '../api/types'
import { useAuth } from './useAuth'
import { Icon } from '../components/Icon'
import { Button } from '../components/UI'
import './Auth.css'

type AuthMode = 'login' | 'register'

export function AuthPage() {
  const { login, register, loading } = useAuth()
  const [mode, setMode] = useState<AuthMode>('login')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  const switchMode = (nextMode: AuthMode) => {
    setMode(nextMode)
    setErrorMessage('')
    setPassword('')
    setConfirmPassword('')
  }

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setErrorMessage('')

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setErrorMessage('Ingresa un correo electrónico válido.')
      return
    }
    if (password.length === 0) {
      setErrorMessage('Ingresa tu contraseña.')
      return
    }

    if (mode === 'register') {
      if (fullName.trim().length === 0) {
        setErrorMessage('Ingresa tu nombre completo.')
        return
      }
      if (password.length < 12) {
        setErrorMessage('La contraseña debe tener al menos 12 caracteres.')
        return
      }
      if (password !== confirmPassword) {
        setErrorMessage('Las contraseñas no coinciden.')
        return
      }
    }

    try {
      if (mode === 'register') {
        const data: RegisterData = { full_name: fullName.trim(), email: email.trim(), password }
        await register(data)
      } else {
        const credentials: LoginCredentials = { email: email.trim(), password }
        await login(credentials)
      }
    } catch (error) {
      setErrorMessage(error instanceof ApiError || error instanceof Error
        ? error.message
        : 'Ocurrió un error. Intenta nuevamente.')
    }
  }

  return <main className="auth-layout">
    <section className="auth-story" aria-label="EcoPunto">
      <div className="auth-brand"><div className="brand-mark"><Icon name="leaf" size={22} /></div><span>Eco<span>Punto</span></span></div>
      <div className="auth-story-copy"><span className="auth-kicker"><Icon name="recycle" size={15} /> ECONOMÍA CIRCULAR, MÁS CERCA</span><h1>Pequeñas acciones.<br />Un futuro más limpio.</h1><p>Registra tus aportes, sigue tu impacto y sé parte de una comunidad que transforma la forma de reciclar.</p></div>
      <div className="auth-story-art" aria-hidden="true"><div className="auth-art-circle"/><div className="auth-art-orbit auth-art-orbit-one"/><div className="auth-art-orbit auth-art-orbit-two"/><div className="auth-art-leaf auth-art-leaf-one"><Icon name="leaf" size={75}/></div><div className="auth-art-leaf auth-art-leaf-two"><Icon name="leaf" size={56}/></div><div className="auth-art-spark"><Icon name="points" size={34}/></div></div>
      <div className="auth-story-footer"><span className="online-dot"/> Una experiencia virtual para cuidar lo que compartimos.</div>
    </section>

    <section className="auth-form-side">
      <div className="auth-form-wrap">
        <div className="auth-heading"><span className="eyebrow">{mode === 'login' ? 'QUÉ BUENO VERTE DE NUEVO' : 'COMIENZA A SUMAR'}</span><h2>{mode === 'login' ? 'Inicia sesión' : 'Crea tu cuenta'}</h2><p>{mode === 'login' ? 'Ingresa para continuar con EcoPunto.' : 'Regístrate como ciudadano para empezar.'}</p></div>
        <form className="auth-form" onSubmit={onSubmit} noValidate>
          {mode === 'register' && <label className="auth-field"><span>Nombre completo</span><input autoComplete="name" value={fullName} onChange={event => setFullName(event.target.value)} maxLength={120} placeholder="Ej. María Rodríguez" required /></label>}
          <label className="auth-field"><span>Correo electrónico</span><input type="email" autoComplete="email" value={email} onChange={event => setEmail(event.target.value)} maxLength={254} placeholder="nombre@correo.com" required /></label>
          <label className="auth-field"><span>Contraseña</span><input type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} minLength={mode === 'register' ? 12 : 1} maxLength={128} placeholder={mode === 'register' ? 'Mínimo 12 caracteres' : 'Ingresa tu contraseña'} required /><small>{mode === 'register' ? 'Usa al menos 12 caracteres.' : 'Se enviará al backend de EcoPunto para validación.'}</small></label>
          {mode === 'register' && <label className="auth-field"><span>Confirma tu contraseña</span><input type="password" autoComplete="new-password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} maxLength={128} placeholder="Repite tu contraseña" required /></label>}
          {errorMessage && <div className="auth-error" role="alert"><Icon name="info" size={17}/><span>{errorMessage}</span></div>}
          <Button className="auth-submit" type="submit" disabled={loading}>{loading && <span className="button-spinner" aria-hidden="true"/>}{loading ? 'Conectando…' : mode === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}{!loading && <Icon name="arrow" size={17}/>}</Button>
        </form>
        <div className="auth-switch">{mode === 'login' ? '¿Todavía no tienes una cuenta?' : '¿Ya tienes una cuenta?'} <button type="button" onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Regístrate' : 'Inicia sesión'}</button></div>
        <div className="auth-note"><Icon name="check" size={15}/><span>Al registrarte se crea una cuenta de ciudadano. Los roles administrativos los asigna el sistema.</span></div>
      </div>
      <footer className="auth-footer">EcoPunto <span>·</span> Plataforma virtual de economía circular</footer>
    </section>
  </main>
}
