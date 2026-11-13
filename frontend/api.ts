import { useEffect, useState } from 'react'

export type Role = 'creator' | 'reviewer' | 'admin'
export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type Profile = Record<'name' | 'description' | 'industry' | 'audience' | 'personality' | 'style' | 'tone' | 'primary_color' | 'secondary_color', string>
export type Session = { role: Role; actor: string; profile: Profile; workspace_id: string; ai_available: boolean; sample: string }
export type Source = { id: string; title: string; content: string; version: number }
export type RuleSpec = {
  title: string; category: string; kind: 'phrase' | 'required' | 'price_floor' | 'approved_fact';
  description: string; severity: Severity; pattern: string; replacement: string; source_id: string;
  value: number | null; valid_from: string | null; valid_until: string | null; active: boolean
}
export type Rule = { id: string; spec: RuleSpec; active: boolean; version: number; source_title: string; updated_at: string }
export type Knowledge = { sources: Source[]; rules: Rule[] }
export type Finding = {
  id: string; category: string; severity: Severity; original_text: string; explanation: string;
  suggested_correction: string; evidence_status: string; requires_human_review: boolean;
  rule_id: string | null; rule_title: string | null; rule_version: number | null;
  source_id: string | null; source_title: string | null; source_version: number | null;
  source_excerpt: string | null; status: string; reason: string | null
}
export type Assessment = { id: string; created_at: string; mode: string; rules_checked: number; notice: string | null; findings: Finding[] }
export type Version = { id: string; number: number; content: string; created_at: string; reviews: Assessment[] }
export type Action = { id: string; version_id: string; actor: string; action: string; comment: string; created_at: string }
export type Summary = {
  id: string; title: string; content_type: string; platform: string; status: string;
  revision: number; generation: number; creator: string; updated_at: string; created_at: string
}
export type Submission = Summary & { versions: Version[]; actions: Action[] }
export type Metrics = {
  total: number; violations: number; statuses: Record<string, number>; categories: Record<string, number>;
  severity: Record<string, number>; rules: Record<string, number>; trends: Record<string, number>
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}
export async function api<T>(url: string, method = 'GET', body?: object): Promise<T> {
  const isFile = body instanceof FormData
  const response = await fetch('/api' + url, {
    method, headers: body && !isFile ? { 'Content-Type': 'application/json' } : undefined,
    body: isFile ? body : body ? JSON.stringify(body) : undefined,
  })
  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = payload?.detail
    const message = Array.isArray(detail) ? detail.map(issue => issue.msg).join(' ') : detail
    throw new ApiError(response.status, typeof message === 'string' ? message : 'The request failed. Please try again.')
  }
  return payload
}
export function readFile(file: File) {
  const data = new FormData()
  data.append('file', file)
  return api<{ title: string; content: string }>('/extract', 'POST', data)
}
export const label = (value: string) =>
  value.toLowerCase().replaceAll('_', ' ').replace(/^./, letter => letter.toUpperCase())
export const dateLabel = (value: string) =>
  new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    .format(new Date(/Z$|[+-]\d\d:\d\d$/.test(value) ? value : value + 'Z'))

export function useTask() {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  async function run(task: () => Promise<void>) {
    setPending(true)
    setError('')
    setMessage('')
    try { await task() } catch (error) {
      setError(error instanceof Error ? error.message : 'Something went wrong.')
    } finally { setPending(false) }
  }
  return { pending, error, message, setMessage, run }
}

export function useData<T>(endpoint: string) {
  const [data, setData] = useState<T>()
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  useEffect(() => {
    let current = true
    void api<T>(endpoint).then(value => {
      if (current) { setData(value); setError('') }
    }).catch(error => { if (current) setError(error.message) })
    return () => { current = false }
  }, [endpoint, reload])
  return { data, setData, error, refresh: () => setReload(value => value + 1) }
}
