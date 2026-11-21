import { useState } from 'react'
import { Icon, type IconName } from './components/Icon'
import { Button, NavItem, ProgressBar, SectionHeading, StatCard } from './components/UI'
import { useAuth } from './auth/useAuth'
import { AuthPage } from './auth/AuthPage'
import type { UserRole } from './api/types'
import { DepositForm } from './components/DepositForm'
import { DepositHistory } from './components/DepositHistory'
import { AdminCatalog } from './components/AdminCatalog'
import { CitizenDashboard } from './components/CitizenDashboard'
import { CitizenPoints } from './components/CitizenPoints'
import './auth/Session.css'
import './App.css'

type Role = UserRole
type View = 'Inicio' | 'Registrar depósito' | 'Mis EcoPuntos' | 'Historial' | 'Beneficios' | 'Gestión de EcoPuntos' | 'Alertas y recolecciones'

const citizenNav: { label: View; icon: IconName }[] = [
  { label: 'Inicio', icon: 'home' }, { label: 'Registrar depósito', icon: 'drop' }, { label: 'Mis EcoPuntos', icon: 'points' }, { label: 'Historial', icon: 'history' },
]
const adminNav: { label: View; icon: IconName }[] = [
  { label: 'Inicio', icon: 'home' }, { label: 'Gestión de EcoPuntos', icon: 'bins' }, { label: 'Alertas y recolecciones', icon: 'bell' },
]
const recyclerNav: { label: View; icon: IconName }[] = [
  { label: 'Inicio', icon: 'home' }, { label: 'Alertas y recolecciones', icon: 'bell' },
]


function App() {
  const { session, logout } = useAuth()
  const [view, setView] = useState<View>('Inicio')
  const [menuOpen, setMenuOpen] = useState(false)
  const role = session?.user.role
  const navigation = role === 'CITIZEN' ? citizenNav : role === 'ADMIN' ? adminNav : recyclerNav

  const handleLogout = () => {
    logout()
    setView('Inicio')
    setMenuOpen(false)
  }

  if (!session || !role) return <AuthPage />

  const firstName = session.user.full_name.split(' ')[0] || session.user.full_name
  const initials = session.user.full_name.split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()

  return <div className="app-shell">
    {menuOpen && <button className="sidebar-scrim" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} />}
    <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Icon name="leaf" size={22} /></div><span>Eco<span>Punto</span></span></div>
      <div className="workspace-label">PLATAFORMA DE RECICLAJE</div>
      <div className="nav-caption">MENÚ PRINCIPAL</div>
      <nav className="main-nav" aria-label="Navegación principal">{navigation.map(item => <NavItem key={item.label} {...item} active={view === item.label} badge={item.label === 'Alertas y recolecciones' ? '3' : undefined} onClick={() => { setView(item.label); setMenuOpen(false) }} />)}</nav>
      <div className="sidebar-bottom"><div className="impact-card"><div className="impact-icon"><Icon name="recycle" size={20} /></div><strong>Pequeñas acciones,<br />grandes cambios.</strong><span>Cada residuo cuenta para un futuro más limpio.</span><div className="impact-leaves"><Icon name="leaf" size={52} /></div></div><div className="sidebar-foot"><span className="online-dot" /> Plataforma de demostración</div></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu" aria-label="Abrir menú" onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? 'close' : 'menu'} /></button><div className="breadcrumbs">EcoPunto <Icon name="chevron" size={14} /><strong>{view}</strong></div></div><div className="topbar-actions">{role !== 'CITIZEN' && <span className="demo-tag"><span /> Datos de demostración</span>}<div className="profile"><div className="avatar">{initials}</div><div className="profile-copy"><strong>{session.user.full_name}</strong><span>{roleLabel(role)}</span></div></div><button className="logout-button" onClick={handleLogout}>Cerrar sesión <Icon name="close" size={15}/></button></div></header>
      <div className="page-content">
        <div className="demo-banner"><Icon name="info" size={17}/><span>{role === 'CITIZEN' ? (view === 'Beneficios' ? 'El catálogo de beneficios y las redenciones todavía no están conectados al backend.' : 'La información de tu cuenta en esta pantalla se consulta desde EcoPunto.') : view === 'Registrar depósito' ? 'Los catálogos, el registro del depósito, el cálculo de puntos y las actualizaciones se gestionan desde la API.' : view === 'Gestión de EcoPuntos' ? 'EcoPuntos, materiales y compartimentos se consultan y gestionan desde la API.' : 'Las métricas y listas de esta vista siguen siendo datos de demostración y todavía no se consultan desde la API.'}</span></div>
        <div className="page-heading"><div><span className="eyebrow">{role === 'CITIZEN' ? 'TU IMPACTO, DÍA A DÍA' : role === 'ADMIN' ? 'CENTRO DE OPERACIONES' : 'PANEL DE RECICLADOR'}</span><h1>{view === 'Inicio' ? (role === 'CITIZEN' ? `¡Hola, ${firstName}!` : `Hola, ${firstName}`) : view}</h1><p>{pageDescription(view, role)}</p></div><div className="role-badge"><span className="online-dot"/>{roleLabel(role)}</div></div>

        {view === 'Inicio' && (role === 'CITIZEN' ? <CitizenDashboard onNavigate={setView} /> : role === 'ADMIN' ? <AdminDashboard onNavigate={setView} /> : <RecyclerWelcome fullName={session.user.full_name} />)}
        {view !== 'Inicio' && <Subpage view={view} role={role} onNavigate={setView} />}
        <footer className="page-footer"><span>EcoPunto <span className="footer-dot">·</span> Construyendo un futuro circular</span><span>Prototipo visual <span className="footer-dot">·</span> 2026</span></footer>
      </div>
    </main>
  </div>
}

function roleLabel(role: Role) {
  return role === 'CITIZEN' ? 'Ciudadano' : role === 'ADMIN' ? 'Administrador' : 'Reciclador'
}

function pageDescription(view: View, role: Role) {
  if (view === 'Inicio') return role === 'CITIZEN' ? 'Cada material que separas ayuda a construir una ciudad más sostenible.' : role === 'ADMIN' ? 'Una mirada clara al estado de la red de puntos de reciclaje.' : 'Información de tu sesión y acceso a las herramientas de recolección.'
  const descriptions: Record<View, string> = { Inicio: '', 'Registrar depósito': 'Prepara tu próximo aporte al ciclo de aprovechamiento.', 'Mis EcoPuntos': 'Consulta tu saldo y tus transacciones registradas.', Historial: 'Un registro de tus aportes a la economía circular.', Beneficios: 'Esta funcionalidad todavía no está disponible.', 'Gestión de EcoPuntos': 'Monitorea capacidad, ubicación y estado de cada punto.', 'Alertas y recolecciones': 'Novedades operativas y próximas rutas de recolección.' }
  return descriptions[view]
}

function AdminDashboard({ onNavigate }: { onNavigate: (view: View) => void }) {
  const bins = [{ name: 'EcoPunto Parque Central', location: 'Chapinero · Bogotá', fill: 82, material: 'Plástico y latas', tone: 'amber' as const }, { name: 'EcoPunto Universidad', location: 'Usaquén · Bogotá', fill: 46, material: 'Papel y cartón', tone: 'green' as const }, { name: 'EcoPunto Centro', location: 'La Candelaria · Bogotá', fill: 91, material: 'Mixto aprovechable', tone: 'red' as const }]
  return <>
    <div className="stats-grid admin-stats"><StatCard label="EcoPuntos activos" value="12" detail="En toda la red" icon="bins"/><StatCard label="Material recuperado" value="348 kg" detail="Este mes · +12%" icon="weight" tone="mint"/><StatCard label="Alertas pendientes" value="3" detail="Requieren seguimiento" icon="bell" tone="amber"/><StatCard label="Recolecciones hoy" value="5" detail="2 rutas programadas" icon="truck" tone="blue"/></div>
    <section className="admin-grid"><div className="panel bins-panel"><SectionHeading eyebrow="ESTADO DE LA RED" title="Nivel de llenado"><button className="text-link" onClick={() => onNavigate('Gestión de EcoPuntos')}>Ver todos <Icon name="arrow" size={16}/></button></SectionHeading><div className="bin-list">{bins.map(bin => <div className="bin-row" key={bin.name}><div className="bin-symbol"><Icon name="bins" size={19}/></div><div className="bin-main"><div className="bin-title"><strong>{bin.name}</strong><span className={`fill-label fill-${bin.tone}`}>{bin.fill}%</span></div><span className="bin-location"><Icon name="location" size={13}/>{bin.location} · {bin.material}</span><ProgressBar value={bin.fill} tone={bin.tone}/></div></div>)}</div></div>
      <div className="panel chart-panel"><SectionHeading eyebrow="RECUPERACIÓN" title="Material recolectado"/><div className="chart-total">348 <span>kg <small>este mes</small></span><span className="chart-growth"><Icon name="trend" size={14}/> 12%</span></div><MiniChart/><div className="chart-legend"><span><i className="legend-green"/>Este mes</span><span><i className="legend-pale"/>Mes anterior</span></div></div></section>
    <section className="panel alerts-panel"><SectionHeading eyebrow="REQUIERE ATENCIÓN" title="Alertas recientes"><button className="text-link" onClick={() => onNavigate('Alertas y recolecciones')}>Ver alertas <Icon name="arrow" size={16}/></button></SectionHeading><div className="alert-row"><div className="alert-indicator alert-red"><Icon name="bins" size={19}/></div><div className="alert-copy"><strong>EcoPunto Centro casi lleno</strong><span>La Candelaria · Nivel de llenado al 91%</span></div><span className="alert-time">Hace 12 min</span><button className="small-action" onClick={() => onNavigate('Alertas y recolecciones')}>Programar recolección <Icon name="arrow" size={14}/></button></div><div className="alert-row"><div className="alert-indicator alert-amber"><Icon name="clock" size={19}/></div><div className="alert-copy"><strong>Recolección pendiente</strong><span>EcoPunto Parque Central · Ruta norte</span></div><span className="alert-time">Hace 1 h</span><button className="small-action" onClick={() => onNavigate('Alertas y recolecciones')}>Ver detalle <Icon name="arrow" size={14}/></button></div></section>
  </>
}

function MiniChart() {
  const current = [35, 47, 40, 62, 53, 76, 67, 88, 72, 92, 82, 100]
  const previous = [28, 38, 33, 50, 44, 59, 55, 68, 63, 75, 70, 82]
  return <div className="mini-chart"><div className="chart-y-labels"><span>100</span><span>75</span><span>50</span><span>25</span><span>0</span></div><div className="chart-plot"><div className="chart-gridlines"><i/><i/><i/><i/><i/></div><div className="chart-bars">{current.map((v, i) => <div className="bar-group" key={i}><span className="bar bar-previous" style={{ height: `${previous[i]}%` }}/><span className="bar bar-current" style={{ height: `${v}%` }}/></div>)}</div></div><div className="chart-x-labels"><span>1 nov</span><span>7 nov</span><span>14 nov</span><span>21 nov</span><span>30 nov</span></div></div>
}

function RecyclerWelcome({ fullName }: { fullName: string }) {
  return <section className="panel recycler-welcome"><div className="recycler-welcome-icon"><Icon name="truck" size={24}/></div><span className="eyebrow">SESIÓN AUTENTICADA</span><h2>Hola, {fullName}</h2><p>Tu perfil está identificado como reciclador. Las alertas y el registro virtual de recolecciones estarán disponibles cuando conectemos esas pantallas con la API.</p><div className="recycler-status"><span className="online-dot"/> Rol confirmado desde el backend</div></section>
}

function Subpage({ view, role, onNavigate }: { view: View; role: Role; onNavigate: (view: View) => void }) {
  if (view === 'Registrar depósito') return <DepositForm />
  if (view === 'Mis EcoPuntos') return <CitizenPoints />
  if (view === 'Beneficios') return <section className="panel placeholder-panel"><div className="placeholder-icon"><Icon name="gift" size={24}/></div><h3>Beneficios no disponibles</h3><p>El catálogo de beneficios y las redenciones todavía no están conectados al backend.</p></section>
  if (view === 'Historial') return <DepositHistory />
  if (view === 'Gestión de EcoPuntos') return <AdminCatalog />
  return <section className="panel bins-panel"><SectionHeading eyebrow="CENTRO DE OPERACIONES" title="Alertas y recolecciones"/><div className="route-banner"><div className="route-icon"><Icon name="truck" size={23}/></div><div><strong>Próxima ruta de recolección</strong><span>Ruta norte · Hoy, 2:30 p. m. · 3 puntos programados</span></div><Button variant="secondary">Ver ruta <Icon name="arrow" size={16}/></Button></div>{['EcoPunto Centro · 91% de llenado · Prioridad alta', 'EcoPunto Parque Central · 82% de llenado · Programar hoy', 'Recolección de papel · Universidad · Programada para mañana'].map((text, index) => <div className="alert-row page-alert" key={text}><div className={`alert-indicator ${index === 0 ? 'alert-red' : 'alert-amber'}`}><Icon name={index === 2 ? 'calendar' : 'bell'} size={19}/></div><div className="alert-copy"><strong>{text.split(' · ')[0]}</strong><span>{text.split(' · ').slice(1).join(' · ')}</span></div><span className={`status-pill ${index === 0 ? 'status-red' : 'status-amber'}`}>{index === 0 ? 'Crítico' : 'Pendiente'}</span><Button variant="ghost" onClick={() => onNavigate(role === 'ADMIN' ? 'Gestión de EcoPuntos' : 'Inicio')}>Ver <Icon name="arrow" size={15}/></Button></div>)}</section>
}

export default App
