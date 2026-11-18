import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Activity, ArrowRight, BookOpen, ChevronRight, ClipboardCheck, FileCheck2, FileText, History, LayoutDashboard, Menu, PanelLeftClose, Settings2, ShieldCheck, Sparkles, X } from 'lucide-react'
import { api, ApiError, type Role, type Session, useTask } from './api'
import { Loading, Logo, Notice } from './ui'
import { ReviewPage } from './Review'
import { KnowledgePage, SettingsPage } from './Knowledge'
import { Dashboard, SubmissionList } from './Dashboard'
import { Governance } from './Governance'

const pages = [
  ['overview', 'Overview', LayoutDashboard],
  ['review', 'Content Review', FileText],
  ['knowledge', 'Brand Knowledge', BookOpen],
  ['queue', 'Approval Queue', ClipboardCheck],
  ['history', 'Review History', History],
  ['analytics', 'Analytics', Activity],
  ['governance', 'Campaign governance', ClipboardCheck],
  ['settings', 'Settings', Settings2],
] as const
type Page = typeof pages[number][0]

function route() {
  const [page, id, revision, assessment] = location.hash.slice(1).split('/')
  return { page: pages.find(([key]) => key === page)?.[0] || 'overview', id, revision, assessment }
}

function Welcome({ start, busy, error }: { start: () => void; busy: boolean; error: string }) {
  return <div className="welcome">
    <header className="welcome-header"><Logo/><span>CODERX · CODENOVA INDIA 2026</span></header>
    <main className="welcome-main">
      <div className="welcome-copy">
        <span className="workspace-tag"><span className="dot"/> Brand governance workspace</span>
        <h1>Create freely.<br/>Stay <em>on-brand.</em></h1>
        <p>Check marketing content against approved brand guidelines, fix issues with evidence in view, and get a human sign-off before publishing.</p>
        <button className="button primary welcome-cta" onClick={start} disabled={busy}>{busy ? 'Creating workspace…' : 'Try Live Demo'}<ArrowRight size={19}/></button>
        <small>Includes a private NovaTech sample workspace. No account required.</small>
        {error && <Notice>{error}</Notice>}
      </div>
      <section className="welcome-flow panel glass" aria-label="Review workflow">
        <div className="flow-head"><span className="icon-tile"><ShieldCheck size={24}/></span><div><strong>From draft to decision</strong><p>NovaTech sample workspace</p></div></div>
        {[
          { icon: FileText, title: 'Review a marketing draft', copy: 'Review copy, import a document or attach campaign artwork.' },
          { icon: Sparkles, title: 'Resolve findings with evidence', copy: 'See the brand rule behind each recommendation.' },
          { icon: FileCheck2, title: 'Get human approval', copy: 'Switch to a sample reviewer and record a decision.' },
        ].map(({ icon: Icon, title, copy }) => <div className="flow-step" key={title}><span className="flow-icon"><Icon size={19}/></span><div><strong>{title}</strong><p>{copy}</p></div></div>)}
      </section>
    </main>
    <footer><ShieldCheck size={15}/> BrandGuard AI</footer>
  </div>
}

export function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)
  const [current, setCurrent] = useState(route)
  const [collapsed, setCollapsed] = useState(false)
  const [mobile, setMobile] = useState(false)
  const [startupError, setStartupError] = useState('')
  const [demo, setDemo] = useState(false)
  const [key, setKey] = useState('')
  const navigationToggle = useRef<HTMLButtonElement>(null)
  const navigationClose = useRef<HTMLButtonElement>(null)
  const task = useTask()
  useEffect(() => {
    const sync = () => { setCurrent(route()); setMobile(false); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])
  useEffect(() => {
    void api<{demo: boolean}>('/access').then(access => { setDemo(access.demo); return api<Session>('/session') }).then(setSession).catch(error => {
      setSession(null)
      if (!(error instanceof ApiError && error.status === 401)) setStartupError('The workspace could not be loaded. Check the connection and try again.')
    })
  }, [])
  useEffect(() => {
    if (!mobile) return
    const mobileViewport = window.matchMedia('(max-width: 810px)')
    const toggle = navigationToggle.current
    const closeOnDesktop = () => { if (!mobileViewport.matches) setMobile(false) }
    navigationClose.current?.focus()
    mobileViewport.addEventListener('change', closeOnDesktop)
    return () => {
      mobileViewport.removeEventListener('change', closeOnDesktop)
      toggle?.focus()
    }
  }, [mobile])
  function handleNavigationKeys(event: KeyboardEvent<HTMLElement>) {
    if (!mobile) return
    if (event.key === 'Escape') {
      event.preventDefault()
      setMobile(false)
    }
    if (event.key !== 'Tab') return
    const first = navigationClose.current
    const last = event.currentTarget.querySelector<HTMLAnchorElement>('nav a:last-child')
    const from = event.shiftKey ? first : last
    const to = event.shiftKey ? last : first
    if (event.target === from && to) {
      event.preventDefault()
      to.focus()
    }
  }
  function go(page: Page, id?: string) { location.hash = page + (id ? '/' + id : '') }
  function start() { void task.run(async () => {
    setSession(await api<Session>('/demo', 'POST'))
    go('overview')
  }) }
  function changeRole(role: Role) { void task.run(async () => setSession(await api<Session>('/demo/role', 'PUT', { role }))) }
  if (session === undefined) return <Loading/>
  if (!session && demo) return <Welcome start={start} busy={task.pending} error={task.error || startupError}/>
  if (!session) return <main className="team-login"><Logo/><form className="panel form-card" onSubmit={event => {
    event.preventDefault()
    void task.run(async () => { setSession(await api<Session>('/login', 'POST', {key})); setKey('') })
  }}>
    <h1>Workspace sign-in</h1><p>Use the private access key issued by your workspace administrator.</p>
    <label>Workspace key<input type="password" autoComplete="current-password" required value={key} onChange={e => setKey(e.target.value)}/></label>
    {(task.error || startupError) && <Notice>{task.error || startupError}</Notice>}
    <button className="button primary" disabled={task.pending}>Sign in</button>
  </form></main>
  const open = (id: string) => go('review', id)
  const activePage = pages.find(([page]) => page === current.page)?.[1]
  return <div className={'shell' + (collapsed ? ' collapsed' : '')}>
    <a className="skip" href="#main-content" inert={mobile || undefined} onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus() }}>Skip to content</a>
    {mobile && <div className="mobile-overlay" aria-hidden="true" onClick={() => setMobile(false)}/>}
    <aside id="workspace-sidebar" className={'sidebar' + (mobile ? ' mobile-open' : '')}
      role={mobile ? 'dialog' : undefined} aria-modal={mobile || undefined} aria-label={mobile ? 'Workspace menu' : undefined} onKeyDown={handleNavigationKeys}>
      <div className="side-top"><Logo/><button ref={navigationClose} className="icon-button close-mobile" aria-label="Close navigation" onClick={() => setMobile(false)}><X size={20}/></button></div>
      <div className="workspace"><span className="workspace-avatar">{session.profile.name.slice(0, 1)}</span><div><strong>{session.profile.name}</strong><small>{session.demo ? 'Sample workspace' : 'Team workspace'}</small></div></div>
      <nav aria-label="Workspace navigation">
        {pages.map(([key, title, Icon]) => <a key={key} href={'#' + key} title={title} aria-label={title}
          aria-current={current.page === key ? 'page' : undefined} onClick={() => setMobile(false)}><Icon size={19}/><span>{title}</span></a>)}
      </nav>
      <div className="side-bottom">
        <button className="icon-button collapse" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => setCollapsed(!collapsed)}><PanelLeftClose size={18}/><span>Collapse sidebar</span></button>
      </div>
    </aside>
    <div className="main-area" inert={mobile || undefined}>
      <header className="topbar">
        <div className="breadcrumb">
          <button ref={navigationToggle} className="icon-button mobile-toggle" aria-label="Open navigation" aria-expanded={mobile} aria-controls="workspace-sidebar" onClick={() => setMobile(true)}><Menu size={21}/></button>
          <span className="crumb-brand">{session.profile.name}</span><ChevronRight className="crumb-divider" size={14} aria-hidden="true"/><strong>{activePage}</strong>
        </div>
        <div className="identity"><span className="person-avatar">{session.actor.split(' ').map(word => word[0]).join('').slice(0,2)}</span><div><strong>{session.actor}</strong><label htmlFor="demo-role">{session.demo ? 'Demo role' : session.role}</label></div>
          {session.demo ? <select id="demo-role" aria-label="Demo role" value={session.role} disabled={task.pending} onChange={event => changeRole(event.target.value as Role)}>
            <option value="creator">Creator</option><option value="reviewer">Reviewer</option><option value="admin">Admin</option>
          </select> : <button className="button secondary small" onClick={() => void task.run(async () => {
            await api('/logout', 'POST'); setSession(null); go('overview')
          })}>Sign out</button>}
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        {task.error && <Notice>{task.error}</Notice>}
        {(current.page === 'overview' || current.page === 'analytics') && <Dashboard key={current.page} analytics={current.page === 'analytics'} open={open} create={() => go('review')} knowledge={() => go('knowledge')} queue={() => go('queue')} history={() => go('history')} session={session}/>}
        {current.page === 'review' && <ReviewPage key={[current.id,current.assessment].join('/')} id={current.id} revision={current.revision} reviewId={current.assessment} session={session} open={open} queue={() => go('queue')}/>}
        {current.page === 'governance' && <Governance/>}
        {current.page === 'knowledge' && <KnowledgePage session={session}/>}
        {(current.page === 'queue' || current.page === 'history') && <SubmissionList key={current.page} queue={current.page === 'queue'} open={open} create={() => go('review')}/>}
        {current.page === 'settings' && <SettingsPage session={session} update={setSession}/>}
      </main>
      <footer className="app-footer">BrandGuard AI · CoderX</footer>
    </div>
  </div>
}
