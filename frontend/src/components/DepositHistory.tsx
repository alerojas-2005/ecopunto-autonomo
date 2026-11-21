import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getEcoPoints, getMaterials } from '../api/catalog'
import { getMyDeposits } from '../api/deposits'
import { getPointTransactions } from '../api/points'
import type { DepositSummary, EcoPointSummary, MaterialSummary, PointTransactionSummary } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'

import './DepositHistory.css'

function formatPoints(value: string) {
  return Number(value).toLocaleString('es-CO', { maximumFractionDigits: 4 })
}

export function DepositHistory() {
  const { session, logout } = useAuth()
  const [deposits, setDeposits] = useState<DepositSummary[]>([])
  const [transactions, setTransactions] = useState<PointTransactionSummary[]>([])
  const [materials, setMaterials] = useState<MaterialSummary[]>([])
  const [ecopoints, setEcopoints] = useState<EcoPointSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!session?.token) return
    const controller = new AbortController()
    void Promise.all([
      getMyDeposits(session.token, controller.signal),
      getPointTransactions(session.token, controller.signal),
      getMaterials(session.token, controller.signal),
      getEcoPoints(session.token, controller.signal),
    ]).then(([depositItems, transactionItems, materialItems, ecopointItems]) => {
      setError('')
      setDeposits(depositItems)
      setTransactions(transactionItems)
      setMaterials(materialItems)
      setEcopoints(ecopointItems)
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return
      if (reason instanceof ApiError && reason.isUnauthorized) {
        logout()
        return
      }
      setError(reason instanceof Error ? reason.message : 'No fue posible cargar tu historial.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [session?.token, logout, attempt])

  const materialNames = new Map(materials.map(item => [item.id, item.name]))
  const ecopointNames = new Map(ecopoints.map(item => [item.id, item.name]))

  return <section className="panel deposit-history">
    <div className="deposit-history-heading"><div><span className="eyebrow">REGISTRO DE APORTES</span><h2>Tu historial de depósitos</h2></div>{!loading && !error && <span>{deposits.length} registros</span>}</div>
    {loading && <p className="history-state" role="status">Consultando historial y transacciones…</p>}
    {error && <p className="history-state error" role="alert">No se pudo cargar el historial: {error} <button type="button" onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></p>}
    {!loading && !error && deposits.length === 0 && <p className="history-state">Aún no tienes depósitos registrados.</p>}
    {!loading && !error && deposits.length > 0 && <div className="deposit-history-list">{deposits.map(deposit => {
      const transaction = transactions.find(item => item.deposit_id === deposit.id)
      return <article className="deposit-history-row" key={deposit.id}>
        <div className="history-deposit-icon"><Icon name="recycle" size={18}/></div>
        <div className="history-deposit-main"><strong>{materialNames.get(deposit.material_id) ?? 'Material no disponible en catálogo activo'}</strong><span>{ecopointNames.get(deposit.ecopoint_id) ?? 'EcoPunto no disponible en catálogo activo'} · {new Date(deposit.created_at).toLocaleString('es-CO')}</span></div>
        <span className="history-weight">{deposit.weight_g.toLocaleString('es-CO')} g</span>
        <span className="history-points">+{formatPoints(transaction?.amount ?? deposit.points_awarded)} pts</span>
      </article>
    })}</div>}
    {!loading && !error && <p className="history-source">Historial y transacciones consultados desde la API.</p>}
  </section>
}
