import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getPointsBalance, getPointTransactions } from '../api/points'
import type { BalanceSummary, PointTransactionSummary } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Icon } from './Icon'
import { StatCard } from './UI'
import './DepositHistory.css'

function formatPoints(value: string) {
  return Number(value).toLocaleString('es-CO', { maximumFractionDigits: 4 })
}

export function CitizenPoints() {
  const { session, logout } = useAuth()
  const [balance, setBalance] = useState<BalanceSummary | null>(null)
  const [transactions, setTransactions] = useState<PointTransactionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!session?.token) return
    const controller = new AbortController()
    void Promise.all([
      getPointsBalance(session.token, controller.signal),
      getPointTransactions(session.token, controller.signal),
    ]).then(([balanceResult, transactionItems]) => {
      setBalance(balanceResult)
      setTransactions(transactionItems)
    }).catch((reason: unknown) => {
      if (controller.signal.aborted) return
      if (reason instanceof ApiError && reason.isUnauthorized) {
        logout()
        return
      }
      setBalance(null)
      setTransactions([])
      setError(reason instanceof Error ? reason.message : 'No fue posible cargar tus EcoPuntos.')
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [session?.token, logout, attempt])

  return <section className="panel deposit-history">
    <div className="deposit-history-heading"><div><span className="eyebrow">SALDO Y MOVIMIENTOS</span><h2>Mis EcoPuntos</h2></div></div>
    {loading && <p className="history-state" role="status">Consultando saldo y transacciones…</p>}
    {error && <p className="history-state error" role="alert">No se pudieron cargar tus EcoPuntos: {error} <button type="button" onClick={() => { setError(''); setLoading(true); setAttempt(value => value + 1) }}>Reintentar</button></p>}
    {!loading && !error && balance && <>
      <div className="stats-grid"><StatCard label="Saldo actual" value={`${formatPoints(balance.balance)} pts`} detail="Calculado desde tus transacciones" icon="points"/></div>
      <h3 className="points-transactions-heading">Transacciones</h3>
      {transactions.length === 0 ? <p className="history-state">Aún no tienes transacciones registradas.</p> : <div className="deposit-history-list">{transactions.map(transaction => {
        const amount = Number(transaction.amount)
        const sign = amount > 0 ? '+' : ''
        return <article className="deposit-history-row" key={transaction.id}>
          <div className="history-deposit-icon"><Icon name={transaction.type === 'EARN' ? 'points' : 'gift'} size={18}/></div>
          <div className="history-deposit-main"><strong>{transaction.description}</strong><span>{new Date(transaction.created_at).toLocaleString('es-CO')}</span></div>
          <span className="history-points">{sign}{formatPoints(transaction.amount)} pts</span>
        </article>
      })}</div>}
    </>}
  </section>
}
