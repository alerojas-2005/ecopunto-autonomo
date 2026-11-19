import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { getEcoPointCompartments, getEcoPoints, getMaterials } from '../api/catalog'
import { createDeposit, getMyDeposits } from '../api/deposits'
import { getPointsBalance, getPointTransactions } from '../api/points'
import type { BalanceSummary, CompartmentSummary, DepositSummary, EcoPointSummary, MaterialSummary } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Button, SectionHeading } from './UI'
import { Icon } from './Icon'
import './DepositForm.css'
import './DepositFormStatus.css'

function errorText(error: unknown) {
  return error instanceof Error ? error.message : 'No se pudo consultar la información. Intenta nuevamente.'
}

function decimalText(value: string) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toLocaleString('es-CO', { maximumFractionDigits: 2 }) : value
}

export function DepositForm() {
  const { session, logout } = useAuth()
  const token = session?.token
  const [ecopoints, setEcopoints] = useState<EcoPointSummary[]>([])
  const [materials, setMaterials] = useState<MaterialSummary[]>([])
  const [ecopointError, setEcopointError] = useState('')
  const [materialError, setMaterialError] = useState('')
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogAttempt, setCatalogAttempt] = useState(0)
  const [selectedEcopointId, setSelectedEcopointId] = useState('')
  const [selectedMaterialId, setSelectedMaterialId] = useState('')
  const [compartments, setCompartments] = useState<CompartmentSummary[]>([])
  const [compartmentsLoading, setCompartmentsLoading] = useState(false)
  const [compartmentsLoaded, setCompartmentsLoaded] = useState(false)
  const [compartmentsError, setCompartmentsError] = useState('')
  const [selectedCompartmentId, setSelectedCompartmentId] = useState('')
  const [weightGrams, setWeightGrams] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const submitLock = useRef(false)
  const [success, setSuccess] = useState<{ deposit: DepositSummary; balance: BalanceSummary | null; depositCount: number | null; transactionCount: number | null; refreshed: boolean } | null>(null)
  const [submitError, setSubmitError] = useState('')
  const [refreshError, setRefreshError] = useState('')
  const compartmentRequest = useRef<AbortController | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    const loadCatalogs = async () => {
      if (!token) return
      const [ecopointsResult, materialsResult] = await Promise.allSettled([
        getEcoPoints(token, controller.signal),
        getMaterials(token, controller.signal),
      ])
      if (controller.signal.aborted) return

      const rejected = [ecopointsResult, materialsResult].find(
        result => result.status === 'rejected' && result.reason instanceof ApiError && result.reason.isUnauthorized,
      )
      if (rejected?.status === 'rejected') {
        logout()
        return
      }

      if (ecopointsResult.status === 'fulfilled') {
        setEcopoints(ecopointsResult.value.filter(item => item.active))
        setEcopointError('')
      } else {
        setEcopointError(errorText(ecopointsResult.reason))
      }
      if (materialsResult.status === 'fulfilled') {
        setMaterials(materialsResult.value.filter(item => item.active))
        setMaterialError('')
      } else {
        setMaterialError(errorText(materialsResult.reason))
      }
      setCatalogLoading(false)
    }

    void loadCatalogs()
    return () => controller.abort()
  }, [token, logout, catalogAttempt])

  useEffect(() => () => compartmentRequest.current?.abort(), [])

  const selectEcopoint = (ecopointId: string, resetMaterial = true) => {
    compartmentRequest.current?.abort()
    setSelectedEcopointId(ecopointId)
    if (resetMaterial) setSelectedMaterialId('')
    setSelectedCompartmentId('')
    setCompartments([])
    setCompartmentsError('')
    setCompartmentsLoaded(false)

    if (!ecopointId || !token) {
      setCompartmentsLoading(false)
      return
    }

    const controller = new AbortController()
    compartmentRequest.current = controller
    setCompartmentsLoading(true)
    void getEcoPointCompartments(ecopointId, token, controller.signal)
      .then(items => {
        setCompartments(items.filter(item => item.active))
        setCompartmentsLoaded(true)
      })
      .catch(error => {
        if (controller.signal.aborted) return
        if (error instanceof ApiError && error.isUnauthorized) {
          logout()
          return
        }
        setCompartmentsError(errorText(error))
      })
      .finally(() => {
        if (!controller.signal.aborted) setCompartmentsLoading(false)
      })
  }

  const compatibleCompartments = compartments.filter(item => item.material_id === selectedMaterialId)
  const selectedCompartment = compatibleCompartments.length === 1
    ? compatibleCompartments[0]
    : compatibleCompartments.find(item => item.id === selectedCompartmentId)
  const selectedMaterial = materials.find(item => item.id === selectedMaterialId)
  const weightNumber = Number(weightGrams)
  const weightIsValid = /^\d+$/.test(weightGrams) && Number.isSafeInteger(weightNumber) && weightNumber > 0 && weightNumber <= 100_000
  const selectionReady = Boolean(selectedEcopointId && selectedMaterialId && selectedCompartment && weightIsValid)

  const submitDeposit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || !selectionReady || !selectedCompartment || submitLock.current) return
    submitLock.current = true
    setSubmitting(true)
    setSubmitError('')
    setRefreshError('')
    setSuccess(null)
    try {
      const deposit = await createDeposit({
        ecopoint_id: selectedEcopointId,
        material_id: selectedMaterialId,
        compartment_id: selectedCompartment.id,
        weight_g: weightNumber,
      }, token)
      const [compartmentResult, balanceResult, depositsResult, transactionsResult] = await Promise.allSettled([
        getEcoPointCompartments(selectedEcopointId, token),
        getPointsBalance(token),
        getMyDeposits(token),
        getPointTransactions(token),
      ])
      const unauthorized = [compartmentResult, balanceResult, depositsResult, transactionsResult].some(
        result => result.status === 'rejected' && result.reason instanceof ApiError && result.reason.isUnauthorized,
      )
      if (unauthorized) {
        logout()
        return
      }
      if (compartmentResult.status === 'fulfilled') {
        const freshCompartments = compartmentResult.value.filter(item => item.active)
        setCompartments(freshCompartments)
        if (!freshCompartments.some(item => item.id === selectedCompartment.id)) setSelectedCompartmentId('')
      }
      const balance = balanceResult.status === 'fulfilled' ? balanceResult.value : null
      const refreshed = compartmentResult.status === 'fulfilled' && balanceResult.status === 'fulfilled'
        && depositsResult.status === 'fulfilled' && transactionsResult.status === 'fulfilled'
      setSuccess({
        deposit,
        balance,
        depositCount: depositsResult.status === 'fulfilled' ? depositsResult.value.length : null,
        transactionCount: transactionsResult.status === 'fulfilled' ? transactionsResult.value.length : null,
        refreshed,
      })
      if (!refreshed) setRefreshError('El depósito quedó registrado, pero no fue posible actualizar todas las consultas. Puedes volver a cargar la pantalla.')
    } catch (error) {
      if (error instanceof ApiError && error.isUnauthorized) {
        logout()
        return
      }
      if (error instanceof ApiError) {
        if (error.status === 403) setSubmitError('Tu perfil no tiene permiso para registrar depósitos. Inicia sesión con una cuenta ciudadana.')
        else if (error.status === 404) setSubmitError('El EcoPunto, material o compartimento ya no está disponible. Actualiza los catálogos e inténtalo de nuevo.')
        else if (error.status === 422) setSubmitError(`El backend rechazó los datos del depósito: ${error.message}`)
        else if (error.status === 400 || error.status === 409) setSubmitError(error.message)
        else setSubmitError(`No se pudo registrar el depósito: ${error.message}`)
      } else setSubmitError(errorText(error))
    } finally {
      submitLock.current = false
      setSubmitting(false)
    }
  }

  const retryCatalogs = () => {
    setCatalogLoading(true)
    setCatalogAttempt(attempt => attempt + 1)
  }

  const selectedEcopoint = ecopoints.find(item => item.id === selectedEcopointId)
  return <section className="panel form-panel deposit-form">
    <div className="deposit-intro"><SectionHeading eyebrow="APORTE VIRTUAL" title="Prepara tu depósito"/><p>Selecciona un EcoPunto, el material y el peso que vas a depositar. Los datos de selección se consultan desde EcoPunto.</p></div>

    {(ecopointError || materialError) && <div className="deposit-alert" role="alert"><Icon name="info" size={18}/><div><strong>No se pudieron cargar todos los catálogos</strong>{ecopointError && <span>EcoPuntos: {ecopointError}</span>}{materialError && <span>Materiales: {materialError}</span>}<button type="button" onClick={retryCatalogs}>Reintentar consultas</button></div></div>}
    {catalogLoading && <div className="deposit-loading" role="status"><span className="deposit-spinner"/> Consultando EcoPuntos y materiales…</div>}
    {!catalogLoading && !ecopointError && !materialError && ecopoints.length > 0 && materials.length > 0 && <div className="deposit-catalog-ready" role="status"><Icon name="check" size={16}/> Catálogos cargados. Elige un EcoPunto y un material para consultar sus compartimentos.</div>}

    {success && <div className="deposit-success" role="status"><Icon name="check" size={20}/><div><strong>Depósito registrado correctamente</strong><span>{selectedMaterial?.name ?? 'Material'} · {success.deposit.weight_g.toLocaleString('es-CO')} g en {selectedEcopoint?.name ?? 'el EcoPunto seleccionado'}.</span><span>El backend otorgó {decimalText(success.deposit.points_awarded)} EcoPuntos.</span>{success.balance && <span>Saldo actualizado: {decimalText(success.balance.balance)} EcoPuntos.</span>}{success.depositCount !== null && <span>Historial: {success.depositCount} depósitos · Transacciones: {success.transactionCount ?? 'sin actualizar'}.</span>}<small>{success.refreshed ? 'Compartimento, saldo, historial y transacciones consultados nuevamente.' : 'El depósito está confirmado; algunas consultas de actualización no respondieron.'}</small></div></div>}
    {submitError && <div className="deposit-submit-error" role="alert"><Icon name="info" size={17}/><span>{submitError}</span></div>}
    {refreshError && <div className="deposit-refresh-note" role="status">{refreshError}</div>}
    <form onSubmit={submitDeposit}>
    <div className="deposit-fields">
      <label className="deposit-field"><span>EcoPunto</span><select value={selectedEcopointId} onChange={event => selectEcopoint(event.target.value)} disabled={catalogLoading || Boolean(ecopointError) || ecopoints.length === 0}><option value="">Selecciona un EcoPunto</option>{ecopoints.map(item => <option key={item.id} value={item.id}>{item.name} · {item.address}</option>)}</select>{!catalogLoading && !ecopointError && ecopoints.length === 0 && <small>No hay EcoPuntos activos disponibles.</small>}</label>
      <label className="deposit-field"><span>Material</span><select value={selectedMaterialId} onChange={event => { setSelectedMaterialId(event.target.value); setSelectedCompartmentId('') }} disabled={catalogLoading || Boolean(materialError) || materials.length === 0}><option value="">Selecciona un material</option>{materials.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select>{!catalogLoading && !materialError && materials.length === 0 && <small>No hay materiales activos disponibles.</small>}</label>
    </div>

    {selectedEcopointId && <div className="deposit-compartment-area">
      {compartmentsLoading && <div className="deposit-loading compact" role="status"><span className="deposit-spinner"/> Consultando compartimentos de este EcoPunto…</div>}
      {compartmentsError && <div className="deposit-inline-error" role="alert"><span>No se pudieron consultar los compartimentos: {compartmentsError}</span><button type="button" onClick={() => selectEcopoint(selectedEcopointId, false)}>Reintentar</button></div>}
      {!compartmentsLoading && !compartmentsError && selectedMaterialId && compartmentsLoaded && compatibleCompartments.length === 0 && <div className="deposit-empty-match"><Icon name="info" size={18}/><span>Este EcoPunto no tiene un compartimento activo para {selectedMaterial?.name ?? 'el material seleccionado'}.</span></div>}
      {!compartmentsLoading && !compartmentsError && compatibleCompartments.length > 1 && <label className="deposit-field"><span>Compartimento</span><select value={selectedCompartmentId} onChange={event => setSelectedCompartmentId(event.target.value)}><option value="">Selecciona un compartimento</option>{compatibleCompartments.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>}
      {selectedCompartment && <section className="compartment-card" aria-label="Estado del compartimento"><div className="compartment-card-heading"><div className="compartment-mark"><Icon name="bins" size={20}/></div><div><span className="eyebrow">COMPARTIMENTO SELECCIONADO</span><strong>{selectedCompartment.label}</strong></div><span className="compartment-fill">{decimalText(selectedCompartment.fill_percentage)}% lleno</span></div><div className="compartment-details"><div><span>Material</span><strong>{selectedMaterial?.name ?? '—'}</strong></div><div><span>Peso actual</span><strong>{decimalText(selectedCompartment.current_kg)} kg</strong></div><div><span>Capacidad máxima</span><strong>{decimalText(selectedCompartment.capacity_kg)} kg</strong></div></div><div className="compartment-progress" role="img" aria-label={`Llenado: ${decimalText(selectedCompartment.fill_percentage)} por ciento`}><span style={{ width: `${Math.max(0, Math.min(100, Number(selectedCompartment.fill_percentage)))}%` }}/></div></section>}
    </div>}

    <label className="deposit-field weight-field"><span>Peso del material</span><div className="weight-input-wrap"><input type="number" min="1" max="100000" step="1" inputMode="numeric" value={weightGrams} onChange={event => setWeightGrams(event.target.value)} placeholder="Ej. 250"/><span>gramos</span></div><small>Ingresa un peso entero mayor que cero, hasta 100.000 gramos.</small></label>

    {selectionReady && <div className="deposit-ready"><Icon name="check" size={17}/><span>Listo para registrar el depósito virtual. Los puntos serán calculados por el backend.</span></div>}
    <div className="deposit-next-step"><span>El registro actualizará el compartimento y el saldo en el servidor.</span><Button type="submit" disabled={!selectionReady || submitting}>{submitting ? <>Registrando…</> : <>Registrar depósito <Icon name="arrow" size={16}/></>}</Button></div>
    </form>
  </section>
}
