import type { ReactNode, SVGProps } from 'react'

export type IconName = 'home' | 'drop' | 'points' | 'history' | 'gift' | 'bins' | 'bell' | 'leaf' | 'menu' | 'close' | 'arrow' | 'weight' | 'recycle' | 'clock' | 'chevron' | 'plus' | 'location' | 'camera' | 'check' | 'calendar' | 'truck' | 'trend' | 'info'

const paths: Record<IconName, ReactNode> = {
  home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9M9 20v-6h6v6"/></>,
  drop: <><path d="M12 3s7 7.2 7 12a7 7 0 1 1-14 0c0-4.8 7-12 7-12Z"/><path d="M9 16a3 3 0 0 0 3 2"/></>,
  points: <><circle cx="12" cy="12" r="9"/><path d="m12 7 1.4 3.6L17 12l-3.6 1.4L12 17l-1.4-3.6L7 12l3.6-1.4L12 7Z"/></>,
  history: <><path d="M3 12a9 9 0 1 0 2.6-6.4L3 8"/><path d="M3 3v5h5m4-1v5l3 2"/></>,
  gift: <><rect x="3" y="8" width="18" height="13" rx="2"/><path d="M12 8v13M3 12h18M12 8H7a2.5 2.5 0 1 1 2.5-2.5C9.5 7 12 8 12 8Zm0 0h5a2.5 2.5 0 1 0-2.5-2.5C14.5 7 12 8 12 8Z"/></>,
  bins: <><path d="M4 7h16M10 11v6m4-6v6M6 7l1 14h10l1-14M9 7V4h6v3"/><path d="m4 7 2-2m14 2-2-2"/></>,
  bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
  leaf: <><path d="M20 4c-8 0-14 3-14 10a6 6 0 0 0 6 6c7 0 10-8 8-16Z"/><path d="M4 21c3-6 7-9 12-12"/></>,
  menu: <><path d="M4 6h16M4 12h16M4 18h16"/></>, close: <><path d="m6 6 12 12M18 6 6 18"/></>,
  arrow: <><path d="M5 12h14m-6-6 6 6-6 6"/></>, weight: <><path d="M6 7h12l2 14H4L6 7Z"/><path d="M9 7a3 3 0 1 1 6 0m-3 4 2 3"/></>,
  recycle: <><path d="m7 7 2-3 3 1M17 17l2 3-3 1M5 15l-3-1 1-3M9 4l2 4m8 9-4-1m-8-1 2-4"/><path d="m6 8 3-4m7 16 3-4M2 14l4-1"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>, chevron: <path d="m9 18 6-6-6-6"/>,
  plus: <><path d="M12 5v14M5 12h14"/></>, location: <><path d="M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></>,
  camera: <><path d="M4 7h3l2-3h6l2 3h3a2 2 0 0 1 2 2v10H2V9a2 2 0 0 1 2-2Z"/><circle cx="12" cy="13" r="3"/></>,
  check: <path d="m5 12 4 4L19 6"/>, calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18"/></>,
  truck: <><path d="M3 6h11v12H3zM14 10h4l3 3v5h-7z"/><circle cx="7.5" cy="18" r="1.5"/><circle cx="17.5" cy="18" r="1.5"/></>,
  trend: <><path d="m3 17 6-6 4 4 8-9"/><path d="M15 6h6v6"/></>,
  info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/></>,
}

export function Icon({ name, size = 20, ...props }: SVGProps<SVGSVGElement> & { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>
}
