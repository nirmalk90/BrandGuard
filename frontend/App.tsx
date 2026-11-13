import { useEffect, useState } from 'react'
import { Activity, ArrowRight, BookOpen, ClipboardCheck, FileCheck2, FileText, History, LayoutDashboard, Menu, PanelLeftClose, Settings2, ShieldCheck, Sparkles, X } from 'lucide-react'
import { api, ApiError, type Role, type Session, useTask } from './api'
import { Badge, Loading, Logo, Notice } from './ui'
import { ReviewPage } from './Review'
import { KnowledgePage, SettingsPage } from './Knowledge'
import { Dashboard, SubmissionList } from './Dashboard'

const pages = [
  ['overview', 'Overview', LayoutDashboard],
  ['review', 'Content Review', FileText],
  ['knowledge', 'Brand Knowledge', BookOpen],
  ['queue', 'Approval Queue', ClipboardCheck],
  ['history', 'Review History', History],
  ['analytics', 'Analytics', Activity],
  ['settings', 'Settings', Settings2],
] as const
type Page = typeof pages[number][0]

function route() {
  const [page, id] = location.hash.slice(1).split('/')
  return { page: pages.find(([key]) => key === page)?.[0] || 'overview', id }
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
      <section className="welcome-flow panel" aria-label="Review workflow">
        <div className="flow-head"><span className="icon-tile"><ShieldCheck size={24}/></span><div><strong>From draft to decision</strong><p>NovaTech sample workspace</p></div></div>
        {[
          { icon: FileText, title: 'Review a marketing draft', copy: 'Start with sample copy or upload a document.' },
          { icon: Sparkles, title: 'Resolve findings with evidence', copy: 'See the brand rule behind each recommendation.' },
          { icon: FileCheck2, title: 'Get human approval', copy: 'Switch to a sample reviewer and record a decision.' },
        ].map(({ icon: Icon, title, copy }) => <div className="flow-step" key={title}><span className="flow-icon"><Icon size={19}/></span><div><strong>{title}</strong><p>{copy}</p></div></div>)}
      </section>
    </main>
    <footer><ShieldCheck size={15}/> BrandGuard AI <span>Round 2 · The Build</span></footer>
  </div>
}

export function App() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)
  const [current, setCurrent] = useState(route)
  const [collapsed, setCollapsed] = useState(false)
  const [mobile, setMobile] = useState(false)
  const [startupError, setStartupError] = useState('')
  const task = useTask()
  useEffect(() => {
    const sync = () => { setCurrent(route()); setMobile(false); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])
  useEffect(() => {
    void api<Session>('/session').then(setSession).catch(error => {
      setSession(null)
      if (!(error instanceof ApiError && error.status === 401)) setStartupError('The workspace could not be loaded. Check the connection and try again.')
    })
  }, [])
  function go(page: Page, id?: string) { location.hash = page + (id ? '/' + id : '') }
  function start() { void task.run(async () => {
    setSession(await api<Session>('/demo', 'POST'))
    go('overview')
  }) }
  function changeRole(role: Role) { void task.run(async () => setSession(await api<Session>('/demo/role', 'PUT', { role }))) }
  if (session === undefined) return <Loading/>
  if (!session) return <Welcome start={start} busy={task.pending} error={task.error || startupError}/>
  const open = (id: string) => go('review', id)
  const activePage = pages.find(([page]) => page === current.page)?.[1]
  return <div className={'shell' + (collapsed ? ' collapsed' : '')}>
    <a className="skip" href="#main-content" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus() }}>Skip to content</a>
    {mobile && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobile(false)}/>}
    <aside className={'sidebar' + (mobile ? ' mobile-open' : '')}>
      <div className="side-top"><Logo/><button className="icon-button close-mobile" aria-label="Close navigation" onClick={() => setMobile(false)}><X size={20}/></button></div>
      <div className="workspace"><span className="workspace-avatar">{session.profile.name.slice(0, 1)}</span><div><strong>{session.profile.name}</strong><small>Sample workspace</small></div></div>
      <nav aria-label="Workspace navigation">
        <div className="nav-caption">WORKSPACE</div>
        {pages.map(([key, title, Icon]) => <a key={key} href={'#' + key} title={title} aria-current={current.page === key ? 'page' : undefined}><Icon size={19}/><span>{title}</span></a>)}
      </nav>
      <div className="side-bottom"><span className="side-status"><span className="dot"/><span>Demo workspace</span></span>
        <button className="icon-button collapse" aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'} onClick={() => setCollapsed(!collapsed)}><PanelLeftClose size={18}/></button>
      </div>
    </aside>
    <div className="main-area">
      <header className="topbar">
        <div className="breadcrumb"><button className="icon-button mobile-toggle" aria-label="Open navigation" aria-expanded={mobile} onClick={() => setMobile(!mobile)}><Menu size={21}/></button><span className="crumb-brand">{session.profile.name}</span><span className="crumb-slash">/</span><strong>{activePage}</strong></div>
        <div className="identity"><span className="person-avatar">{session.actor.split(' ').map(word => word[0]).join('')}</span><div><strong>{session.actor}</strong><label htmlFor="demo-role">Demo role</label></div>
          <select id="demo-role" aria-label="Demo role" value={session.role} disabled={task.pending} onChange={event => changeRole(event.target.value as Role)}>
            <option value="creator">Creator</option><option value="reviewer">Reviewer</option><option value="admin">Admin</option>
          </select>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        {task.error && <Notice>{task.error}</Notice>}
        {(current.page === 'overview' || current.page === 'analytics') && <Dashboard key={current.page} analytics={current.page === 'analytics'} open={open} create={() => go('review')} knowledge={() => go('knowledge')} queue={() => go('queue')} history={() => go('history')} session={session}/>}
        {current.page === 'review' && <ReviewPage key={current.id || 'new'} id={current.id} session={session} open={open} queue={() => go('queue')}/>}
        {current.page === 'knowledge' && <KnowledgePage session={session}/>}
        {(current.page === 'queue' || current.page === 'history') && <SubmissionList key={current.page} queue={current.page === 'queue'} open={open} create={() => go('review')}/>}
        {current.page === 'settings' && <SettingsPage session={session} update={setSession}/>}
      </main>
      <div className="app-footer"><span>BrandGuard AI · CoderX</span><Badge value="Sample workspace"/></div>
    </div>
  </div>
}
