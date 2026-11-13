import { useState } from 'react'
import { BookOpen, FileText, Plus } from 'lucide-react'
import { api, dateLabel, label, readFile, useData, useTask, type Knowledge, type Profile, type Rule, type RuleSpec, type Session, type Severity, type Source } from './api'
import { Badge, Loading, Notice, PageTitle } from './ui'

const categories = ['Terminology', 'Promotional claim', 'Approved fact', 'Tone', 'Clarity']
const kinds: Record<RuleSpec['kind'], string> = {
  phrase: 'Prohibited phrase', required: 'Required terminology', price_floor: 'Monthly price floor (INR)', approved_fact: 'Approved fact',
}

function RuleForm({ rule, sources, done }: { rule?: Rule; sources: Source[]; done: () => void }) {
  const [spec, setSpec] = useState<RuleSpec>(rule?.spec ?? {
    title: '', category: 'Terminology', kind: 'phrase', description: '', severity: 'medium',
    pattern: '', replacement: '', source_id: sources[0]?.id || '', value: null, valid_from: null, valid_until: null, active: true,
  })
  const task = useTask()
  const field = <K extends keyof RuleSpec>(key: K, value: RuleSpec[K]) => setSpec({ ...spec, [key]: value })
  return <form className="panel form-card" onSubmit={event => { event.preventDefault(); void task.run(async () => {
    await api(rule ? '/rules/' + rule.id : '/rules', rule ? 'PUT' : 'POST', spec); done()
  }) }}>
    <h2>{rule ? 'Edit rule' : 'New brand rule'}</h2>
    {task.error && <Notice>{task.error}</Notice>}
    <fieldset disabled={task.pending} className="field-group">
      <label>Rule title<input required maxLength={160} value={spec.title} onChange={event => field('title', event.target.value)}/></label>
      <div className="field-grid"><label>Category<select value={spec.category} onChange={event => field('category', event.target.value)}>{categories.map(value => <option key={value}>{value}</option>)}</select></label>
        <label>Check<select value={spec.kind} onChange={event => field('kind', event.target.value as RuleSpec['kind'])}>{Object.entries(kinds).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label></div>
      <label>Description<textarea required maxLength={1200} rows={3} value={spec.description} onChange={event => field('description', event.target.value)}/></label>
      {spec.kind !== 'approved_fact' && <label>{spec.kind === 'price_floor' ? 'Scope terms' : 'Phrase to check'}<input required maxLength={160} placeholder="Separate alternatives with |" value={spec.pattern} onChange={event => field('pattern', event.target.value)}/></label>}
      {spec.kind === 'price_floor' && <label>Minimum price in INR<input required type="number" min={1} max={100000000} value={spec.value ?? ''} onChange={event => field('value', event.target.value ? Number(event.target.value) : null)}/></label>}
      <label>Suggested replacement<input maxLength={300} value={spec.replacement} onChange={event => field('replacement', event.target.value)}/></label>
      <div className="field-grid"><label>Severity<select value={spec.severity} onChange={event => field('severity', event.target.value as Severity)}>{['critical','high','medium','low'].map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label>
        <label>Approved source<select required value={spec.source_id} onChange={event => field('source_id', event.target.value)}>{sources.map(source => <option value={source.id} key={source.id}>{source.title}</option>)}</select></label></div>
      <div className="field-grid"><label>Valid from<input type="date" value={spec.valid_from ?? ''} onChange={event => field('valid_from', event.target.value || null)}/></label>
        <label>Valid through<input type="date" value={spec.valid_until ?? ''} onChange={event => field('valid_until', event.target.value || null)}/></label></div>
      <label className="check"><input type="checkbox" checked={spec.active} onChange={event => field('active', event.target.checked)}/> Active rule</label>
      <div className="button-row"><button className="button primary">Save rule</button><button type="button" className="button secondary" onClick={done}>Cancel</button></div>
    </fieldset>
  </form>
}

function SourceForm({ done }: { done: () => void }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const task = useTask()
  return <form className="panel form-card" onSubmit={event => { event.preventDefault(); void task.run(async () => {
    await api('/sources', 'POST', { title, content }); done()
  }) }}>
    <h2>Add approved source</h2>{task.error && <Notice>{task.error}</Notice>}
    <fieldset disabled={task.pending} className="field-group">
      <label className="file-button">Import TXT, PDF or DOCX<input aria-label="Import source file" type="file" accept=".txt,.pdf,.docx" onChange={event => {
        const file = event.target.files?.[0]
        if (file) void task.run(async () => { const doc = await readFile(file); setTitle(doc.title); setContent(doc.content) })
        event.target.value = ''
      }}/></label>
      <label>Source title<input required maxLength={160} value={title} onChange={event => setTitle(event.target.value)}/></label>
      <label>Source text<textarea required maxLength={20000} rows={8} value={content} onChange={event => setContent(event.target.value)}/></label>
      <div className="button-row"><button className="button primary">Save source</button><button type="button" className="button secondary" onClick={done}>Cancel</button></div>
    </fieldset>
  </form>
}

export function KnowledgePage({ session }: { session: Session }) {
  const { data, error, refresh } = useData<Knowledge>('/knowledge')
  const [editor, setEditor] = useState<Rule | 'new' | 'source' | null>(null)
  const admin = session.role === 'admin'
  function done() { setEditor(null); refresh() }
  return <>
    <PageTitle title="Brand Knowledge" description="Maintain the rules, facts, and source documents behind every review."
      action={admin && <div className="button-row"><button className="button secondary" onClick={() => setEditor('source')}><Plus size={16}/> Add source</button>
      <button className="button primary" onClick={() => setEditor('new')}><Plus size={16}/> Add rule</button></div>}/>
    <section className="panel profile-banner"><span className="icon-tile"><BookOpen size={24}/></span><div><h2>{session.profile.name}</h2><p>{session.profile.industry} · {session.profile.description}</p><p><strong>Brand voice</strong> · {session.profile.tone}</p></div></section>
    {error ? <Notice>{error}</Notice> : !data ? <Loading/> : <>
      {admin && editor === 'source' && <SourceForm done={done}/>}
      {admin && editor && editor !== 'source' && <RuleForm key={editor === 'new' ? 'new' : editor.id} sources={data.sources} rule={editor === 'new' ? undefined : editor} done={done}/>}
      <section className="panel form-card">
        <div className="section-head"><div><h2>Brand rules and approved facts</h2><p>{data.rules.filter(rule => rule.active).length} enabled · Review checks respect validity dates.</p></div></div>
        <div className="rule-list">{data.rules.map(rule => <article className="rule-card" key={rule.id}>
          <div className="issue-head"><h3>{rule.spec.title}</h3><div className="chips"><Badge value={rule.spec.severity}/><Badge value={rule.active ? 'Active' : 'Inactive'}/></div></div>
          <p>{rule.spec.description}</p>
          {rule.spec.pattern && <p className="muted">{kinds[rule.spec.kind]} · {rule.spec.pattern.replaceAll('|', ' / ')}{rule.spec.replacement && ' → ' + rule.spec.replacement}</p>}
          {(rule.spec.valid_from || rule.spec.valid_until) && <p className="muted">Validity · {rule.spec.valid_from || 'Open start'} through {rule.spec.valid_until || 'Open end'}</p>}
          <small>{rule.source_title} · Rule v{rule.version} · Updated {dateLabel(rule.updated_at)}</small>
          <details><summary>Rule ID</summary><small>{rule.id}</small></details>
          {admin && <button className="text-button" onClick={() => { setEditor(rule); window.scrollTo(0, 0) }}>Edit rule</button>}
        </article>)}</div>
      </section>
      <section className="panel form-card"><h2>Approved sources</h2>{data.sources.map(source => <details className="source" key={source.id}>
        <summary><FileText size={16}/> {source.title} · v{source.version}</summary><p>{source.content}</p><small>Source ID · {source.id}</small>
      </details>)}</section>
    </>}
  </>
}

const profileLabels: Record<keyof Profile, string> = {
  name: 'Brand name', description: 'Brand description', industry: 'Industry', audience: 'Target audience',
  personality: 'Brand personality', style: 'Communication style', tone: 'Preferred tone',
  primary_color: 'Primary brand color', secondary_color: 'Secondary brand color',
}
export function SettingsPage({ session, update }: { session: Session; update: (session: Session) => void }) {
  const [profile, setProfile] = useState(session.profile)
  const task = useTask()
  return <>
    <PageTitle title="Settings" description="Manage your sample brand profile and review preferences."/>
    <form className="panel form-card settings-card" onSubmit={event => { event.preventDefault(); void task.run(async () => {
      update(await api<Session>('/brand', 'PUT', profile)); task.setMessage('Brand profile saved.')
    }) }}>
      <h2>Brand profile</h2>
      {session.role !== 'admin' && <p className="muted">Switch to Admin in the demo role menu to edit the profile.</p>}
      {task.error && <Notice>{task.error}</Notice>}{task.message && <p className="success" role="status">{task.message}</p>}
      <fieldset className="field-grid" disabled={session.role !== 'admin' || task.pending}>
        {(Object.keys(profileLabels) as (keyof Profile)[]).map(key => <label key={key}>{profileLabels[key]}<input
          type={key.endsWith('_color') ? 'color' : 'text'} required={key === 'name'} value={profile[key]} onChange={event => setProfile({ ...profile, [key]: event.target.value })}/></label>)}
        {session.role === 'admin' && <div><button className="button primary">Save brand profile</button></div>}
      </fieldset>
    </form>
    <section className="panel form-card settings-card"><h2>Analysis mode</h2><Badge value={session.ai_available ? 'Optional AI assistance' : 'Rule-based'} />
      <p className="muted">{session.ai_available ? 'External AI assistance requires opt-in on each review.' : 'Drafts are checked using rules and approved facts stored in this workspace.'}</p></section>
  </>
}
