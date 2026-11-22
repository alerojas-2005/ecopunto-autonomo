import { useEffect, useState, type FormEvent } from 'react'
import { getEcoPoints } from '../api/catalog'
import { getUniversities } from '../api/universities'
import {
  addAssignment, addOrganization, addRecycler, addSector, deleteOrganization,
  getAssignments, getOrganizations, getRecyclers, getSectors, setOrganizationCoverage,
  setSectorPoints, updateAssignment, updateOrganization, updateRecycler, updateSector,
  type Assignment, type Organization, type OrganizationDraft, type Recycler,
  type RecyclerDraft, type Sector,
} from '../api/recyclers'
import { useAuth } from '../auth/useAuth'
import { Button } from './UI'
import './AdminRecyclers.css'

type Tab = 'Organizaciones' | 'Recicladores' | 'Asignaciones'
type University = { id: string; name: string }
type Point = { id: string; name: string; university_id: string; active: boolean }
const blankOrganization: OrganizationDraft = { name: '', type: 'ASSOCIATION', tax_id: null, phone: null, email: null, address: null, city: 'Bogotá', description: null, status: 'PENDING' }
const blankRecycler: RecyclerDraft = { full_name: '', email: '', password: '', link_type: 'INDEPENDENT', organization_id: null, phone: null, document_type: null, document_number: null, is_active: true }

export function AdminRecyclers() {
  const { session, logout } = useAuth()
  const token = session?.token
  const [tab, setTab] = useState<Tab>('Organizaciones')
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [recyclers, setRecyclers] = useState<Recycler[]>([])
  const [sectors, setSectors] = useState<Sector[]>([])
  const [assignments, setAssignments] = useState<Assignment[]>([])
  const [universities, setUniversities] = useState<University[]>([])
  const [points, setPoints] = useState<Point[]>([])
  const [editingOrg, setEditingOrg] = useState('')
  const [editingRecycler, setEditingRecycler] = useState('')
  const [orgDraft, setOrgDraft] = useState<OrganizationDraft>(blankOrganization)
  const [recyclerDraft, setRecyclerDraft] = useState<RecyclerDraft>(blankRecycler)
  const [orgSectorIds, setOrgSectorIds] = useState<string[]>([])
  const [orgPointIds, setOrgPointIds] = useState<string[]>([])
  const [selectedOrg, setSelectedOrg] = useState('')
  const [orgSearch, setOrgSearch] = useState('')
  const [orgStatusFilter, setOrgStatusFilter] = useState('')
  const [orgTypeFilter, setOrgTypeFilter] = useState('')
  const [recyclerSearch, setRecyclerSearch] = useState('')
  const [recyclerOrgFilter, setRecyclerOrgFilter] = useState('')
  const [recyclerActiveFilter, setRecyclerActiveFilter] = useState('')
  const [assignmentFilters, setAssignmentFilters] = useState({ organization_id: '', recycler_id: '', sector_id: '', university_id: '', ecopoint_id: '', state: '' })
  const [sectorName, setSectorName] = useState('')
  const [sectorLocality, setSectorLocality] = useState('')
  const [sectorCity, setSectorCity] = useState('Bogotá')
  const [manualRecyclerId,setManualRecyclerId]=useState('')
  const [manualSectorId,setManualSectorId]=useState('')
  const [manualUniversityId,setManualUniversityId]=useState('')
  const [manualEcopointId,setManualEcopointId]=useState('')
  const [manualStartsAt,setManualStartsAt]=useState('')
  const [manualEndsAt,setManualEndsAt]=useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    void Promise.all([
      getOrganizations(token, controller.signal), getRecyclers(token, controller.signal),
      getSectors(token, controller.signal), getAssignments(token, controller.signal),
      getUniversities(token, controller.signal), getEcoPoints(token, controller.signal),
    ]).then(([orgs, people, areas, grants, universitiesList, pointList]) => {
      if (controller.signal.aborted) return
      setOrganizations(orgs); setRecyclers(people); setSectors(areas); setAssignments(grants)
      setUniversities(universitiesList); setPoints(pointList); setError('')
    }).catch(reason => {
      if (controller.signal.aborted) return
      const message = reason instanceof Error ? reason.message : 'No se pudo cargar el módulo.'
      setError(message)
      if (reason instanceof Error && 'isUnauthorized' in reason && reason.isUnauthorized) logout()
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [token, refresh, logout])

  const refreshData = () => setRefresh(value => value + 1)
  const saveOrganization = async (event: FormEvent) => {
    event.preventDefault(); if (!token) return
    setSaving(true); setError(''); setNotice('')
    try {
      const item = editingOrg
        ? await updateOrganization(editingOrg, orgDraft, token)
        : await addOrganization(orgDraft, token)
      await setOrganizationCoverage(item.id, orgSectorIds, orgPointIds, token)
      setEditingOrg(''); setOrgDraft(blankOrganization); setOrgSectorIds([]); setOrgPointIds([])
      setNotice('Organización y cobertura guardadas.'); refreshData()
    } catch (reason) { setError(message(reason)) } finally { setSaving(false) }
  }
  const editOrganization = (item: Organization) => {
    setEditingOrg(item.id); setSelectedOrg(item.id)
    setOrgDraft({ name:item.name,type:item.type,tax_id:item.tax_id,phone:item.phone,email:item.email,address:item.address,city:item.city,description:item.description,status:item.status })
    setOrgSectorIds(item.sector_ids); setOrgPointIds(item.ecopoint_ids); setNotice('')
  }
  const saveRecycler = async (event: FormEvent) => {
    event.preventDefault(); if (!token) return
    setSaving(true); setError(''); setNotice('')
    try {
      if (editingRecycler) {
        const profile = { ...recyclerDraft }
        delete profile.password
        await updateRecycler(editingRecycler, profile, token)
        setNotice('Perfil actualizado; la cobertura se sincronizó con la organización.')
      } else {
        const password = recyclerDraft.password ?? ''
        await addRecycler({ ...recyclerDraft, password }, token)
        setNotice(recyclerDraft.link_type === 'ORGANIZATION' ? 'Cuenta creada y autorizaciones generadas desde la cobertura vigente.' : 'Cuenta independiente creada. Asigna manualmente sus ámbitos autorizados.')
      }
      setRecyclerDraft(blankRecycler); setEditingRecycler(''); refreshData()
    } catch (reason) { setError(message(reason)) } finally { setSaving(false) }
  }
  const editRecycler = (item: Recycler) => {
    setEditingRecycler(item.id)
    setRecyclerDraft({ full_name:item.full_name,email:item.email,link_type:item.link_type,organization_id:item.organization_id,phone:item.phone,document_type:item.document_type,document_number:item.document_number,is_active:item.is_active })
    setTab('Recicladores'); setNotice('')
  }
  const saveSector = async (event: FormEvent) => {
    event.preventDefault(); if (!token) return
    setSaving(true); setError(''); setNotice('')
    try { const sector = await addSector({ name:sectorName,locality:sectorLocality,city:sectorCity }, token); setSectorName('');setSectorLocality('');setNotice(`Sector “${sector.name}” creado. Vincula EcoPuntos desde la cobertura.`);refreshData() }
    catch(reason) { setError(message(reason)) } finally { setSaving(false) }
  }
  const saveSectorPoints = async (sector: Sector, selected: string[]) => {
    if (!token) return
    setSaving(true);setError('');setNotice('')
    try { await setSectorPoints(sector.id, selected, token);setNotice(`EcoPuntos del sector “${sector.name}” actualizados; las autorizaciones se sincronizaron.`);refreshData() }
    catch(reason) { setError(message(reason)) } finally { setSaving(false) }
  }
  const saveDirectAssignment = async (event:FormEvent) => {
    event.preventDefault();if(!token)return
    setSaving(true);setError('');setNotice('')
    try {
      await addAssignment({recycler_id:manualRecyclerId,sector_id:manualSectorId||null,university_id:manualUniversityId||null,ecopoint_id:manualEcopointId||null,starts_at:manualStartsAt?new Date(`${manualStartsAt}T00:00:00Z`).toISOString():undefined,ends_at:manualEndsAt?new Date(`${manualEndsAt}T23:59:59Z`).toISOString():null,status:'ACTIVE'},token)
      setNotice('Autorización directa creada.');setManualSectorId('');setManualUniversityId('');setManualEcopointId('');setManualStartsAt('');setManualEndsAt('');refreshData()
    } catch(reason){setError(message(reason))} finally{setSaving(false)}
  }
  const run = async (action: () => Promise<unknown>, success: string) => {
    setSaving(true);setError('');setNotice('')
    try { await action();setNotice(success);refreshData() } catch(reason) {setError(message(reason))} finally {setSaving(false)}
  }
  const orgName = (id:string|null) => organizations.find(item=>item.id===id)?.name ?? 'Independiente'
  const filteredOrgs = organizations.filter(item => (!orgSearch || `${item.name} ${item.city} ${item.tax_id ?? ''}`.toLocaleLowerCase().includes(orgSearch.toLocaleLowerCase())) && (!orgStatusFilter || item.status===orgStatusFilter) && (!orgTypeFilter || item.type===orgTypeFilter))
  const filteredRecyclers = recyclers.filter(item => (!recyclerSearch || `${item.full_name} ${item.email}`.toLocaleLowerCase().includes(recyclerSearch.toLocaleLowerCase())) && (!recyclerOrgFilter || item.organization_id===recyclerOrgFilter) && (!recyclerActiveFilter || String(item.is_active)===recyclerActiveFilter))

  return <section className="recycler-admin">
    <div className="recycler-tabs">{(['Organizaciones','Recicladores','Asignaciones'] as Tab[]).map(item=><button key={item} className={tab===item?'selected':''} onClick={()=>setTab(item)}>{item}</button>)}</div>
    {error&&<p role="alert" className="recycler-error">{error}</p>}{notice&&<p role="status" className="recycler-notice">{notice}</p>}{loading&&<p className="operations-state">Cargando datos reales del módulo…</p>}

    {tab==='Organizaciones'&&<div className="recycler-layout">
      <form className="panel recycler-form" onSubmit={saveOrganization}>
        <h2>{editingOrg?'Editar organización':'Nueva organización'}</h2>
        <label>Nombre<input value={orgDraft.name} onChange={e=>setOrgDraft({...orgDraft,name:e.target.value})} required maxLength={120}/></label>
        <label>Tipo<select value={orgDraft.type} onChange={e=>setOrgDraft({...orgDraft,type:e.target.value})}>{['ASSOCIATION','COOPERATIVE','COMPANY','INDEPENDENT','OTHER'].map(x=><option key={x}>{x}</option>)}</select></label>
        <label>NIT opcional<input value={orgDraft.tax_id??''} onChange={e=>setOrgDraft({...orgDraft,tax_id:e.target.value||null})} maxLength={40}/></label>
        <label>Teléfono<input value={orgDraft.phone??''} onChange={e=>setOrgDraft({...orgDraft,phone:e.target.value||null})} maxLength={40}/></label>
        <label>Correo<input type="email" value={orgDraft.email??''} onChange={e=>setOrgDraft({...orgDraft,email:e.target.value||null})}/></label>
        <label>Dirección<input value={orgDraft.address??''} onChange={e=>setOrgDraft({...orgDraft,address:e.target.value||null})}/></label>
        <label>Ciudad<input value={orgDraft.city} onChange={e=>setOrgDraft({...orgDraft,city:e.target.value})} required/></label>
        <label>Descripción<textarea value={orgDraft.description??''} onChange={e=>setOrgDraft({...orgDraft,description:e.target.value||null})}/></label>
        <label>Estado<select value={orgDraft.status} onChange={e=>setOrgDraft({...orgDraft,status:e.target.value})}>{['PENDING','ACTIVE','INACTIVE'].map(x=><option key={x}>{x}</option>)}</select></label>
        <label>Sectores atendidos<select multiple value={orgSectorIds} onChange={e=>setOrgSectorIds(Array.from(e.target.selectedOptions,option=>option.value))}>{sectors.map(s=><option key={s.id} value={s.id}>{s.name} · {s.locality} ({s.city})</option>)}</select><small>Ctrl/Cmd permite elegir varios. Configura primero los EcoPuntos en cada sector.</small></label>
        <label>EcoPuntos cubiertos<select multiple value={orgPointIds} onChange={e=>setOrgPointIds(Array.from(e.target.selectedOptions,option=>option.value))}>{points.filter(p=>p.active).map(p=><option key={p.id} value={p.id}>{p.name} · {universities.find(u=>u.id===p.university_id)?.name??'Universidad'}</option>)}</select><small>Solo se aceptan EcoPuntos vinculados explícitamente a sectores seleccionados.</small></label>
        <div className="recycler-form-actions"><Button disabled={saving}>{saving?'Guardando…':editingOrg?'Guardar cambios':'Crear organización'}</Button>{editingOrg&&<Button type="button" variant="secondary" onClick={()=>{setEditingOrg('');setOrgDraft(blankOrganization);setOrgSectorIds([]);setOrgPointIds([])}}>Cancelar</Button>}</div>
      </form>
      <div className="panel"><h2>Organizaciones recicladoras</h2><div className="recycler-filters"><input placeholder="Buscar nombre, ciudad o NIT" value={orgSearch} onChange={e=>setOrgSearch(e.target.value)}/><select value={orgTypeFilter} onChange={e=>setOrgTypeFilter(e.target.value)}><option value="">Todos los tipos</option>{['ASSOCIATION','COOPERATIVE','COMPANY','INDEPENDENT','OTHER'].map(x=><option key={x}>{x}</option>)}</select><select value={orgStatusFilter} onChange={e=>setOrgStatusFilter(e.target.value)}><option value="">Todos los estados</option>{['ACTIVE','PENDING','INACTIVE'].map(x=><option key={x}>{x}</option>)}</select></div>
        {filteredOrgs.map(item=><article className={`recycler-row ${selectedOrg===item.id?'recycler-row-selected':''}`} key={item.id} onClick={()=>setSelectedOrg(item.id)}><strong>{item.name}</strong><span>{item.type} · {item.city} · {item.sector_ids.length} sectores · {item.ecopoint_ids.length} EcoPuntos</span><small>{item.status}</small><button type="button" onClick={e=>{e.stopPropagation();editOrganization(item)}}>Ver / Editar</button><button type="button" disabled={saving} onClick={e=>{e.stopPropagation();void run(()=>updateOrganization(item.id,{status:item.status==='ACTIVE'?'INACTIVE':'ACTIVE'},token!),`Organización ${item.status==='ACTIVE'?'suspendida':'activada'}.`)}}>{item.status==='ACTIVE'?'Suspender':'Activar'}</button><button type="button" disabled={saving} onClick={e=>{e.stopPropagation();void run(()=>deleteOrganization(item.id,token!), 'Organización eliminada.') }}>Eliminar</button></article>)}
        {!filteredOrgs.length&&<p>No hay organizaciones con esos filtros.</p>}
        {selectedOrg&&organizations.find(item=>item.id===selectedOrg)&&<section className="recycler-detail"><h3>Detalle: {organizations.find(item=>item.id===selectedOrg)?.name}</h3><p>{organizations.find(item=>item.id===selectedOrg)?.description||'Sin descripción.'}</p><strong>Sectores:</strong> {organizations.find(item=>item.id===selectedOrg)?.sector_ids.map(id=>sectors.find(s=>s.id===id)?.name??id).join(', ')||'Sin sectores'}<br/><strong>Recicladores:</strong> {recyclers.filter(person=>person.organization_id===selectedOrg).map(person=>person.full_name).join(', ')||'Sin perfiles vinculados'}</section>}
        <h2 className="recycler-subheading">Sectores y puntos por sector</h2><form className="recycler-inline" onSubmit={saveSector}><label>Nombre del sector<input value={sectorName} onChange={e=>setSectorName(e.target.value)} required/></label><label>Localidad<input value={sectorLocality} onChange={e=>setSectorLocality(e.target.value)} required/></label><label>Ciudad<input value={sectorCity} onChange={e=>setSectorCity(e.target.value)} required/></label><Button disabled={saving}>Crear sector</Button></form>
        {sectors.map(sector=><SectorCoverage key={`${sector.id}:${sector.ecopoint_ids.join(',')}`} sector={sector} points={points} saving={saving} onSave={saveSectorPoints} onToggle={active=>void run(()=>updateSector(sector.id,{active},token!),`Sector ${active?'activado':'desactivado'}. Las autorizaciones fueron sincronizadas.`)}/>)}
      </div>
    </div>}

    {tab==='Recicladores'&&<div className="recycler-layout">
      <form className="panel recycler-form" onSubmit={saveRecycler}><h2>{editingRecycler?'Editar perfil':'Nuevo perfil de reciclador'}</h2>
        <label>Nombre completo<input value={recyclerDraft.full_name} onChange={e=>setRecyclerDraft({...recyclerDraft,full_name:e.target.value})} required/></label>
        <label>Correo<input type="email" value={recyclerDraft.email} onChange={e=>setRecyclerDraft({...recyclerDraft,email:e.target.value})} required/></label>
        {!editingRecycler&&<label>Contraseña inicial<input type="password" minLength={12} autoComplete="new-password" value={recyclerDraft.password??''} onChange={e=>setRecyclerDraft({...recyclerDraft,password:e.target.value})} required/><small>Mínimo 12 caracteres. Se almacena usando el hash de seguridad configurado.</small></label>}
        <label>Tipo de vinculación<select value={recyclerDraft.link_type} onChange={e=>setRecyclerDraft({...recyclerDraft,link_type:e.target.value as RecyclerDraft['link_type'],organization_id:e.target.value==='ORGANIZATION'?recyclerDraft.organization_id:null})}><option value="INDEPENDENT">Independiente</option><option value="ORGANIZATION">Organización</option></select></label>
        {recyclerDraft.link_type==='ORGANIZATION'&&<label>Organización<select value={recyclerDraft.organization_id??''} onChange={e=>setRecyclerDraft({...recyclerDraft,organization_id:e.target.value||null})} required><option value="">Selecciona una organización</option>{organizations.map(o=><option key={o.id} value={o.id}>{o.name} · {o.status}</option>)}</select></label>}
        <label>Teléfono<input value={recyclerDraft.phone??''} onChange={e=>setRecyclerDraft({...recyclerDraft,phone:e.target.value||null})}/></label>
        <label>Tipo de documento (opcional)<input value={recyclerDraft.document_type??''} onChange={e=>setRecyclerDraft({...recyclerDraft,document_type:e.target.value||null})}/></label>
        <label>Número de documento (opcional)<input value={recyclerDraft.document_number??''} onChange={e=>setRecyclerDraft({...recyclerDraft,document_number:e.target.value||null})}/></label>
        <label className="recycler-checkbox"><input type="checkbox" checked={recyclerDraft.is_active} onChange={e=>setRecyclerDraft({...recyclerDraft,is_active:e.target.checked})}/> Perfil activo</label>
        <div className="recycler-form-actions"><Button disabled={saving}>{saving?'Guardando…':editingRecycler?'Guardar cambios':'Crear cuenta'}</Button>{editingRecycler&&<Button type="button" variant="secondary" onClick={()=>{setEditingRecycler('');setRecyclerDraft(blankRecycler)}}>Cancelar</Button>}</div>
      </form>
      <div className="panel"><h2>Perfiles de reciclador</h2><div className="recycler-filters"><input placeholder="Buscar nombre o correo" value={recyclerSearch} onChange={e=>setRecyclerSearch(e.target.value)}/><select value={recyclerOrgFilter} onChange={e=>setRecyclerOrgFilter(e.target.value)}><option value="">Todas las organizaciones</option>{organizations.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select><select value={recyclerActiveFilter} onChange={e=>setRecyclerActiveFilter(e.target.value)}><option value="">Todos los estados</option><option value="true">Activos</option><option value="false">Suspendidos</option></select></div>
        {filteredRecyclers.map(person=><article className="recycler-row" key={person.id}><strong>{person.full_name}</strong><span>{person.email} · {person.link_type==='INDEPENDENT'?'Independiente':orgName(person.organization_id)}</span><small>{person.is_active?'Activo':'Suspendido'}</small><button type="button" onClick={()=>editRecycler(person)}>Ver / Editar</button><button type="button" disabled={saving} onClick={()=>void run(()=>updateRecycler(person.id,{is_active:!person.is_active},token!),`Perfil ${person.is_active?'suspendido':'activado'}; sus autorizaciones se sincronizaron.`)}>{person.is_active?'Suspender':'Activar'}</button></article>)}
        {!filteredRecyclers.length&&<p>No hay perfiles con esos filtros.</p>}
      </div>
    </div>}

    {tab==='Asignaciones'&&<div className="panel"><h2>Administrar autorizaciones</h2><form className="recycler-inline" onSubmit={saveDirectAssignment}><label>Asignación directa para independiente<select value={manualRecyclerId} onChange={e=>setManualRecyclerId(e.target.value)} required><option value="">Selecciona reciclador</option>{recyclers.filter(r=>r.link_type==='INDEPENDENT'&&r.is_active).map(r=><option key={r.id} value={r.id}>{r.full_name}</option>)}</select></label><label>Sector opcional<select value={manualSectorId} onChange={e=>setManualSectorId(e.target.value)}><option value="">Sin sector</option>{sectors.filter(s=>s.active).map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label><label>Universidad opcional<select value={manualUniversityId} onChange={e=>{setManualUniversityId(e.target.value);setManualEcopointId('')}}><option value="">Sin universidad</option>{universities.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select></label><label>EcoPunto opcional<select value={manualEcopointId} onChange={e=>setManualEcopointId(e.target.value)}><option value="">Sin EcoPunto</option>{points.filter(p=>!manualUniversityId||p.university_id===manualUniversityId).map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Vigente desde<input type="date" value={manualStartsAt} onChange={e=>setManualStartsAt(e.target.value)}/></label><label>Válida hasta<input type="date" value={manualEndsAt} onChange={e=>setManualEndsAt(e.target.value)}/></label><Button disabled={saving||!manualSectorId&&!manualUniversityId&&!manualEcopointId}>Crear asignación</Button></form><div className="recycler-filters assignment-filters">
      <select value={assignmentFilters.organization_id} onChange={e=>setAssignmentFilters({...assignmentFilters,organization_id:e.target.value})}><option value="">Todas las organizaciones</option>{organizations.map(o=><option key={o.id} value={o.id}>{o.name}</option>)}</select>
      <select value={assignmentFilters.recycler_id} onChange={e=>setAssignmentFilters({...assignmentFilters,recycler_id:e.target.value})}><option value="">Todos los recicladores</option>{recyclers.map(r=><option key={r.id} value={r.id}>{r.full_name}</option>)}</select>
      <select value={assignmentFilters.sector_id} onChange={e=>setAssignmentFilters({...assignmentFilters,sector_id:e.target.value})}><option value="">Todos los sectores</option>{sectors.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select>
      <select value={assignmentFilters.university_id} onChange={e=>setAssignmentFilters({...assignmentFilters,university_id:e.target.value})}><option value="">Todas las universidades</option>{universities.map(u=><option key={u.id} value={u.id}>{u.name}</option>)}</select>
      <select value={assignmentFilters.ecopoint_id} onChange={e=>setAssignmentFilters({...assignmentFilters,ecopoint_id:e.target.value})}><option value="">Todos los EcoPuntos</option>{points.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select>
      <select value={assignmentFilters.state} onChange={e=>setAssignmentFilters({...assignmentFilters,state:e.target.value})}><option value="">Todos los estados</option>{['ACTIVE','PENDING','INACTIVE','SUSPENDED'].map(x=><option key={x}>{x}</option>)}</select>
    </div><Button variant="secondary" onClick={()=>void run(async()=>setAssignments(await getAssignments(token!,undefined,assignmentFilters)), 'Filtros aplicados.')}>Aplicar filtros</Button>
    {assignments.map(item=><AssignmentRow key={item.id} item={item} recyclerName={recyclers.find(r=>r.id===item.recycler_id)?.full_name??item.recycler_id} scope={scopeName(item,sectors,points,universities)} saving={saving} onSave={data=>void run(()=>updateAssignment(item.id,data,token!), 'Asignación actualizada.')}/>)}
    {!assignments.length&&<p>No hay asignaciones para mostrar.</p>}<p className="recycler-help">Las autorizaciones automáticas heredan la cobertura de una organización. Las directas son administradas por ADMIN para perfiles independientes. Las filas vencidas o inactivas permanecen en el historial.</p></div>}
  </section>
}

function SectorCoverage({sector,points,saving,onSave,onToggle}:{sector:Sector;points:Point[];saving:boolean;onSave:(sector:Sector,ids:string[])=>void;onToggle:(active:boolean)=>void}) {
  const [ids,setIds]=useState(sector.ecopoint_ids)
  return <article className="sector-coverage"><div><strong>{sector.name}</strong><span>{sector.locality} · {sector.city} · {sector.active?'Activo':'Inactivo'}</span></div><label>EcoPuntos del sector<select multiple value={ids} onChange={e=>setIds(Array.from(e.target.selectedOptions,o=>o.value))}>{points.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><Button variant="secondary" disabled={saving} onClick={()=>onSave(sector,ids)}>Guardar puntos</Button><Button variant="secondary" disabled={saving} onClick={()=>onToggle(!sector.active)}>{sector.active?'Desactivar':'Activar'}</Button></article>
}

function AssignmentRow({item,recyclerName,scope,saving,onSave}:{item:Assignment;recyclerName:string;scope:string;saving:boolean;onSave:(data:Partial<Pick<Assignment,'status'|'starts_at'|'ends_at'|'notes'>>)=>void}) {
  return <article className="assignment-row"><div><strong>{recyclerName}</strong><span>{scope} · {item.origin==='AUTOMATIC'?'Heredada de organización':'Directa de ADMIN'}</span><small>Inicio {new Date(item.starts_at).toLocaleDateString('es-CO')} · {item.ends_at?`Fin ${new Date(item.ends_at).toLocaleDateString('es-CO')}`:'Sin fecha final'} · {item.status}</small></div><label>Estado<select defaultValue={item.status} onChange={e=>onSave({status:e.target.value})} disabled={saving}>{['ACTIVE','PENDING','INACTIVE','SUSPENDED'].map(x=><option key={x}>{x}</option>)}</select></label><label>Vigencia hasta<input type="date" defaultValue={item.ends_at?.slice(0,10)??''} disabled={saving} onBlur={e=>onSave({ends_at:e.target.value?new Date(`${e.target.value}T23:59:59Z`).toISOString():null})}/></label></article>
}

function scopeName(item:Assignment,sectors:Sector[],points:Point[],universities:University[]) {
  return [sectors.find(s=>s.id===item.sector_id)?.name,points.find(p=>p.id===item.ecopoint_id)?.name,universities.find(u=>u.id===item.university_id)?.name].filter(Boolean).join(' · ')||'Ámbito sin etiqueta'
}
function message(reason:unknown){return reason instanceof Error?reason.message:'No fue posible guardar los cambios.'}
