import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createUser, getUsers, updateUser } from '../api/auth'
import { getUniversities, updateUniversity } from '../api/universities'
import type { UniversitySummary, UserProfile, UserRole } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'
import { Button } from './UI'
import './AdminManagement.css'

type Tab = 'universities' | 'users'
type UserDraft = { email: string; full_name: string; password: string; role: UserRole; university_id: string; is_active: boolean }
const blankUser: UserDraft = { email: '', full_name: '', password: '', role: 'CITIZEN', university_id: '', is_active: true }
// Los usuarios de plataforma se crean por el flujo seguro de bootstrap, no desde este formulario.
const assignableRoles: UserRole[] = ['CITIZEN', 'RECYCLER']

export function AdminManagement() {
  const { session, logout } = useAuth()
  const token = session?.token
  const [tab, setTab] = useState<Tab>('universities')
  const [universities, setUniversities] = useState<UniversitySummary[]>([])
  const [users, setUsers] = useState<UserProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editingId, setEditingId] = useState('')
  const [draft, setDraft] = useState<UserDraft>(blankUser)
  const [createOpen, setCreateOpen] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    const fetchData = async () => {
      try {
        const [universityItems, userItems] = await Promise.all([
          getUniversities(token, controller.signal), getUsers(token, controller.signal),
        ])
        if (controller.signal.aborted) return
        setUniversities(universityItems)
        setUsers(userItems)
        setError('')
      } catch (reason) {
        if (!controller.signal.aborted) setError(message(reason, logout))
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    }
    void fetchData()
    return () => controller.abort()
  }, [token, logout, attempt])
  const toggleUniversity = async (university: UniversitySummary, field: 'active' | 'public_registration_enabled') => {
    if (!token || saving) return
    setSaving(true); setError(''); setNotice('')
    try {
      const updated = await updateUniversity(university.id, { [field]: !university[field] }, token)
      setUniversities(items => items.map(item => item.id === updated.id ? updated : item))
      setNotice('Universidad actualizada.')
    } catch (reason) { setError(message(reason, logout)) } finally { setSaving(false) }
  }

  const beginEdit = (user: UserProfile) => {
    setEditingId(user.id)
    setCreateOpen(false)
    setDraft({ email: user.email, full_name: user.full_name, password: '', role: user.role, university_id: user.university_id ?? '', is_active: user.is_active })
    setError(''); setNotice('')
  }

  const submitUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || saving) return
    if (draft.role !== 'ADMIN' && !draft.university_id) { setError('Selecciona una universidad para CITIZEN o RECYCLER.'); return }
    setSaving(true); setError(''); setNotice('')
    try {
      if (editingId) {
        await updateUser(editingId, {
          email: draft.email.trim(), full_name: draft.full_name.trim(), role: draft.role,
          university_id: draft.role === 'ADMIN' ? null : draft.university_id,
          is_active: draft.is_active,
        }, token)
        setNotice('Usuario actualizado.')
      } else {
        await createUser({
          email: draft.email.trim(), full_name: draft.full_name.trim(), password: draft.password,
          role: draft.role, university_id: draft.role === 'ADMIN' ? null : draft.university_id,
        }, token)
        setNotice('Usuario creado.')
      }
      setEditingId(''); setCreateOpen(false); setDraft(blankUser)
      setLoading(true); setAttempt(value => value + 1)
    } catch (reason) { setError(message(reason, logout)) } finally { setSaving(false) }
  }

  if (session?.user.role !== 'ADMIN') return <section className="panel" role="alert">Esta pantalla requiere una sesión ADMIN.</section>

  return <section className="admin-management">
    <header className="admin-management-header"><div><span className="eyebrow">ADMINISTRACIÓN GLOBAL</span><h2>Universidades y usuarios</h2><p>Gestiona el catálogo institucional y las cuentas desde la API.</p></div><div className="admin-management-tabs" role="tablist" aria-label="Administración"><button role="tab" aria-selected={tab === 'universities'} onClick={() => setTab('universities')}>Universidades <span>{universities.length}</span></button><button role="tab" aria-selected={tab === 'users'} onClick={() => setTab('users')}>Usuarios <span>{users.length}</span></button></div></header>
    {error && <div className="admin-management-message error" role="alert"><Icon name="info" size={16}/>{error}<button onClick={() => setError('')}>Cerrar</button></div>}
    {notice && <div className="admin-management-message success" role="status"><Icon name="check" size={16}/>{notice}</div>}
    {loading ? <p className="admin-management-state" role="status">Consultando la API…</p> : tab === 'universities' ? <section className="panel admin-management-panel"><div className="admin-management-caption"><strong>Instituciones registradas</strong><span>{universities.length} universidades</span></div>{universities.length === 0 ? <p className="admin-management-state">No hay universidades disponibles.</p> : <div className="admin-management-table-wrap"><table><thead><tr><th>Universidad</th><th>Sede / ciudad</th><th>Estado</th><th>Registro público</th></tr></thead><tbody>{universities.map(university => <tr key={university.id}><td><strong>{university.name}</strong><small>{university.slug}</small></td><td>{university.campus_name}<small>{university.city}</small></td><td><button className={`admin-toggle ${university.active ? 'on' : ''}`} disabled={saving} onClick={() => void toggleUniversity(university, 'active')}>{university.active ? 'Activa' : 'Inactiva'}</button></td><td><button className={`admin-toggle ${university.public_registration_enabled ? 'on' : ''}`} disabled={saving || !university.active} onClick={() => void toggleUniversity(university, 'public_registration_enabled')}>{university.public_registration_enabled ? 'Habilitado' : 'Deshabilitado'}</button></td></tr>)}</tbody></table></div>}</section> : <section className="panel admin-management-panel">
      <div className="admin-management-caption"><strong>Cuentas de la plataforma</strong><span>{users.length} usuarios consultados (máximo 500)</span><Button type="button" onClick={() => { setCreateOpen(true); setEditingId(''); setDraft(blankUser); setError(''); setNotice('') }}>+ Crear usuario</Button></div>
      {(createOpen || editingId) && <form className="admin-user-form" onSubmit={submitUser}><div className="admin-user-form-title"><strong>{editingId ? 'Editar usuario' : 'Crear usuario'}</strong><button type="button" onClick={() => { setCreateOpen(false); setEditingId(''); setDraft(blankUser) }}>Cancelar</button></div><div className="admin-user-form-grid"><label>Nombre completo<input value={draft.full_name} onChange={event => setDraft({ ...draft, full_name: event.target.value })} maxLength={120} required/></label><label>Correo electrónico<input type="email" autoComplete="email" value={draft.email} onChange={event => setDraft({ ...draft, email: event.target.value })} maxLength={254} required/></label>{!editingId && <label>Contraseña<input type="password" autoComplete="new-password" value={draft.password} onChange={event => setDraft({ ...draft, password: event.target.value })} minLength={12} maxLength={128} required/><small>Mínimo 12 caracteres. Comunica la contraseña al usuario por un canal seguro.</small></label>}{editingId && draft.role === 'ADMIN' ? <label>Rol<input value="ADMIN" readOnly/></label> : <label>Rol<select value={draft.role} onChange={event => setDraft({ ...draft, role: event.target.value as UserRole })} required>{assignableRoles.map(role => <option key={role} value={role}>{roleLabel(role)}</option>)}</select></label>}{draft.role !== 'ADMIN' && <label>Universidad<select value={draft.university_id} onChange={event => setDraft({ ...draft, university_id: event.target.value })} required><option value="">Selecciona universidad activa</option>{universities.filter(item => item.active).map(university => <option key={university.id} value={university.id}>{university.name}</option>)}</select></label>}{editingId && <label className="admin-active-check"><input type="checkbox" checked={draft.is_active} onChange={event => setDraft({ ...draft, is_active: event.target.checked })}/> Cuenta activa</label>}</div><Button type="submit" disabled={saving || (!editingId && universities.every(item => !item.active))}>{saving ? 'Guardando…' : editingId ? 'Guardar cambios' : 'Crear usuario'}</Button></form>}
      {users.length === 0 ? <p className="admin-management-state">No hay usuarios registrados.</p> : <div className="admin-management-table-wrap"><table><thead><tr><th>Usuario</th><th>Rol</th><th>Universidad</th><th>Estado</th><th/></tr></thead><tbody>{users.map(user => <tr key={user.id}><td><strong>{user.full_name}</strong><small>{user.email}</small></td><td>{roleLabel(user.role)}</td><td>{universities.find(item => item.id === user.university_id)?.name ?? (user.role === 'ADMIN' ? 'Plataforma global' : 'Sin universidad')}</td><td><span className={`admin-user-status ${user.is_active ? 'active' : ''}`}>{user.is_active ? 'Activo' : 'Inactivo'}</span></td><td><button className="admin-edit-link" type="button" onClick={() => beginEdit(user)}>Editar</button></td></tr>)}</tbody></table></div>}
    </section>}
  </section>
}

function roleLabel(role: UserRole) {
  return role === 'ADMIN' ? 'ADMIN' : role === 'RECYCLER' ? 'RECYCLER' : 'CITIZEN'
}

function message(error: unknown, logout: () => void) {
  if (error instanceof ApiError) {
    if (error.isUnauthorized) { logout(); return 'La sesión expiró. Inicia sesión de nuevo.' }
    return error.message
  }
  return error instanceof Error ? error.message : 'No fue posible completar la operación.'
}
