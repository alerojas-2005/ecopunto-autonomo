import { useEffect, useMemo, useState } from 'react'
import { ApiError } from '../api/client'
import { getEcoPoints, getMaterials } from '../api/catalog'
import { getMyDeposits } from '../api/deposits'
import { getPointsBalance, getPointTransactions } from '../api/points'
import type { BalanceSummary, DepositSummary, EcoPointSummary, MaterialSummary, PointTransactionSummary } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'
import { Button, SectionHeading, StatCard } from './UI'

type DashboardData = {
  balance: BalanceSummary
  deposits: DepositSummary[]
  transactions: PointTransactionSummary[]
  materials: MaterialSummary[]
  ecopoints: EcoPointSummary[]
}

function formatPoints(value: string) {
  return Number(value).toLocaleString('es-CO', { maximumFractionDigits: 4 })
}

function formatWeight(weightGrams: number) {
  return `${(weightGrams / 1000).toLocaleString('es-CO', { maximumFractionDigits: 3 })} kg`
}

export function CitizenDashboard({ onNavigate }: { onNavigate: (view: 'Registrar depósito' | 'Historial') => void }) {
  const { session, logout } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!session?.token) return
    const controller = new AbortController()
    void Promise.all([
      getPointsBalance(session.token, controller.signal),
      getPointTransactions(session.token, controller.signal),
      getMyDeposits(session.token, controller.signal),
      getMaterials(session.token, controller.signal),
      getEcoPoints(session.token, controller.signal),
    ]).then(([balance, transactions, deposits, materials, ecopoints]) => {
      setData({ balance, transactions, deposits, materials, ecopoints })
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return
      if (reason instanceof ApiError && reason.isUnauthorized) {
        logout()
        return
      }
      setData(null)
      setError(reason instanceof Error ? reason.message : 'No fue posible cargar tus datos.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [session?.token, logout, attempt])

  const totalWeight = useMemo(() => data?.deposits.reduce((total, deposit) => total + deposit.weight_g, 0) ?? 0, [data])
  const latestDeposits = useMemo(() => data?.deposits.slice().sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at)).slice(0, 3) ?? [], [data])
  const materialNames = new Map(data?.materials.map(item => [item.id, item.name]) ?? [])
  const ecopointNames = new Map(data?.ecopoints.map(item => [item.id, item.name]) ?? [])
  const transactionByDeposit = new Map(data?.transactions.filter(item => item.deposit_id).map(item => [item.deposit_id as string, item]) ?? [])

  return <>
    <section className="citizen-hero"><div className="hero-copy"><div className="hero-kicker"><Icon name="leaf" size={15} /> TU APORTE HACE LA DIFERENCIA</div><h2>Un planeta más limpio<br />empieza contigo.</h2><p>Consulta aquí los depósitos y EcoPuntos registrados en tu cuenta.</p><Button onClick={() => onNavigate('Registrar depósito')}><Icon name="plus" size={18} /> Registrar un depósito</Button></div><div className="hero-art" aria-hidden="true"><div className="sun-disc"/><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="hero-plant plant-left"><i/><i/><i/></div><div className="hero-plant plant-right"><i/><i/><i/><i/></div><div className="hero-pot"/></div><div className="hero-watermark"><Icon name="leaf" size={138}/></div></section>
    {loading && <p className="history-state" role="status">Consultando tu saldo, depósitos y transacciones…</p>}
    {error && <p className="history-state error" role="alert">No se pudieron cargar tus datos: {error} <button type="button" onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></p>}
    {!loading && !error && data && <>
      <div className="stats-grid citizen-stats"><StatCard label="Saldo actual" value={`${formatPoints(data.balance.balance)} pts`} detail="Saldo de transacciones registradas" icon="points"/><StatCard label="Depósitos realizados" value={String(data.deposits.length)} detail="Registros de tu cuenta" icon="recycle" tone="mint"/><StatCard label="Peso depositado" value={formatWeight(totalWeight)} detail="Suma del peso de tus depósitos" icon="weight" tone="amber"/></div>
      <section className="panel activity-panel"><SectionHeading eyebrow="TU CONTRIBUCIÓN" title="Actividad reciente"><button className="text-link" onClick={() => onNavigate('Historial')}>Ver historial <Icon name="arrow" size={16}/></button></SectionHeading>
        {latestDeposits.length === 0 ? <p className="history-state">Aún no tienes depósitos registrados.</p> : <div className="activity-list">{latestDeposits.map(deposit => {
          const transaction = transactionByDeposit.get(deposit.id)
          const materialName = materialNames.get(deposit.material_id) ?? 'Material no disponible en catálogo activo'
          const ecopointName = ecopointNames.get(deposit.ecopoint_id) ?? 'EcoPunto no disponible en catálogo activo'
          return <div className="activity-row" key={deposit.id}><div className="activity-symbol symbol-mint"><Icon name="recycle" size={19}/></div><div className="activity-name"><strong>{materialName}</strong><span>{ecopointName} · {new Date(deposit.created_at).toLocaleString('es-CO')}</span></div><div className="activity-weight">{formatWeight(deposit.weight_g)}</div><div className="activity-points">+{formatPoints(transaction?.amount ?? deposit.points_awarded)} pts</div></div>
        })}</div>}
      </section>
    </>}
  </>
}
