import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getUsers } from '../api/auth'
import { getDeposits, type DepositFilters } from '../api/deposits'
import { getMaterials, getEcoPoints } from '../api/catalog'
import { getUniversities } from '../api/universities'
import type { DepositSummary, EcoPointSummary, MaterialSummary, UniversitySummary, UserProfile } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'
import { Button } from './UI'
import './AdminDeposits.css'

type FilterForm = { university_id: string; user_id: string; material_id: string; from_date: string; to_date: string }
const emptyFilters: FilterForm = { university_id: '', user_id: '', material_id: '', from_date: '', to_date: '' }

export function AdminDeposits() {
  const { session, logout } = useAuth()
  const token = session?.token
  const [deposits, setDeposits] = useState<DepositSummary[]>([])
  const [users, setUsers] = useState<UserProfile[]>([])
  const [universities, setUniversities] = useState<UniversitySummary[]>([])
  const [points, setPoints] = useState<EcoPointSummary[]>([])
  const [materials, setMaterials] = useState<MaterialSummary[]>([])
  const [filterForm, setFilterForm] = useState<FilterForm>(emptyFilters)
  const [filters, setFilters] = useState<DepositFilters>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    void Promise.all([
      getDeposits(token, filters, controller.signal), getUsers(token, controller.signal),
      getUniversities(token, controller.signal), getEcoPoints(token, controller.signal),
      getMaterials(token, controller.signal),
    ]).then(([depositItems, userItems, universityItems, pointItems, materialItems]) => {
      setDeposits(depositItems); setUsers(userItems); setUniversities(universityItems)
      setPoints(pointItems); setMaterials(materialItems); setError('')
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return
      if (reason instanceof ApiError && reason.isUnauthorized) logout()
      else setError(reason instanceof Error ? reason.message : 'No fue posible consultar los depósitos.')
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [token, logout, filters])

  const applyFilters = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true); setError('')
    setFilters({
      university_id: filterForm.university_id || undefined,
      user_id: filterForm.user_id || undefined,
      material_id: filterForm.material_id || undefined,
      from_date: filterForm.from_date ? new Date(filterForm.from_date).toISOString() : undefined,
      to_date: filterForm.to_date ? new Date(filterForm.to_date).toISOString() : undefined,
    })
  }
  const clearFilters = () => { setFilterForm(emptyFilters); setFilters({}); setLoading(true); setError('') }
  const usersById = new Map(users.map(user => [user.id, user]))
  const pointsById = new Map(points.map(point => [point.id, point]))
  const materialsById = new Map(materials.map(material => [material.id, material]))

  if (session?.user.role !== 'ADMIN') return <section className="panel" role="alert">Esta pantalla requiere una sesión ADMIN.</section>

  return <section className="admin-deposits panel"><header className="admin-deposits-heading"><div><span className="eyebrow">CONSULTA GLOBAL</span><h2>Depósitos</h2><p>El ámbito y los filtros se aplican en el backend.</p></div><span>{loading ? 'Consultando…' : `${deposits.length} registros (máximo 500)`}</span></header>
    <form className="admin-deposit-filters" onSubmit={applyFilters}><label>Universidad<select value={filterForm.university_id} onChange={event => setFilterForm({ ...filterForm, university_id: event.target.value })}><option value="">Todas</option>{universities.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Usuario<select value={filterForm.user_id} onChange={event => setFilterForm({ ...filterForm, user_id: event.target.value })}><option value="">Todos</option>{users.map(item => <option key={item.id} value={item.id}>{item.full_name} · {item.role}</option>)}</select></label><label>Material<select value={filterForm.material_id} onChange={event => setFilterForm({ ...filterForm, material_id: event.target.value })}><option value="">Todos</option>{materials.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label><label>Desde<input type="datetime-local" value={filterForm.from_date} onChange={event => setFilterForm({ ...filterForm, from_date: event.target.value })}/></label><label>Hasta<input type="datetime-local" value={filterForm.to_date} onChange={event => setFilterForm({ ...filterForm, to_date: event.target.value })}/></label><div className="admin-deposit-filter-actions"><Button type="submit" disabled={loading}><Icon name="check" size={14}/> Filtrar</Button><Button type="button" variant="secondary" onClick={clearFilters}>Limpiar</Button></div></form>
    {error && <p className="admin-deposits-error" role="alert">{error}</p>}{loading && <p className="admin-deposits-state" role="status">Consultando depósitos de la API…</p>}
    {!loading && !error && deposits.length === 0 && <p className="admin-deposits-state">No hay depósitos para estos filtros.</p>}
    {!loading && !error && deposits.length > 0 && <div className="admin-deposits-table-wrap"><table><thead><tr><th>Ciudadano</th><th>Universidad</th><th>EcoPunto</th><th>Material</th><th>Peso</th><th>Puntos</th><th>Fecha</th></tr></thead><tbody>{deposits.map(deposit => { const citizen = usersById.get(deposit.citizen_id); const point = pointsById.get(deposit.ecopoint_id); return <tr key={deposit.id}><td>{citizen?.full_name ?? 'Usuario'}</td><td>{universities.find(uni => uni.id === citizen?.university_id)?.name ?? '—'}</td><td>{point?.name ?? 'EcoPunto'}</td><td>{deposit.material_id ? materialsById.get(deposit.material_id)?.name ?? 'Material' : 'No identificado'}</td><td>{(deposit.weight_g / 1000).toLocaleString('es-CO', { maximumFractionDigits: 3 })} kg</td><td>{Number(deposit.points_awarded).toLocaleString('es-CO', { maximumFractionDigits: 4 })}</td><td>{new Date(deposit.created_at).toLocaleString('es-CO')}</td></tr> })}</tbody></table></div>}
  </section>
}
