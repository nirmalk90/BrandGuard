import { ArrowRight, BookOpen, CheckCircle2, ClipboardList, Clock3, FileText, Flag, Plus, XCircle } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { dateLabel, label, useData, type Metrics, type Session, type Summary } from './api'
import shieldArt from './dashboard-shield.webp'
import { Badge, Empty, GoButton, Loading, Notice, PageTitle, statusTone } from './ui'

const ReviewTrend = lazy(() => import('./ReviewTrend'))

function Table({ entries, open, title }: { entries: Summary[]; open: (id: string) => void; title: string }) {
  return <div className="table-scroll" tabIndex={0} role="region" aria-label={title}>
    <table>
      <thead><tr><th scope="col">Content</th><th scope="col">Status</th><th scope="col">Revision</th><th scope="col">Updated</th></tr></thead>
      <tbody>{entries.map(item => <tr key={item.id}>
        <td><div className="table-content">
          <span className="icon-tile" aria-hidden="true"><FileText size={17}/></span>
          <div><button className="text-button" onClick={() => open(item.id)}>{item.title}</button><small>{item.content_type} · {item.platform}</small></div>
        </div></td>
        <td><Badge value={item.status}/></td><td>v{item.revision}</td><td>{dateLabel(item.updated_at)}</td>
      </tr>)}</tbody>
    </table>
  </div>
}

export function SubmissionList({ queue, open, create }: { queue: boolean; open: (id: string) => void; create: () => void }) {
  const { data, error } = useData<Summary[]>(queue ? '/submissions?status=PENDING_APPROVAL' : '/submissions')
  const title = queue ? 'Approval Queue' : 'Review History'
  return <>
    <PageTitle title={title}
      description={queue ? 'Open a submission to review its findings and record a decision.' : 'Open any submission to see saved versions, findings, and decisions.'}/>
    {error ? <Notice>{error}</Notice> : !data ? <Loading/> : <section className="panel">
      {data.length ? <Table entries={data} open={open} title={title}/> : <Empty title={queue ? 'No submissions awaiting approval' : 'No reviews yet'} action={<GoButton onClick={create}>Open Content Review</GoButton>}>
        {queue ? 'Submissions appear here after a creator requests approval.' : 'Analyze your first draft to start building the review history.'}
      </Empty>}
    </section>}
  </>
}

function MetricCards({ stats }: { stats: Metrics }) {
  const metrics = [
    ['Total submissions', stats.total, ClipboardList, 'accent'],
    ['Pending approval', stats.statuses.PENDING_APPROVAL ?? 0, Clock3, 'warning'],
    ['Approved', stats.statuses.APPROVED ?? 0, CheckCircle2, 'positive'],
    ['Rejected', stats.statuses.REJECTED ?? 0, XCircle, 'critical'],
    ['Issues detected', stats.violations, Flag, 'violet'],
  ] as const
  return <ul className="metric-grid" role="list">{metrics.map(([name, value, Icon, tone]) =>
    <li className="panel glass metric" key={name}>
      <span className={'icon-tile tone-' + tone} aria-hidden="true"><Icon size={18}/></span>
      <strong>{value}</strong><span className="metric-label">{name}</span>
    </li>
  )}</ul>
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(values))
  return <section className="panel chart"><h2>{title}</h2>{Object.entries(values).length ? <ul className="distribution">
    {Object.entries(values).map(([name, value]) => <li key={name}><div><span>{label(name)}</span><strong>{value}</strong></div><progress className={'tone-' + statusTone(name)} max={max} value={value} aria-label={label(name)}/></li>)}
  </ul> : <p className="muted">No data yet.</p>}</section>
}

export function Dashboard({ analytics, session, open, create, knowledge, queue, history }: {
  analytics: boolean; session: Session; open: (id: string) => void; create: () => void;
  knowledge: () => void; queue: () => void; history: () => void;
}) {
  const { data: stats, error } = useData<Metrics>('/analytics')
  const recent = useData<Summary[]>('/submissions')
  return <>
    <PageTitle title={analytics ? 'Analytics' : 'Workspace overview'}
      description={analytics ? 'Monitor review activity and recurring issues across saved versions.' : 'Track submissions, findings, and approval decisions for ' + session.profile.name + '.'}/>
    {!analytics && <section className="panel glass dashboard-hero" aria-labelledby="dashboard-hero-title">
      <div className="hero-copy">
        <h2 id="dashboard-hero-title">Stay on-brand,<br/>from draft to approval.</h2>
        <p>{session.role === 'creator'
          ? 'Check a draft against approved brand rules, see the evidence behind each finding, and send your revision for sign-off.'
          : 'Open the approval queue to see which drafts are awaiting a decision and read the evidence behind each review.'}</p>
        <div className="button-row">
          {session.role === 'creator'
            ? <button className="button primary" onClick={create}><Plus size={18}/> New content review</button>
            : <GoButton onClick={queue}>Open approval queue</GoButton>}
          <button className="button secondary" onClick={knowledge}><BookOpen size={16}/> Explore brand knowledge</button>
        </div>
      </div>
      <img className="hero-art" src={shieldArt} alt="" width="960" height="540"/>
    </section>}
    {error ? <Notice>{error}</Notice> : stats ? <MetricCards stats={stats}/> : <Loading/>}
    {!analytics && <section className="panel" aria-labelledby="recent-reviews"><div className="section-head"><h2 id="recent-reviews">Recent reviews</h2><button className="button secondary small" onClick={history}>View history <ArrowRight size={15}/></button></div>
      {recent.error ? <Notice>{recent.error}</Notice> : !recent.data ? <Loading/> : recent.data.length ? <Table entries={recent.data.slice(0, 5)} open={open} title="Recent reviews"/> : <Empty title="No content reviewed yet">Start a review to see submissions and decisions here.</Empty>}
    </section>}
    {analytics && stats && <div className="analytics-grid">
      <Distribution title="Issues by category" values={stats.categories}/>
      <Distribution title="Submission statuses" values={stats.statuses}/>
      <Distribution title="Issues by severity" values={stats.severity}/>
      <Distribution title="Most frequently flagged rules" values={stats.rules}/>
      <section className="panel chart trend"><h2>Review activity</h2>
        {Object.keys(stats.trends).length ? <Suspense fallback={<Loading>Loading chart…</Loading>}><ReviewTrend trends={stats.trends}/></Suspense> : <p className='muted'>Review activity appears after the first analysis.</p>}
      </section>
    </div>}
  </>
}
