import { AlertCircle, ArrowRight, Inbox, LoaderCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { label } from './api'

const statusTones: Record<string, 'positive' | 'critical' | 'warning' | 'accent'> = {
  approved: 'positive', supported: 'positive', active: 'positive', 'rule-based': 'positive',
  critical: 'critical', high: 'critical', rejected: 'critical', contradicted: 'critical',
  medium: 'warning', not_substantiated: 'warning', pending_approval: 'warning', changes_requested: 'warning',
  needs_human_review: 'warning', 'human review recommended': 'warning', contested: 'warning',
  reviewed: 'accent', low: 'accent', hybrid: 'accent', open: 'accent', 'optional ai assistance': 'accent',
}

export function statusTone(value: string) {
  const key = value.toLowerCase()
  return Object.hasOwn(statusTones, key) ? statusTones[key] : 'neutral'
}

export function Badge({ value }: { value: string }) {
  return <span className={'badge tone-' + statusTone(value)}>{label(value)}</span>
}
export function Notice({ children }: { children: ReactNode }) {
  return <div className="notice" role="alert"><AlertCircle size={17}/><span>{children}</span></div>
}
export function Loading({ children = 'Loading workspace…' }: { children?: ReactNode }) {
  return <div className="loading" role="status"><LoaderCircle size={18}/>{children}</div>
}
export function Empty({ title, children, action }: { title: string; children: ReactNode; action?: ReactNode }) {
  return <div className="empty"><span className="icon-tile"><Inbox size={20}/></span><h3>{title}</h3><p>{children}</p>{action}</div>
}
export function PageTitle({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="page-title"><div><h1>{title}</h1><p>{description}</p></div>{action}</div>
}
export function GoButton({ onClick, children }: { onClick: () => void; children: ReactNode }) {
  return <button className="button primary" onClick={onClick}>{children}<ArrowRight size={16}/></button>
}
export function Logo() {
  return <div className="logo"><img src="/brandguard.svg" alt="" width="36" height="36"/><span>BrandGuard <b>AI</b></span></div>
}
