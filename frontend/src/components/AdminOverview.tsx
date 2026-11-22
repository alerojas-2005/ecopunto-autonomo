import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import { getEcoPoints } from '../api/catalog'
import { getUsers } from '../api/auth'
import { getAlerts, getCollections } from '../api/operations'
import { getUniversities } from '../api/universities'
import type { AlertSummary, CollectionSummary, EcoPointSummary, UniversitySummary, UserProfile } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'
import { Button, SectionHeading, StatCard } from './UI'
import './AdminOverview.css'

type OverviewData = { points: EcoPointSummary[]; universities: UniversitySummary[]; users: UserProfile[]; alerts: AlertSummary[]; collections: CollectionSummary[] }

export function AdminOverview({ onNavigate }: { onNavigate: (view: 'Gestión de EcoPuntos' | 'Universidades y usuarios' | 'Alertas y recolecciones') => void }) {
  const { session, logout } = useAuth()
  const [data, setData] = useState<OverviewData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!session?.token) return
    const controller = new AbortController()
    void Promise.all([
      getEcoPoints(session.token, controller.signal), getUniversities(session.token, controller.signal),
      getUsers(session.token, controller.signal), getAlerts(session.token, controller.signal),
      getCollections(session.token, controller.signal),
    ]).then(([points, universities, users, alerts, collections]) => {
      setData({ points, universities, users, alerts, collections }); setError('')
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return
      if (reason instanceof ApiError && reason.isUnauthorized) logout()
      else setError(reason instanceof Error ? reason.message : 'No fue posible cargar el resumen.')
      setData(null)
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [session?.token, logout, attempt])

  const activeAlerts = useMemo(() => data?.alerts.filter(alert => alert.status === 'ACTIVE') ?? [], [data])
  const monthCollections = useMemo(() => data?.collections.filter(item => {
    const date = new Date(item.created_at); const now = new Date()
    return date.getFullYear() === now.getFullYear() && date.getMonth() === now.getMonth()
  }) ?? [], [data])
  const collectedKg = monthCollections.reduce((total, item) => total + Number(item.weight_kg), 0)

  return <section className="admin-overview">
    <div className="admin-overview-toolbar"><span className="api-live-label"><i/>Datos del backend</span><Button type="button" variant="secondary" onClick={() => { setLoading(true); setAttempt(value => value + 1) }} disabled={loading}><Icon name="refresh" size={15}/> Actualizar</Button></div>
    {loading && <p className="admin-overview-state" role="status">Consultando la plataforma…</p>}
    {error && <p className="admin-overview-error" role="alert">No se pudo cargar el resumen: {error} <button type="button" onClick={() => { setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></p>}
    {!loading && data && <>
      <div className="stats-grid admin-stats"><StatCard label="EcoPuntos activos" value={String(data.points.filter(point => point.active).length)} detail="Red global" icon="bins"/><StatCard label="Universidades activas" value={String(data.universities.filter(university => university.active).length)} detail="Instituciones habilitadas" icon="home" tone="mint"/><StatCard label="Alertas activas" value={String(activeAlerts.length)} detail="En toda la plataforma" icon="bell" tone="amber"/><StatCard label="Usuarios" value={String(data.users.length)} detail="Máximo 500 consultados" icon="points" tone="blue"/></div>
      <section className="admin-overview-grid"><div className="panel admin-overview-panel"><SectionHeading eyebrow="RED GLOBAL" title="EcoPuntos recientes"><button type="button" className="text-link" onClick={() => onNavigate('Gestión de EcoPuntos')}>Gestionar <Icon name="arrow" size={15}/></button></SectionHeading>{data.points.length === 0 ? <p className="admin-overview-state">No hay EcoPuntos registrados.</p> : <div className="admin-overview-list">{data.points.slice(0, 5).map(point => <div className="admin-overview-row" key={point.id}><span className="overview-icon"><Icon name="bins" size={17}/></span><div><strong>{point.name}</strong><small>{point.address} · {point.code}</small></div><span className={`overview-state ${point.active ? 'active' : ''}`}>{point.active ? 'Activo' : 'Inactivo'}</span></div>)}</div>}</div>
        <div className="panel admin-overview-panel"><SectionHeading eyebrow="REQUIERE ATENCIÓN" title="Alertas activas"><button type="button" className="text-link" onClick={() => onNavigate('Alertas y recolecciones')}>Ver todas <Icon name="arrow" size={15}/></button></SectionHeading>{activeAlerts.length === 0 ? <p className="admin-overview-state">No hay alertas activas.</p> : <div className="admin-overview-list">{activeAlerts.slice(0, 5).map(alert => <div className="admin-overview-row" key={alert.id}><span className="overview-icon amber"><Icon name="bell" size={17}/></span><div><strong>{alert.message}</strong><small>{new Date(alert.created_at).toLocaleString('es-CO')}</small></div><span className="overview-state warning">Activa</span></div>)}</div>}</div></section>
      <div className="panel admin-collection-summary"><div><span className="eyebrow">ACTIVIDAD DEL MES</span><strong>{collectedKg.toLocaleString('es-CO', { maximumFractionDigits: 3 })} kg</strong><small>{monthCollections.length} recolecciones registradas este mes</small></div><Button type="button" variant="secondary" onClick={() => onNavigate('Alertas y recolecciones')}>Consultar recolecciones <Icon name="arrow" size={15}/></Button></div>
    </>}
  </section>
}
