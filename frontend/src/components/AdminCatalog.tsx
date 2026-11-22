import { useEffect, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import {
  createCompartment,
  createEcoPoint,
  createMaterial,
  getEcoPointCompartments,
  getEcoPoints,
  getMaterials,
  updateCompartment,
  updateEcoPoint,
  updateMaterial,
} from '../api/catalog'
import { getUniversities } from '../api/universities'
import type { CompartmentSummary, EcoPointSummary, MaterialSummary, UniversitySummary } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { Button } from './UI'
import { Icon } from './Icon'
import './AdminCatalog.css'

type AdminTab = 'ecopoints' | 'materials'
type EcoPointDraft = { university_id: string; code: string; name: string; address: string; active: boolean }
type MaterialDraft = { name: string; description: string; pointsPerGram: string; active: boolean }
type CompartmentDraft = { materialId: string; label: string; capacityKg: string; threshold: string; active: boolean }

const emptyEcoPoint: EcoPointDraft = { university_id: '', code: '', name: '', address: '', active: true }
const emptyMaterial: MaterialDraft = { name: '', description: '', pointsPerGram: '', active: true }
const emptyCompartment: CompartmentDraft = { materialId: '', label: '', capacityKg: '', threshold: '80', active: true }

function apiErrorMessage(error: unknown, logout: () => void): string {
  if (!(error instanceof ApiError)) return error instanceof Error ? error.message : 'Ocurrió un error inesperado.'
  if (error.status === 401) {
    logout()
    return 'La sesión expiró. Inicia sesión nuevamente.'
  }
  if (error.status === 403) return 'El backend rechazó la operación: esta acción requiere rol ADMIN.'
  if (error.status === 404) return 'El registro o EcoPunto ya no existe. Recarga la lista e inténtalo de nuevo.'
  if (error.status === 409) return `Conflicto: ${error.message}`
  if (error.status === 422) return `Revisa los datos: ${error.message}`
  return error.message
}

function decimalText(value: string) {
  const number = Number(value)
  return Number.isFinite(number) ? number.toLocaleString('es-CO', { maximumFractionDigits: 3 }) : value
}

export function AdminCatalog() {
  const { session, logout } = useAuth()
  const token = session?.token
  const [tab, setTab] = useState<AdminTab>('ecopoints')
  const [ecopoints, setEcopoints] = useState<EcoPointSummary[]>([])
  const [materials, setMaterials] = useState<MaterialSummary[]>([])
  const [universities, setUniversities] = useState<UniversitySummary[]>([])
  const [compartments, setCompartments] = useState<CompartmentSummary[]>([])
  const [selectedEcopointId, setSelectedEcopointId] = useState('')
  const [loading, setLoading] = useState(true)
  const [compartmentsLoading, setCompartmentsLoading] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [saving, setSaving] = useState(false)

  const [ecoPointDraft, setEcoPointDraft] = useState<EcoPointDraft>(emptyEcoPoint)
  const [editingEcoPointId, setEditingEcoPointId] = useState('')
  const [ecoPointFormOpen, setEcoPointFormOpen] = useState(false)
  const [materialDraft, setMaterialDraft] = useState<MaterialDraft>(emptyMaterial)
  const [editingMaterialId, setEditingMaterialId] = useState('')
  const [materialFormOpen, setMaterialFormOpen] = useState(false)
  const [compartmentDraft, setCompartmentDraft] = useState<CompartmentDraft>(emptyCompartment)
  const [editingCompartmentId, setEditingCompartmentId] = useState('')
  const [compartmentFormOpen, setCompartmentFormOpen] = useState(false)

  const activeEcopointId = selectedEcopointId || ecopoints[0]?.id || ''
  const selectedEcopoint = ecopoints.find(item => item.id === activeEcopointId)

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    void Promise.all([getEcoPoints(token, controller.signal), getMaterials(token, controller.signal), getUniversities(token, controller.signal)])
      .then(([pointItems, materialItems, universityItems]) => {
        setEcopoints(pointItems)
        setMaterials(materialItems)
        setUniversities(universityItems.filter(item => item.active))
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(apiErrorMessage(reason, logout))
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [token, logout])

  useEffect(() => {
    if (!token || !activeEcopointId) return
    const controller = new AbortController()
    void getEcoPointCompartments(activeEcopointId, token, controller.signal)
      .then(items => setCompartments(items))
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) setError(apiErrorMessage(reason, logout))
      })
      .finally(() => {
        if (!controller.signal.aborted) setCompartmentsLoading(false)
      })
    return () => controller.abort()
  }, [activeEcopointId, token, logout])

  const refreshEcoPoints = async () => {
    if (!token) return
    const items = await getEcoPoints(token)
    setEcopoints(items)
  }

  const refreshMaterials = async () => {
    if (!token) return
    const items = await getMaterials(token)
    setMaterials(items)
  }

  const refreshCompartments = async (ecopointId: string) => {
    if (!token) return
    setCompartmentsLoading(true)
    try {
      setCompartments(await getEcoPointCompartments(ecopointId, token))
    } finally {
      setCompartmentsLoading(false)
    }
  }

  const openNewEcoPoint = () => {
    setEditingEcoPointId('')
    setEcoPointDraft(emptyEcoPoint)
    setEcoPointFormOpen(true)
    setNotice('')
    setError('')
  }

  const openEcoPointEdit = (item: EcoPointSummary) => {
    setEditingEcoPointId(item.id)
    setEcoPointDraft({ university_id: '', code: item.code, name: item.name, address: item.address, active: item.active })
    setEcoPointFormOpen(true)
    setNotice('')
    setError('')
  }

  const submitEcoPoint = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || saving) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      const ecoPointPatch = { code: ecoPointDraft.code, name: ecoPointDraft.name, address: ecoPointDraft.address, active: ecoPointDraft.active }
      const saved = editingEcoPointId
        ? await updateEcoPoint(editingEcoPointId, ecoPointPatch, token)
        : await createEcoPoint(ecoPointDraft, token)
      setSelectedEcopointId(saved.id)
      setEcoPointFormOpen(false)
      setNotice(editingEcoPointId ? 'EcoPunto actualizado.' : 'EcoPunto creado.')
      try { await refreshEcoPoints() } catch (refreshFailure) { setError(`Guardado correctamente, pero no se pudo actualizar la lista: ${apiErrorMessage(refreshFailure, logout)}`) }
    } catch (reason) {
      setError(apiErrorMessage(reason, logout))
    } finally {
      setSaving(false)
    }
  }

  const openNewMaterial = () => {
    setEditingMaterialId('')
    setMaterialDraft(emptyMaterial)
    setMaterialFormOpen(true)
    setNotice('')
    setError('')
  }

  const openMaterialEdit = (item: MaterialSummary) => {
    setEditingMaterialId(item.id)
    setMaterialDraft({ name: item.name, description: item.description ?? '', pointsPerGram: item.points_per_gram, active: item.active })
    setMaterialFormOpen(true)
    setNotice('')
    setError('')
  }

  const submitMaterial = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || saving) return
    setSaving(true)
    setError('')
    setNotice('')
    const payload = {
      name: materialDraft.name.trim(),
      description: materialDraft.description.trim() || null,
      points_per_gram: materialDraft.pointsPerGram,
      active: materialDraft.active,
    }
    try {
      if (editingMaterialId) await updateMaterial(editingMaterialId, payload, token)
      else await createMaterial(payload, token)
      setMaterialFormOpen(false)
      setNotice(editingMaterialId ? 'Material actualizado.' : 'Material creado.')
      try { await refreshMaterials() } catch (refreshFailure) { setError(`Guardado correctamente, pero no se pudo actualizar la lista: ${apiErrorMessage(refreshFailure, logout)}`) }
    } catch (reason) {
      setError(apiErrorMessage(reason, logout))
    } finally {
      setSaving(false)
    }
  }

  const openNewCompartment = () => {
    setEditingCompartmentId('')
    setCompartmentDraft(emptyCompartment)
    setCompartmentFormOpen(true)
    setNotice('')
    setError('')
  }

  const openCompartmentEdit = (item: CompartmentSummary) => {
    setEditingCompartmentId(item.id)
    setCompartmentDraft({ materialId: item.material_id, label: item.label, capacityKg: item.capacity_kg, threshold: String(item.fill_threshold_pct), active: item.active })
    setCompartmentFormOpen(true)
    setNotice('')
    setError('')
  }

  const submitCompartment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!token || !activeEcopointId || saving) return
    setSaving(true)
    setError('')
    setNotice('')
    try {
      if (editingCompartmentId) {
        await updateCompartment(editingCompartmentId, {
          label: compartmentDraft.label.trim(),
          capacity_kg: compartmentDraft.capacityKg,
          fill_threshold_pct: Number(compartmentDraft.threshold),
          active: compartmentDraft.active,
        }, token)
      } else {
        await createCompartment(activeEcopointId, {
          material_id: compartmentDraft.materialId,
          label: compartmentDraft.label.trim(),
          capacity_kg: compartmentDraft.capacityKg,
          current_kg: '0.000',
          fill_threshold_pct: Number(compartmentDraft.threshold),
          active: compartmentDraft.active,
        }, token)
      }
      setCompartmentFormOpen(false)
      setNotice(editingCompartmentId ? 'Compartimento actualizado.' : 'Compartimento creado.')
      try { await refreshCompartments(activeEcopointId) } catch (refreshFailure) { setError(`Guardado correctamente, pero no se pudo actualizar la lista: ${apiErrorMessage(refreshFailure, logout)}`) }
    } catch (reason) {
      setError(apiErrorMessage(reason, logout))
    } finally {
      setSaving(false)
    }
  }

  if (session?.user.role !== 'ADMIN') return <section className="panel admin-catalog-access" role="alert">Esta pantalla requiere una sesión ADMIN.</section>

  const selectedMaterials = materials.filter(item => item.active)
  return <section className="admin-catalog">
    <div className="admin-catalog-toolbar"><div><span className="eyebrow">ADMINISTRACIÓN DE CATÁLOGO</span><h2>Red de reciclaje</h2><p>EcoPuntos, materiales y compartimentos administrados por la API.</p></div><div className="admin-tabs" role="tablist" aria-label="Catálogos"><button type="button" role="tab" aria-selected={tab === 'ecopoints'} className={tab === 'ecopoints' ? 'selected' : ''} onClick={() => setTab('ecopoints')}>EcoPuntos</button><button type="button" role="tab" aria-selected={tab === 'materials'} className={tab === 'materials' ? 'selected' : ''} onClick={() => setTab('materials')}>Materiales</button></div></div>
    {notice && <div className="admin-catalog-notice" role="status"><Icon name="check" size={16}/>{notice}</div>}
    {error && <div className="admin-catalog-error" role="alert"><Icon name="info" size={16}/><span>{error}</span><button type="button" onClick={() => setError('')}>Cerrar</button></div>}
    {loading ? <div className="admin-catalog-state" role="status">Consultando catálogos…</div> : tab === 'ecopoints' ? <>
      <section className="panel admin-catalog-panel">
        <div className="admin-panel-heading"><div><h3>EcoPuntos</h3><p>{ecopoints.length} registros del backend</p></div><Button type="button" onClick={openNewEcoPoint}><Icon name="plus" size={16}/> Nuevo EcoPunto</Button></div>
        {ecoPointFormOpen && <form className="admin-form" onSubmit={submitEcoPoint}>
          <div className="admin-form-heading"><strong>{editingEcoPointId ? 'Editar EcoPunto' : 'Crear EcoPunto'}</strong><button type="button" onClick={() => setEcoPointFormOpen(false)}>Cancelar</button></div>
          <div className="admin-form-grid">
            {!editingEcoPointId && <label>Universidad<select value={ecoPointDraft.university_id} onChange={e => setEcoPointDraft({ ...ecoPointDraft, university_id: e.target.value })} required><option value="">Selecciona una universidad activa</option>{universities.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}
            <label>Código<input value={ecoPointDraft.code} minLength={2} maxLength={40} onChange={e => setEcoPointDraft({ ...ecoPointDraft, code: e.target.value })} required/></label><label>Nombre<input value={ecoPointDraft.name} maxLength={120} onChange={e => setEcoPointDraft({ ...ecoPointDraft, name: e.target.value })} required/></label><label className="wide">Ubicación / dirección<input value={ecoPointDraft.address} maxLength={240} onChange={e => setEcoPointDraft({ ...ecoPointDraft, address: e.target.value })} required/></label><label className="admin-checkbox"><input type="checkbox" checked={ecoPointDraft.active} onChange={e => setEcoPointDraft({ ...ecoPointDraft, active: e.target.checked })}/> Activo</label>
          </div>
          <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : editingEcoPointId ? 'Guardar cambios' : 'Crear EcoPunto'}</Button>
        </form>}
        {ecopoints.length === 0 && !ecoPointFormOpen ? <p className="admin-catalog-state">No hay EcoPuntos registrados.</p> : <div className="admin-table-wrap"><table className="admin-catalog-table"><thead><tr><th>EcoPunto</th><th>Código</th><th>Ubicación</th><th>Estado</th><th/></tr></thead><tbody>{ecopoints.map(item => <tr key={item.id}><td><strong>{item.name}</strong></td><td>{item.code}</td><td>{item.address}</td><td><span className={`admin-state-pill ${item.active ? 'active' : ''}`}>{item.active ? 'Activo' : 'Inactivo'}</span></td><td><button className="admin-row-action" type="button" onClick={() => openEcoPointEdit(item)}>Editar</button></td></tr>)}</tbody></table></div>}
      </section>

      <section className="panel admin-catalog-panel">
        <div className="admin-panel-heading"><div><h3>Compartimentos</h3><p>Peso actual y llenado consultados por EcoPunto</p></div><label className="admin-ecopoint-select"><span>EcoPunto</span><select value={activeEcopointId} onChange={e => { setCompartmentsLoading(true); setCompartments([]); setSelectedEcopointId(e.target.value); setError('') }} disabled={ecopoints.length === 0}><option value="">Selecciona EcoPunto</option>{ecopoints.map(item => <option key={item.id} value={item.id}>{item.name}{item.active ? '' : ' (inactivo)'}</option>)}</select></label><Button type="button" disabled={!activeEcopointId || selectedMaterials.length === 0} onClick={openNewCompartment}><Icon name="plus" size={16}/> Nuevo compartimento</Button></div>
        {compartmentFormOpen && <form className="admin-form" onSubmit={submitCompartment}>
          <div className="admin-form-heading"><strong>{editingCompartmentId ? 'Editar compartimento' : `Crear compartimento · ${selectedEcopoint?.name ?? ''}`}</strong><button type="button" onClick={() => setCompartmentFormOpen(false)}>Cancelar</button></div>
          <div className="admin-form-grid">{!editingCompartmentId && <label>Material<select value={compartmentDraft.materialId} onChange={e => { const material = selectedMaterials.find(item => item.id === e.target.value); setCompartmentDraft({ ...compartmentDraft, materialId: e.target.value, label: compartmentDraft.label || material?.name || '' }) }} required><option value="">Selecciona material activo</option>{selectedMaterials.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>}<label>Etiqueta<input value={compartmentDraft.label} maxLength={120} onChange={e => setCompartmentDraft({ ...compartmentDraft, label: e.target.value })} required/></label><label>Capacidad (kg)<input type="number" min="0.001" max="9999999.999" step="0.001" value={compartmentDraft.capacityKg} onChange={e => setCompartmentDraft({ ...compartmentDraft, capacityKg: e.target.value })} required/></label><label>Umbral de alerta (%)<input type="number" min="1" max="100" step="1" value={compartmentDraft.threshold} onChange={e => setCompartmentDraft({ ...compartmentDraft, threshold: e.target.value })} required/></label>{editingCompartmentId && <label>Peso actual (kg)<input value={decimalText(compartments.find(item => item.id === editingCompartmentId)?.current_kg ?? '0')} readOnly/><small>El endpoint de edición no permite modificar el peso actual.</small></label>}<label className="admin-checkbox"><input type="checkbox" checked={compartmentDraft.active} onChange={e => setCompartmentDraft({ ...compartmentDraft, active: e.target.checked })}/> Activo</label></div>
          <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : editingCompartmentId ? 'Guardar cambios' : 'Crear compartimento'}</Button>
        </form>}
        {compartmentsLoading ? <p className="admin-catalog-state">Consultando compartimentos…</p> : compartments.length === 0 ? <p className="admin-catalog-state">{activeEcopointId ? 'Este EcoPunto no tiene compartimentos registrados.' : 'Selecciona un EcoPunto para consultar sus compartimentos.'}</p> : <div className="admin-table-wrap"><table className="admin-catalog-table"><thead><tr><th>Compartimento</th><th>Material</th><th>Peso / capacidad</th><th>Llenado</th><th>Estado</th><th/></tr></thead><tbody>{compartments.map(item => { const fill = Math.max(0, Math.min(100, Number(item.fill_percentage))); return <tr key={item.id}><td><strong>{item.label}</strong></td><td>{materials.find(material => material.id === item.material_id)?.name ?? '—'}</td><td>{decimalText(item.current_kg)} / {decimalText(item.capacity_kg)} kg</td><td><div className="admin-fill-cell"><div className="admin-fill-track"><span style={{ width: `${fill}%` }}/></div><span>{decimalText(item.fill_percentage)}%</span></div></td><td><span className={`admin-state-pill ${item.active ? 'active' : ''}`}>{item.active ? 'Activo' : 'Inactivo'}</span></td><td><button className="admin-row-action" type="button" onClick={() => openCompartmentEdit(item)}>Editar</button></td></tr> })}</tbody></table></div>}
      </section>
    </> : <section className="panel admin-catalog-panel">
      <div className="admin-panel-heading"><div><h3>Materiales</h3><p>El factor se expresa en EcoPuntos por gramo</p></div><Button type="button" onClick={openNewMaterial}><Icon name="plus" size={16}/> Nuevo material</Button></div>
      {materialFormOpen && <form className="admin-form" onSubmit={submitMaterial}>
        <div className="admin-form-heading"><strong>{editingMaterialId ? 'Editar material' : 'Crear material'}</strong><button type="button" onClick={() => setMaterialFormOpen(false)}>Cancelar</button></div>
        <div className="admin-form-grid"><label>Nombre<input value={materialDraft.name} maxLength={120} onChange={e => setMaterialDraft({ ...materialDraft, name: e.target.value })} required/></label><label>EcoPuntos por gramo<input type="number" min="0.0001" max="999999.9999" step="0.0001" value={materialDraft.pointsPerGram} onChange={e => setMaterialDraft({ ...materialDraft, pointsPerGram: e.target.value })} required/><small>Factor positivo, hasta 4 decimales.</small></label><label className="wide">Descripción<input value={materialDraft.description} maxLength={300} onChange={e => setMaterialDraft({ ...materialDraft, description: e.target.value })}/></label><label className="admin-checkbox"><input type="checkbox" checked={materialDraft.active} onChange={e => setMaterialDraft({ ...materialDraft, active: e.target.checked })}/> Activo</label></div>
        <Button type="submit" disabled={saving}>{saving ? 'Guardando…' : editingMaterialId ? 'Guardar cambios' : 'Crear material'}</Button>
      </form>}
      {materials.length === 0 && !materialFormOpen ? <p className="admin-catalog-state">No hay materiales registrados.</p> : <div className="admin-table-wrap"><table className="admin-catalog-table"><thead><tr><th>Material</th><th>Descripción</th><th>EcoPuntos / g</th><th>Estado</th><th/></tr></thead><tbody>{materials.map(item => <tr key={item.id}><td><strong>{item.name}</strong></td><td>{item.description || '—'}</td><td>{item.points_per_gram}</td><td><span className={`admin-state-pill ${item.active ? 'active' : ''}`}>{item.active ? 'Activo' : 'Inactivo'}</span></td><td><button className="admin-row-action" type="button" onClick={() => openMaterialEdit(item)}>Editar</button></td></tr>)}</tbody></table></div>}
    </section>}
  </section>
}
