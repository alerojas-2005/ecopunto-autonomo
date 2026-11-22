import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from './client'

export type Organization = { id: string; name: string; type: string; city: string; status: string; tax_id: string | null; phone: string | null; email: string | null; address: string | null; description: string | null; created_at: string; updated_at: string; sector_ids:string[]; ecopoint_ids:string[] }
export type Recycler = { id: string; full_name: string; email: string; is_active: boolean; organization_id: string | null; organization_name: string | null; link_type: 'ORGANIZATION' | 'INDEPENDENT'; profile_status: string; phone: string | null; document_type: string | null; document_number: string | null; role: 'RECYCLER'; university_id: string | null; created_at: string }
export type Sector = { id: string; locality: string; name: string; city: string; description: string | null; active: boolean; ecopoint_ids: string[] }
export type Assignment = { id: string; recycler_id: string; organization_id: string | null; origin: 'DIRECT' | 'AUTOMATIC'; sector_id: string | null; university_id: string | null; ecopoint_id: string | null; starts_at: string; ends_at: string | null; status: string; notes: string | null; sector_name?:string|null; university_name?:string|null; ecopoint_name?:string|null }
export type OrganizationDraft = { name: string; type: string; tax_id: string | null; phone: string | null; email: string | null; address: string | null; city: string; description: string | null; status: string }
export type RecyclerDraft = { email: string; full_name: string; password?: string; organization_id: string | null; link_type: 'ORGANIZATION' | 'INDEPENDENT'; phone: string | null; document_type: string | null; document_number: string | null; is_active: boolean }
export type RecyclerDashboard = { profile:Recycler; assignments:Assignment[]; collections:{id:string;ecopoint_id:string;weight_kg:string;created_at:string;notes:string|null}[]; recovered_weight_kg:string; collection_count:number; material_weights:{material_name:string;weight_kg:string}[]; as_of:string }
export const getOrganizations = (token: string, signal?: AbortSignal, q?: string, state?: string, type?: string) => apiGet<Organization[]>(`/recyclers/organizations${query({q,state,type})}`, token, signal)
export const addOrganization = (data: OrganizationDraft, token: string) => apiPost<Organization, OrganizationDraft>('/recyclers/organizations', data, token)
export const updateOrganization = (id: string, data: Partial<OrganizationDraft>, token: string) => apiPatch<Organization, Partial<OrganizationDraft>>(`/recyclers/organizations/${encodeURIComponent(id)}`, data, token)
export const deleteOrganization = (id:string,token:string)=>apiDelete<void>(`/recyclers/organizations/${encodeURIComponent(id)}`,token)
export const setOrganizationCoverage = (id: string, sector_ids: string[], ecopoint_ids: string[], token: string) => apiPut<Organization, {sector_ids:string[];ecopoint_ids:string[]}>(`/recyclers/organizations/${encodeURIComponent(id)}/coverage`, {sector_ids,ecopoint_ids}, token)
export const getRecyclers = (token: string, signal?: AbortSignal, q?:string, organization_id?:string, active?:boolean) => apiGet<Recycler[]>(`/recyclers${query({q,organization_id,active:active===undefined?undefined:String(active)})}`, token, signal)
export const addRecycler = (data: RecyclerDraft & {password:string}, token: string) => apiPost<Recycler, unknown>('/recyclers', data, token)
export const updateRecycler = (id:string,data:Partial<RecyclerDraft>,token:string)=>apiPatch<Recycler,Partial<RecyclerDraft>>(`/recyclers/${encodeURIComponent(id)}`,data,token)
export const getSectors = (token: string, signal?: AbortSignal) => apiGet<Sector[]>('/recyclers/sectors', token, signal)
export const addSector = (data: { locality: string; name: string; city: string }, token: string) => apiPost<Sector, unknown>('/recyclers/sectors', data, token)
export const updateSector = (id:string,data:Partial<Pick<Sector,'name'|'locality'|'city'|'active'>>,token:string)=>apiPatch<Sector,typeof data>(`/recyclers/sectors/${encodeURIComponent(id)}`,data,token)
export const setSectorPoints = (id:string,ecopoint_ids:string[],token:string)=>apiPut<Sector,{ecopoint_ids:string[]}>(`/recyclers/sectors/${encodeURIComponent(id)}/ecopoints`,{ecopoint_ids},token)
export const getAssignments = (token: string, signal?: AbortSignal, filters:Record<string,string|undefined>={}) => apiGet<Assignment[]>(`/recyclers/assignments${query(filters)}`, token, signal)
export const getRecyclerDashboard = (token:string,signal?:AbortSignal)=>apiGet<RecyclerDashboard>('/recyclers/me/dashboard',token,signal)
export const addAssignment = (data: Partial<Assignment> & { recycler_id: string }, token: string) => apiPost<Assignment, unknown>('/recyclers/assignments', data, token)
export const updateAssignment = (id: string, data:Partial<Pick<Assignment,'status'|'starts_at'|'ends_at'|'notes'>>, token: string) => apiPatch<Assignment, typeof data>(`/recyclers/assignments/${encodeURIComponent(id)}`, data, token)

function query(values:Record<string,string|undefined>){const params=new URLSearchParams();for(const [key,value] of Object.entries(values))if(value!==undefined&&value!=='')params.set(key,value);const encoded=params.toString();return encoded?`?${encoded}`:''}
