import { ArrowRight, BookOpen, CheckCircle2, ClipboardList, Clock3, Flag, Plus, ShieldCheck, XCircle } from 'lucide-react'
import { lazy, Suspense } from 'react'
import { dateLabel, label, useData, type Metrics, type Session, type Summary } from './api'
import { Badge, Empty, GoButton, Loading, Notice, PageTitle } from './ui'

const ReviewTrend = lazy(() => import('./ReviewTrend'))

function Table({ entries, open }: { entries: Summary[]; open: (id: string) => void }) {
  return <div className="table-scroll"><table><thead><tr><th scope="col">Content</th><th scope="col">Status</th><th scope="col">Revision</th><th scope="col">Updated</th></tr></thead>
    <tbody>{entries.map(item => <tr key={item.id}><td><button className="text-button" onClick={() => open(item.id)}>{item.title}</button><small>{item.content_type} · {item.platform}</small></td>
      <td><Badge value={item.status}/></td><td>v{item.revision}</td><td>{dateLabel(item.updated_at)}</td></tr>)}</tbody>
  </table></div>
}

export function SubmissionList({ queue, open, create }: { queue: boolean; open: (id: string) => void; create: () => void }) {
  const { data, error } = useData<Summary[]>(queue ? '/submissions?status=PENDING_APPROVAL' : '/submissions')
  return <>
    <PageTitle title={queue ? 'Approval Queue' : 'Review History'}
      description={queue ? 'Open a submission to review its findings and record a decision.' : 'Open any submission to see saved versions, findings, and decisions.'}/>
    {error ? <Notice>{error}</Notice> : !data ? <Loading/> : <section className="panel">
      {data.length ? <Table entries={data} open={open}/> : <Empty title={queue ? 'No submissions awaiting approval' : 'No reviews yet'} action={<GoButton onClick={create}>Open Content Review</GoButton>}>
        {queue ? 'Submissions appear here after a creator requests approval.' : 'Analyze your first draft to start building the review history.'}
      </Empty>}
    </section>}
  </>
}

function MetricCards({ stats }: { stats: Metrics }) {
  const metrics = [
    ['Total submissions', stats.total, ClipboardList, 'blue'],
    ['Pending approval', stats.statuses.PENDING_APPROVAL ?? 0, Clock3, 'amber'],
    ['Approved', stats.statuses.APPROVED ?? 0, CheckCircle2, 'teal'],
    ['Rejected', stats.statuses.REJECTED ?? 0, XCircle, 'red'],
    ['Issues detected', stats.violations, Flag, 'purple'],
  ] as const
  return <div className="metric-grid">{metrics.map(([name, value, Icon, tone]) =>
    <div className="panel metric" key={name}><span className={'icon-tile ' + tone}><Icon size={19}/></span><strong>{value}</strong><span>{name}</span></div>
  )}</div>
}

function Distribution({ title, values }: { title: string; values: Record<string, number> }) {
  const max = Math.max(1, ...Object.values(values))
  return <section className="panel chart"><h2>{title}</h2>{Object.entries(values).length ? <ul className="distribution">
    {Object.entries(values).map(([name, value]) => <li key={name}><div><span>{label(name)}</span><strong>{value}</strong></div><progress max={max} value={value} aria-label={label(name)}/></li>)}
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
      description={analytics ? 'Monitor review activity and recurring issues across saved versions.' : 'Review marketing content against your brand’s approved knowledge.'}
      action={!analytics && session.role === 'creator' && <button className="button primary" onClick={create}><Plus size={18}/> New content review</button>}/>
    {!analytics && <section className="panel dashboard-hero">
      <div><div className="workspace-tag"><span className="dot"/> {session.profile.name} sample environment</div>
      <h2>Stay on-brand, from draft to approval.</h2><p>Start with a NovaTech example, see which rules apply, and send your revised copy for sign-off.</p>
      <div className="button-row"><GoButton onClick={session.role === 'creator' ? create : queue}>{session.role === 'creator' ? 'Start a review' : 'Open approval queue'}</GoButton><button className="button secondary" onClick={knowledge}><BookOpen size={16}/> Explore brand knowledge</button></div></div>
      <div className="hero-art" aria-hidden="true"><ShieldCheck size={100} strokeWidth={1}/></div>
    </section>}
    {error ? <Notice>{error}</Notice> : stats ? <MetricCards stats={stats}/> : <Loading/>}
    {!analytics && <section className="panel"><div className="section-head"><div><h2>Recent reviews</h2><p>Latest submissions in this workspace.</p></div><button className="text-button" onClick={history}>View history <ArrowRight size={15}/></button></div>
      {recent.error ? <Notice>{recent.error}</Notice> : !recent.data ? <Loading/> : recent.data.length ? <Table entries={recent.data.slice(0, 5)} open={open}/> : <Empty title="No content reviewed yet">Start a review to see submissions and decisions here.</Empty>}
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
