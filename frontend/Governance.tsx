import { useState } from 'react'
import { dateLabel, useData } from './api'
import { Empty, Loading, Notice, PageTitle } from './ui'

type ReviewLink = { review_id: string; submission_id: string; revision: number; title: string; flags: string[]; created_at: string }
type Pattern = { rule_id: string; version: number; title: string; assessed: number | null; flagged: number;
  conflicts: number; disputed: number; violations: number }

function ReviewLinks({ campaign, row, flag, offset, move }: {
  campaign: string; row: Pattern; flag: string; offset: number; move: (offset: number) => void
}) {
  const params = new URLSearchParams({campaign, rule_id:row.rule_id, version:String(row.version), flag, offset:String(offset)})
  const {data,error} = useData<{total: number; reviews: ReviewLink[]}>('/governance/evidence?' + params)
  if (error) return <Notice>{error}</Notice>
  if (!data) return <Loading>Loading assessments…</Loading>
  return <><ul className="review-links">{data.reviews.map(link => <li key={link.review_id}>
    <a href={['#review', link.submission_id, link.revision, link.review_id].join('/')}>{link.title} · v{link.revision}</a>
    <small>{dateLabel(link.created_at)} · {link.flags.join(' · ') || 'No issue'}</small></li>)}</ul>
    {data.total > 25 && <div className="button-row">
      <button className="button secondary small" disabled={!offset} onClick={() => move(offset-25)}>Previous</button>
      <span>{offset+1}–{Math.min(offset+25,data.total)} of {data.total}</span>
      <button className="button secondary small" disabled={offset+25 >= data.total} onClick={() => move(offset+25)}>Next</button></div>}</>
}

function Evidence({campaign, row, filter}: {campaign: string; row: Pattern; filter: string}) {
  const [open,setOpen] = useState(false)
  const [offset,move] = useState(0)
  const flag = filter === 'repeat' ? 'flagged' : filter
  return <details onToggle={e => setOpen(e.currentTarget.open)}><summary>{row.title}</summary>
    {open && <ReviewLinks key={offset} campaign={campaign} row={row} flag={flag} offset={offset} move={move}/>}</details>
}

function Results({ campaign }: { campaign: string }) {
  const { data, error } = useData<Pattern[]>('/governance?campaign=' + encodeURIComponent(campaign))
  const [filter, setFilter] = useState('all')
  if (error) return <Notice>{error}</Notice>
  if (!data) return <Loading/>
  const visible = data.filter(row => filter === 'all' || (filter === 'repeat' && row.flagged >= 2)
    || (filter === 'violation' && row.violations >= 2) || (filter === 'conflict' && row.conflicts >= 2))
  return <section className="panel">
    <div className="section-head"><div><h2>Rule performance</h2><p>Each draft revision counts once per rule version. The rate is the share of assessed revisions with an open or contested finding.</p></div>
      <label>Show<select value={filter} onChange={e => setFilter(e.target.value)}>
        <option value="all">All evaluated rules</option><option value="violation">Recurring violations</option><option value="repeat">Recurring findings</option><option value="conflict">Repeated conflicts</option>
      </select></label></div>
    {!visible.length ? <Empty title="No matching patterns">Recurring findings and repeated conflicts require at least two distinct draft revisions.</Empty> :
    <div className="table-scroll" role="region" aria-label="Campaign rule performance" tabIndex={0}><table className="governance-table">
      <thead><tr>{['Rule and evidence', 'Version', 'Violations', 'Flagged / assessed', 'Rate', 'Change¹', 'Conflicts', 'Disputed'].map(name => <th scope="col" key={name}>{name}</th>)}</tr></thead>
      <tbody>{visible.map(row => {
        const prior = data.filter(other => other.rule_id === row.rule_id && other.version < row.version).sort((a,b) => b.version-a.version)[0]
        const rate = row.assessed ? row.flagged / row.assessed : null
        const change = rate !== null && prior?.assessed ? Math.round((rate - prior.flagged/prior.assessed)*100) : null
        return <tr key={row.rule_id+row.version}><td><Evidence key={filter} campaign={campaign} row={row} filter={filter}/></td>
          <td>v{row.version}</td><td>{row.violations}</td><td>{row.flagged} / {row.assessed ?? 'unknown'}</td><td>{rate === null ? '—' : Math.round(rate*100)+'%'}</td>
          <td>{change === null ? '—' : (change > 0 ? '+' : '')+change+' pp'}</td><td>{row.conflicts}</td><td>{row.disputed}</td></tr>
      })}</tbody>
    </table></div>}
    <p className="muted">¹ Percentage-point change from the previous evaluated rule version in this campaign. Historical assessments without a rule inventory have an unknown denominator.</p>
    <p className="muted">Violations count revisions that contradict an approved rule, excluding dismissed findings. Conflicts count revisions where rules give incompatible guidance for the same wording. Disputes count revisions where a creator contested or dismissed a finding.</p>
  </section>
}

export function CampaignField({ value, change }: { value: string; change: (value: string) => void }) {
  const { data } = useData<string[]>('/campaigns')
  return <label>Campaign<input list="campaign-options" maxLength={100} value={value} placeholder="Unassigned" onChange={e => change(e.target.value)}/>
    <datalist id="campaign-options">{data?.map(c => <option value={c} key={c}/>)}</datalist></label>
}

export function Governance() {
  const { data, error } = useData<string[]>('/campaigns')
  const [selected, setSelected] = useState('')
  const campaign = selected || data?.[0]
  return <><PageTitle title="Campaign governance" description="Track recurring findings and compare the impact of guideline changes within a campaign."/>
    {error ? <Notice>{error}</Notice> : !data ? <Loading/> : !campaign ?
      <section className="panel"><Empty title="No campaigns yet">Assign a campaign when creating a review.</Empty></section> :
      <><section className="panel campaign-selector"><label>Campaign<select value={campaign} onChange={e => setSelected(e.target.value)}>
        {data.map(name => <option key={name}>{name}</option>)}</select></label></section><Results key={campaign} campaign={campaign}/></>}
  </>
}
