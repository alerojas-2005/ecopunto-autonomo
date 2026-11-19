import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

export function Button({ children, variant = 'primary', ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'secondary' | 'ghost' }) {
  const { className, ...buttonProps } = props
  return <button className={`button button-${variant}${className ? ` ${className}` : ''}`} {...buttonProps}>{children}</button>
}

export function StatCard({ label, value, detail, icon, tone = 'green' }: { label: string; value: string; detail: string; icon: IconName; tone?: 'green' | 'mint' | 'amber' | 'blue' }) {
  return <article className="stat-card"><div className={`stat-icon tone-${tone}`}><Icon name={icon} size={21} /></div><div className="stat-label">{label}</div><strong className="stat-value">{value}</strong><div className="stat-detail">{detail}</div></article>
}

export function ProgressBar({ value, tone = 'green' }: { value: number; tone?: 'green' | 'amber' | 'red' }) {
  return <div className="progress-track" role="img" aria-label={`Nivel de llenado: ${value}%`}><span className={`progress-fill progress-${tone}`} style={{ width: `${value}%` }} /></div>
}

export function SectionHeading({ eyebrow, title, children }: { eyebrow?: string; title: string; children?: ReactNode }) {
  return <div className="section-heading"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h2>{title}</h2></div>{children}</div>
}

export function NavItem({ icon, label, active, badge, onClick }: { icon: IconName; label: string; active?: boolean; badge?: string; onClick: () => void }) {
  return <button className={`nav-item ${active ? 'is-active' : ''}`} onClick={onClick}><Icon name={icon} size={19} /><span>{label}</span>{badge && <b className="nav-badge">{badge}</b>}</button>
}
