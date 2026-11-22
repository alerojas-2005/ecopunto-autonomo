import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getEcoPointCompartments, getEcoPoints } from '../api/catalog'
import { createCollection, getAlerts, getCollections, resolveAlert } from '../api/operations'
import type { AlertSummary, CollectionSummary, CompartmentSummary, EcoPointSummary } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'
import { Button, SectionHeading, StatCard } from './UI'
import './OperationsWorkspace.css'

type Data = { points: EcoPointSummary[]; compartments: CompartmentSummary[]; alerts: AlertSummary[]; collections: CollectionSummary[] }

export function OperationsWorkspace({ role }: { role: 'ADMIN' | 'RECYCLER' }) {
  const { session, logout } = useAuth()
  const [data, setData] = useState<Data | null>(null)
  const [loading, setLoading] = useState(true)
  const [savingId, setSavingId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [pointId, setPointId] = useState('')
  const [compartmentId, setCompartmentId] = useState('')
  const [weightKg, setWeightKg] = useState('')
  const [notes, setNotes] = useState('')
  const [attempt, setAttempt] = useState(0)
  const token = session?.token

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    const load = async () => {
      setLoading(true); setError('')
      try {
        const [points, alerts, collections] = await Promise.all([
          getEcoPoints(token, controller.signal), getAlerts(token, controller.signal), getCollections(token, controller.signal),
        ])
        const compartmentGroups = await Promise.all(points.map(point => getEcoPointCompartments(point.id, token, controller.signal)))
        setData({ points, alerts, collections, compartments: compartmentGroups.flat() })
        setPointId(current => points.some(point => point.id === current) ? current : points[0]?.id ?? '')
      } catch (reason) {
        if (controller.signal.aborted) return
        if (reason instanceof ApiError && reason.isUnauthorized) logout()
        else setError(apiMessage(reason))
        setData(null)
      } finally { if (!controller.signal.aborted) setLoading(false) }
    }
    void load()
    return () => controller.abort()
  }, [token, logout, attempt])

  const pointNames = useMemo(() => new Map(data?.points.map(point => [point.id, point.name]) ?? []), [data])
  const compartmentById = useMemo(() => new Map(data?.compartments.map(item => [item.id, item]) ?? []), [data])
  const availableCompartments = data?.compartments.filter(item => item.ecopoint_id === pointId && item.active) ?? []
  const pendingAlerts = data?.alerts.filter(alert => alert.status === 'ACTIVE') ?? []
  const resolve = async (alert: AlertSummary) => {
    if (!token || savingId) return
    setSavingId(alert.id); setError(''); setNotice('')
    try {
      await resolveAlert(alert.id, token)
      setNotice('Alerta resuelta.')
      setAttempt(value => value + 1)
    } catch (reason) {
      if (reason instanceof ApiError && reason.isUnauthorized) logout()
      else setError(apiMessage(reason))
    } finally { setSavingId('') }
  }

  const submitCollection = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || !pointId || !compartmentId || !weightKg || savingId) return
    setSavingId('collection'); setError(''); setNotice('')
    try {
      await createCollection({ ecopoint_id: pointId, compartment_id: compartmentId, weight_kg: weightKg, notes: notes.trim() || null }, token)
      setWeightKg(''); setNotes(''); setNotice('Recolección registrada.')
      setAttempt(value => value + 1)
    } catch (reason) {
      if (reason instanceof ApiError && reason.isUnauthorized) logout()
      else setError(apiMessage(reason))
    } finally { setSavingId('') }
  }

  return <section className="operations-workspace">
    <div className="operations-toolbar"><div><span className="eyebrow">{role === 'ADMIN' ? 'VISTA GLOBAL' : 'ÁMBITO DE TU UNIVERSIDAD'}</span><strong>Operación conectada a EcoPunto</strong></div><Button type="button" variant="secondary" onClick={() => { setLoading(true); setAttempt(value => value + 1) }} disabled={loading}><Icon name="refresh" size={15}/> Actualizar</Button></div>
    {error && <p className="operations-message error" role="alert">{error}</p>}{notice && <p className="operations-message success" role="status">{notice}</p>}
    {loading && <p className="operations-state" role="status">Consultando EcoPuntos, alertas y recolecciones…</p>}
    {!loading && data && <>
      <div className="operations-stats"><StatCard label="EcoPuntos" value={String(data.points.length)} detail="En el ámbito permitido" icon="bins"/><StatCard label="Alertas activas" value={String(pendingAlerts.length)} detail="Requieren revisión" icon="bell" tone="amber"/><StatCard label="Recolecciones" value={String(data.collections.length)} detail="Registros consultados" icon="truck" tone="mint"/></div>
      <div className="operations-grid"><section className="panel operations-panel"><SectionHeading eyebrow="SEGUIMIENTO" title="Alertas"/><div className="operations-list">{data.alerts.length === 0 ? <p className="operations-state">No hay alertas registradas.</p> : data.alerts.map(alert => { const compartment = compartmentById.get(alert.compartment_id); return <article className="operations-row" key={alert.id}><span className={`operations-indicator ${alert.status === 'ACTIVE' ? 'pending' : ''}`}><Icon name="bell" size={17}/></span><div><strong>{alert.message}</strong><small>{pointNames.get(compartment?.ecopoint_id ?? '') ?? 'EcoPunto'} · {compartment?.label ?? 'Compartimento'} · {new Date(alert.created_at).toLocaleString('es-CO')}</small></div><span className={`operations-status ${alert.status === 'ACTIVE' ? 'pending' : ''}`}>{alert.status === 'ACTIVE' ? 'Activa' : 'Resuelta'}</span>{alert.status === 'ACTIVE' && <button type="button" className="operations-action" disabled={Boolean(savingId)} onClick={() => void resolve(alert)}>{savingId === alert.id ? 'Guardando…' : 'Resolver'}</button>}</article> })}</div></section>
        <section className="panel operations-panel"><SectionHeading eyebrow="REGISTROS DE API" title="Recolecciones"/><div className="operations-list">{data.collections.length === 0 ? <p className="operations-state">No hay recolecciones registradas.</p> : data.collections.map(item => { const compartment = compartmentById.get(item.compartment_id); return <article className="operations-row" key={item.id}><span className="operations-indicator"><Icon name="truck" size={17}/></span><div><strong>{pointNames.get(item.ecopoint_id) ?? 'EcoPunto'} · {compartment?.label ?? 'Compartimento'}</strong><small>{new Date(item.created_at).toLocaleString('es-CO')}{item.notes ? ` · ${item.notes}` : ''}</small></div><span className="operations-weight">{Number(item.weight_kg).toLocaleString('es-CO')} kg</span></article> })}</div></section></div>
      {role === 'RECYCLER' && <section className="panel collection-form-panel"><SectionHeading eyebrow="RECOLECCIÓN INSTITUCIONAL" title="Registrar una recolección"/><form className="collection-form" onSubmit={submitCollection}><label>EcoPunto<select value={pointId} onChange={event => { setPointId(event.target.value); setCompartmentId('') }} required><option value="">Selecciona EcoPunto</option>{data.points.filter(point => point.active).map(point => <option key={point.id} value={point.id}>{point.name}</option>)}</select></label><label>Compartimento<select value={compartmentId} onChange={event => setCompartmentId(event.target.value)} required><option value="">Selecciona compartimento</option>{availableCompartments.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>Peso recolectado (kg)<input type="number" min="0.001" max="9999999.999" step="0.001" value={weightKg} onChange={event => setWeightKg(event.target.value)} required/></label><label>Notas (opcional)<input value={notes} onChange={event => setNotes(event.target.value)} maxLength={1000}/></label><Button type="submit" disabled={!pointId || !compartmentId || !weightKg || savingId === 'collection'}>{savingId === 'collection' ? 'Registrando…' : 'Registrar recolección'}</Button></form></section>}
    </>}
  </section>
}

export function RecyclerOverview({ onNavigate }: { onNavigate: () => void }) {
  const { session, logout } = useAuth()
  const [summary, setSummary] = useState<{ points: EcoPointSummary[]; alerts: AlertSummary[]; collections: CollectionSummary[] } | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    if (!session?.token) return
    const controller = new AbortController()
    void Promise.all([getEcoPoints(session.token, controller.signal), getAlerts(session.token, controller.signal), getCollections(session.token, controller.signal)])
      .then(([points, alerts, collections]) => setSummary({ points, alerts, collections }))
      .catch((reason: unknown) => { if (!controller.signal.aborted) { if (reason instanceof ApiError && reason.isUnauthorized) logout(); else setError(apiMessage(reason)) } })
    return () => controller.abort()
  }, [session?.token, logout, attempt])
  return <section className="recycler-overview"><div className="operations-toolbar"><div><span className="eyebrow">ÁMBITO DE TU UNIVERSIDAD</span><strong>Resumen de operaciones</strong></div><Button type="button" variant="secondary" onClick={() => setAttempt(value => value + 1)}><Icon name="refresh" size={15}/> Actualizar</Button></div>{error && <p className="operations-message error" role="alert">{error}</p>}{!summary ? <p className="operations-state" role="status">{error ? 'No se pudo cargar el resumen.' : 'Consultando la API…'}</p> : <><div className="operations-stats"><StatCard label="EcoPuntos activos" value={String(summary.points.filter(point => point.active).length)} detail="De tu universidad" icon="bins"/><StatCard label="Alertas activas" value={String(summary.alerts.filter(alert => alert.status === 'ACTIVE').length)} detail="Pendientes de gestión" icon="bell" tone="amber"/><StatCard label="Recolecciones" value={String(summary.collections.length)} detail="Tus registros operativos" icon="truck" tone="mint"/></div><section className="panel recycler-next"><SectionHeading eyebrow="SIGUIENTE PASO" title="Gestiona la operación"><Button type="button" onClick={onNavigate}>Abrir alertas y recolecciones <Icon name="arrow" size={15}/></Button></SectionHeading><p>Consulta las alertas de tu universidad, resuelve las que ya atendiste y registra recolecciones desde un EcoPunto habilitado.</p></section></>}</section>
}

function apiMessage(error: unknown) {
  return error instanceof Error ? error.message : 'No fue posible consultar la API.'
}
