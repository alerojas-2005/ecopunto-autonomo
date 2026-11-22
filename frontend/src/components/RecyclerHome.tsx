import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getRecyclerDashboard, type RecyclerDashboard } from '../api/recyclers'
import { getEcoPoints } from '../api/catalog'
import { useAuth } from '../auth/useAuth'
import { Button, SectionHeading, StatCard } from './UI'
import { Icon } from './Icon'

export function RecyclerHome({onNavigate}:{onNavigate:()=>void}) {
  const {session,logout}=useAuth()
  const [data,setData]=useState<RecyclerDashboard|null>(null)
  const [pointNames,setPointNames]=useState<Record<string,string>>({})
  const [error,setError]=useState('')
  const [attempt,setAttempt]=useState(0)
  useEffect(()=>{
    if(!session?.token)return
    const controller=new AbortController()
    void Promise.all([getRecyclerDashboard(session.token,controller.signal),getEcoPoints(session.token,controller.signal)]).then(([dashboard,points])=>{setData(dashboard);setPointNames(Object.fromEntries(points.map(point=>[point.id,point.name]))) }).catch(reason=>{
      if(controller.signal.aborted)return
      if(reason instanceof ApiError&&reason.isUnauthorized)logout()
      else setError(reason instanceof Error?reason.message:'No se pudo cargar el dashboard.')
    })
    return ()=>controller.abort()
  },[session?.token,logout,attempt])
  const now=Date.parse(data?.as_of??'')
  const active=data?.assignments.filter(item=>item.status==='ACTIVE'&&new Date(item.starts_at).getTime()<=now&&(!item.ends_at||new Date(item.ends_at).getTime()>=now))??[]
  const distinct=(key:'sector_id'|'university_id'|'ecopoint_id')=>new Set(active.map(item=>item[key]).filter(Boolean)).size
  return <section className="recycler-overview">
    <div className="operations-toolbar"><div><span className="eyebrow">ESPACIO DE TRABAJO</span><strong>{data?.profile.full_name} · {data?.profile.organization_name??'Independiente'}</strong></div><Button type="button" variant="secondary" onClick={()=>setAttempt(v=>v+1)}><Icon name="refresh" size={15}/> Actualizar</Button></div>
    {error&&<p className="operations-message error" role="alert">{error}</p>}
    {!data?<p className="operations-state" role="status">{error?'No se pudo cargar el dashboard.':'Consultando tus asignaciones e historial…'}</p>:<>
      <div className="operations-stats"><StatCard label="Sectores asignados" value={String(distinct('sector_id'))} detail="Asignaciones vigentes" icon="location"/><StatCard label="Universidades" value={String(distinct('university_id'))} detail="Ámbito autorizado" icon="users"/><StatCard label="EcoPuntos autorizados" value={String(Object.keys(pointNames).length)} detail="Disponibles según autorización" icon="bins"/><StatCard label="Recolecciones realizadas" value={String(data.collection_count)} detail={`${Number(data.recovered_weight_kg).toLocaleString('es-CO')} kg recuperados`} icon="truck" tone="mint"/></div>
      <section className="panel recycler-next"><SectionHeading eyebrow="ASIGNACIONES VIGENTES" title="Mi cobertura"><div className="recycler-home-scope">{active.map(item=><span key={item.id}>{[item.sector_name,item.university_name,item.ecopoint_name].filter(Boolean).join(' · ')||'Ámbito asignado'}{item.ends_at?` · hasta ${new Date(item.ends_at).toLocaleDateString('es-CO')}`:' · vigente'}</span>)}{!active.length&&<p>No hay asignaciones activas en este momento.</p>}</div></SectionHeading></section>
      <section className="panel recycler-next"><SectionHeading eyebrow="HISTORIAL DE OPERACIONES" title="Recolecciones"><Button type="button" onClick={onNavigate}>Abrir recolecciones <Icon name="arrow" size={15}/></Button></SectionHeading><div className="recycler-dashboard-list">{data.collections.slice(0,8).map(item=><article key={item.id}><strong>{pointNames[item.ecopoint_id]??'EcoPunto asignado'}</strong><span>{Number(item.weight_kg).toLocaleString('es-CO')} kg · {new Date(item.created_at).toLocaleString('es-CO')}{item.notes?` · ${item.notes}`:''}</span></article>)}{!data.collections.length&&<p>Aún no hay recolecciones registradas.</p>}</div><h3>Material recuperado</h3><div className="recycler-materials">{data.material_weights.map(item=><span key={item.material_name}>{item.material_name}: {Number(item.weight_kg).toLocaleString('es-CO')} kg</span>)}</div></section>
    </>}
  </section>
}
