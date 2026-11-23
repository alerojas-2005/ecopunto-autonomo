import { useState } from 'react'
import { useAuth } from './auth/useAuth'
import { AuthPage } from './auth/AuthPage'
import type { UserRole } from './api/types'
import { AdminCatalog } from './components/AdminCatalog'
import { AdminDeposits } from './components/AdminDeposits'
import { AdminManagement } from './components/AdminManagement'
import { AdminOverview } from './components/AdminOverview'
import { AdminRecyclers } from './components/AdminRecyclers'
import { RecyclerHome } from './components/RecyclerHome'
import { CitizenDashboard } from './components/CitizenDashboard'
import { CitizenPoints } from './components/CitizenPoints'
import { DepositForm } from './components/DepositForm'
import { DepositHistory } from './components/DepositHistory'
import { Icon, type IconName } from './components/Icon'
import { OperationsWorkspace } from './components/OperationsWorkspace'
import { SimulationPage } from './simulation/components/SimulationPage'
import { NavItem } from './components/UI'
import './auth/Session.css'
import './App.css'

type View =
  | 'Inicio'
  | 'Registrar depósito'
  | 'Mis EcoPuntos'
  | 'Historial'
  | 'Gestión de EcoPuntos'
  | 'Universidades y usuarios'
  | 'Recicladores y organizaciones'
  | 'Depósitos'
  | 'Alertas y recolecciones'
  | 'Simulación EcoPunto'
type NavigationItem = { label: View; icon: IconName }

const citizenNavigation: NavigationItem[] = [
  { label: 'Inicio', icon: 'home' },
  { label: 'Registrar depósito', icon: 'drop' },
  { label: 'Mis EcoPuntos', icon: 'points' },
  { label: 'Historial', icon: 'history' },
  { label: 'Simulación EcoPunto', icon: 'recycle' },
]

const adminNavigation: NavigationItem[] = [
  { label: 'Inicio', icon: 'home' },
  { label: 'Universidades y usuarios', icon: 'users' },
  { label: 'Recicladores y organizaciones', icon: 'truck' },
  { label: 'Gestión de EcoPuntos', icon: 'bins' },
  { label: 'Depósitos', icon: 'drop' },
  { label: 'Alertas y recolecciones', icon: 'bell' },
]

const recyclerNavigation: NavigationItem[] = [
  { label: 'Inicio', icon: 'home' },
  { label: 'Alertas y recolecciones', icon: 'bell' },
]

function App() {
  const { session, logout } = useAuth()
  const [view, setView] = useState<View>('Inicio')
  const [menuOpen, setMenuOpen] = useState(false)
  if (!session) return <AuthPage />

  const role = session.user.role
  const navigation = navigationFor(role)
  const firstName = session.user.full_name.trim().split(/\s+/)[0] || session.user.full_name
  const initials = session.user.full_name.trim().split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()
  const navigate = (next: View) => setView(next)
  const closeSession = () => { logout(); setView('Inicio'); setMenuOpen(false) }

  return <div className="app-shell">
    {menuOpen && <button className="sidebar-scrim" aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} />}
    <aside className={`sidebar ${menuOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Icon name="leaf" size={22} /></div><span>Eco<span>Punto</span></span></div>
      <div className="workspace-label">PLATAFORMA DE RECICLAJE</div>
      <div className="nav-caption">MENÚ PRINCIPAL</div>
      <nav className="main-nav" aria-label="Navegación principal">{navigation.map(item => <NavItem key={item.label} {...item} active={view === item.label} onClick={() => { navigate(item.label); setMenuOpen(false) }} />)}</nav>
      <div className="sidebar-bottom"><div className="impact-card"><div className="impact-icon"><Icon name="recycle" size={20} /></div><strong>Pequeñas acciones,<br />grandes cambios.</strong><span>Cada residuo cuenta para un futuro más limpio.</span><div className="impact-leaves"><Icon name="leaf" size={52} /></div></div><div className="sidebar-foot"><span className="online-dot" /> Plataforma EcoPunto</div></div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="topbar-left"><button className="mobile-menu" aria-label="Abrir menú" onClick={() => setMenuOpen(!menuOpen)}><Icon name={menuOpen ? 'close' : 'menu'} /></button><div className="breadcrumbs">EcoPunto <Icon name="chevron" size={14} /><strong>{view}</strong></div></div><div className="topbar-actions"><div className="profile"><div className="avatar">{initials}</div><div className="profile-copy"><strong>{session.user.full_name}</strong><span>{roleLabel(role)}</span></div></div><button className="logout-button" onClick={closeSession}>Cerrar sesión <Icon name="close" size={15}/></button></div></header>
      <div className="page-content">
        <div className="page-heading"><div><span className="eyebrow">{role === 'CITIZEN' ? 'TU IMPACTO, DÍA A DÍA' : role === 'ADMIN' ? 'CENTRO DE OPERACIONES' : 'OPERACIÓN INSTITUCIONAL'}</span><h1>{view === 'Inicio' ? `${role === 'CITIZEN' ? '¡Hola' : 'Hola'}, ${firstName}!` : view}</h1><p>{pageDescription(view, role)}</p></div><div className="role-badge"><span className="online-dot"/>{roleLabel(role)}</div></div>
        {view === 'Inicio' && role === 'CITIZEN' && <CitizenDashboard onNavigate={navigate} />}
        {view === 'Inicio' && role === 'ADMIN' && <AdminOverview onNavigate={navigate} />}
        {view === 'Inicio' && role === 'RECYCLER' && <RecyclerHome onNavigate={() => navigate('Alertas y recolecciones')} />}
        {view !== 'Inicio' && <Subpage view={view} role={role} />}
        <footer className="page-footer"><span>EcoPunto <span className="footer-dot">·</span> Construyendo un futuro circular</span><span>Plataforma multiuniversidad</span></footer>
      </div>
    </main>
  </div>
}

function navigationFor(role: UserRole) {
  if (role === 'CITIZEN') return citizenNavigation
  if (role === 'ADMIN') return adminNavigation
  return recyclerNavigation
}

function roleLabel(role: UserRole) {
  if (role === 'ADMIN') return 'Administrador'
  if (role === 'RECYCLER') return 'Reciclador'
  return 'Ciudadano'
}

function pageDescription(view: View, role: UserRole) {
  if (view === 'Inicio') {
    if (role === 'CITIZEN') return 'Consulta tus aportes, puntos y actividad registrada.'
    if (role === 'ADMIN') return 'Resumen global de los datos y operaciones de EcoPunto.'
    return 'Operaciones y alertas de tu universidad.'
  }
  const descriptions: Record<View, string> = {
    Inicio: '',
    'Registrar depósito': 'Registra un aporte en un EcoPunto disponible.',
    'Mis EcoPuntos': 'Consulta tu saldo y tus transacciones registradas.',
    Historial: 'Consulta tus depósitos e historial de puntos.',
    'Gestión de EcoPuntos': 'Administra puntos, materiales y compartimentos.',
    'Universidades y usuarios': 'Administra globalmente instituciones y cuentas.',
    'Recicladores y organizaciones': 'Administra organizaciones, perfiles y sectores de cobertura.',
    Depósitos: 'Consulta y filtra depósitos de todas las universidades.',
    'Alertas y recolecciones': 'Consulta alertas y recolecciones permitidas para tu rol.',
    'Simulación EcoPunto': 'Explora el funcionamiento de la máquina EcoPunto y conoce cómo se clasifican los residuos.',
  }
  return descriptions[view]
}

function Subpage({ view, role }: { view: View; role: UserRole }) {
  if (view === 'Simulación EcoPunto' && role === 'CITIZEN') {
    return <SimulationPage />
  }

  if (view === 'Simulación EcoPunto') {
    return (
      <section className="panel" role="alert">
        No tienes permisos para abrir esta pantalla.
      </section>
    )
  }
  if (view === 'Registrar depósito' && role === 'CITIZEN') return <DepositForm />
  if (view === 'Mis EcoPuntos' && role === 'CITIZEN') return <CitizenPoints />
  if (view === 'Historial' && role === 'CITIZEN') return <DepositHistory />
  if (view === 'Gestión de EcoPuntos' && role === 'ADMIN') return <AdminCatalog />
  if (view === 'Depósitos' && role === 'ADMIN') return <AdminDeposits />
  if (view === 'Universidades y usuarios' && role === 'ADMIN') return <AdminManagement />
  if (view === 'Recicladores y organizaciones' && role === 'ADMIN') return <AdminRecyclers />
  if (view === 'Alertas y recolecciones' && (role === 'ADMIN' || role === 'RECYCLER')) return <OperationsWorkspace role={role} />
  return <section className="panel" role="alert">No tienes permisos para abrir esta pantalla.</section>
}

export default App
