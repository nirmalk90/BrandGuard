import { useEffect, useState } from 'react'
import { ArrowRight, CheckCircle2, Copy, FileUp, RotateCcw, Send, Sparkles } from 'lucide-react'
import { api, dateLabel, readFile, useData, useTask, type Artwork, type Finding, type Session, type Submission } from './api'
import { ArtworkEvidence, ArtworkPicker, uploadImage } from './Artwork'
import { CampaignField } from './Governance'
import { Badge, Empty, Loading, Notice, PageTitle } from './ui'

const types = ['Instagram caption', 'Social media post', 'Advertisement', 'Marketing email', 'Product description', 'Website copy', 'Business announcement']
const platforms = ['Instagram', 'LinkedIn', 'Email', 'Website', 'Paid media', 'Other']

function FileInput({ disabled, select }: { disabled: boolean; select: (file: File) => void }) {
  return <label className="file-button"><FileUp size={16}/> Import TXT, PDF or DOCX
    <input aria-label="Import draft file" type="file" accept=".txt,.pdf,.docx" disabled={disabled} onChange={event => {
      const file = event.target.files?.[0]
      if (file) select(file)
      event.target.value = ''
    }}/>
  </label>
}

function OptIn({ session, value, onChange }: { session: Session; value: boolean; onChange: (value: boolean) => void }) {
  return session.ai_available ? <label className="check"><input type="checkbox" checked={value} onChange={event => onChange(event.target.checked)}/>
    Include AI assistance. This sends the draft and relevant policy excerpts to the configured external model provider.
  </label> : <span className="mode"><span className="dot"/> Rule-based analysis</span>
}

function NewReview({ session, open }: { session: Session; open: (id: string) => void }) {
  const [title, setTitle] = useState(session.demo ? 'NovaTech launch copy' : '')
  const [contentType, setContentType] = useState(types[2])
  const [platform, setPlatform] = useState(platforms[4])
  const [content, setContent] = useState(session.demo ? session.sample : '')
  const [image, setImage] = useState<Artwork | null>(null)
  const [campaign, setCampaign] = useState('')
  const [ai, setAi] = useState(false)
  const task = useTask()
  return <>
    <PageTitle title="Content Review" description="Review marketing copy and artwork against your approved brand guidelines."/>
    {session.role !== 'creator' ? <div className="panel"><Empty title="Creator access required">{session.demo ? 'Select Creator in the demo role menu to start a content review.' : 'A workspace creator can start a review.'}</Empty></div> :
      <div className="review-layout new-layout">
        <form className="panel form-card" onSubmit={event => {
          event.preventDefault()
          if (!content.trim() && !image) { void task.run(async () => { throw new Error('Enter or import content, or attach artwork to analyze.') }); return }
          const draftOnly = (event.nativeEvent as SubmitEvent).submitter?.getAttribute('value') === 'draft'
          void task.run(async () => {
            const submission = await api<Submission>(draftOnly ? '/submissions/draft' : '/submissions', 'POST',
              { title, content_type: contentType, platform, content, artwork_id: image?.id, campaign: campaign.trim() || 'Unassigned', use_ai: !draftOnly && ai })
            open(submission.id)
          })
        }}>
          <div className="section-head"><div><h2>Submission details</h2><p>{session.profile.name} · {session.actor}</p></div></div>
          {task.error && <Notice>{task.error}</Notice>}
          <fieldset disabled={task.pending} className="field-group">
            <label>Content title<input required maxLength={160} value={title} onChange={event => setTitle(event.target.value)}/></label>
            <CampaignField value={campaign} change={setCampaign}/>
            <div className="field-grid">
              <label>Content type<select value={contentType} onChange={event => setContentType(event.target.value)}>{types.map(value => <option key={value}>{value}</option>)}</select></label>
              <label>Target platform<select value={platform} onChange={event => setPlatform(event.target.value)}>{platforms.map(value => <option key={value}>{value}</option>)}</select></label>
            </div>
            <ArtworkPicker image={image} busy={task.pending} select={file => void task.run(async () => setImage(await uploadImage(file, '/artwork')))} remove={() => setImage(null)}/>
            <label>Original content<textarea maxLength={20000} rows={9} value={content} onChange={event => setContent(event.target.value)}/></label>
            <div className="editor-meta"><FileInput disabled={task.pending} select={file => void task.run(async () => {
              const doc = await readFile(file); setContent(doc.content); setTitle(doc.title)
            })}/><span>{content.length.toLocaleString()} / 20,000 characters</span></div>
            <OptIn session={session} value={ai} onChange={setAi}/>
            <div className="button-row"><button className="button primary" type="submit"><Sparkles size={17}/>{task.pending ? 'Working…' : 'Analyze Content'}</button>
              <button className="button secondary" type="submit" value="draft">Save draft</button>
              {session.demo && <button className="button secondary" type="button" onClick={() => setContent(session.sample)}><RotateCcw size={15}/> Restore sample</button>}</div>
          </fieldset>
        </form>
        <aside className="panel glass review-guide"><span className="icon-tile"><Sparkles size={21}/></span><h2>What the review checks</h2>
          <ul><li>Restricted and preferred terminology in copy and artwork</li><li>Promotional claims and approved facts</li><li>Logo variants and brand colours</li></ul>
          <a className="text-button" href="#knowledge">See brand knowledge <ArrowRight size={15}/></a>
        </aside>
      </div>}
  </>
}



function Issue({ finding, editable, busy, apply, update }: {
  finding: Finding; editable: boolean; busy: boolean; apply: () => void;
  update: (status: string, reason: string) => void;
}) {
  const [reason, setReason] = useState('')
  const [copy, setCopy] = useState('')
  return <article className={'issue ' + finding.severity}>
    <div className="issue-head"><h3>{finding.category}</h3><Badge value={finding.severity}/></div>
    <div className="chips"><Badge value={finding.evidence_status}/><Badge value={finding.status}/>
      {finding.origin === 'artwork' && <Badge value="Artwork"/>}{finding.conflict && <Badge value="Conflicting rules"/>}
      {finding.requires_human_review && <Badge value="Human review recommended"/>}</div>
    {finding.original_text && <blockquote>“{finding.original_text}”</blockquote>}
    <p>{finding.explanation}</p>
    {!finding.rule_id && finding.rule_title && <small>{finding.rule_title} · v{finding.rule_version}</small>}
    {finding.rule_id && <details className="evidence"><summary>{finding.rule_title} · rule v{finding.rule_version}</summary>
      <p><strong>{finding.source_title}</strong> · source v{finding.source_version}</p><p>{finding.source_excerpt}</p>
      <small>Rule {finding.rule_id} · Source {finding.source_id}</small></details>}
    {finding.suggested_correction && <div className="suggestion"><small>Suggested correction</small><p>{finding.suggested_correction}</p>
      <div className="button-row"><button className="button secondary small" onClick={async () => {
        try { await navigator.clipboard.writeText(finding.suggested_correction); setCopy('Copied') }
        catch { setCopy('Clipboard unavailable. Select the correction text to copy it.') }
      }}><Copy size={14}/> Copy</button>{editable && finding.origin !== 'artwork' && <button className="button secondary small" disabled={busy} onClick={apply}>Apply to draft</button>}
      {copy && <span className="muted" role="status">{copy}</span>}</div></div>}
    {finding.reason && <p className="muted">Resolution note · {finding.reason}</p>}
    {editable && finding.evidence_status !== 'SUPPORTED' && <details className="resolution"><summary>Dismiss or contest</summary>
      <label>Reason<textarea rows={2} maxLength={1200} value={reason} onChange={event => setReason(event.target.value)}/></label>
      <div className="button-row">{(finding.status === 'OPEN' ? ['DISMISSED', 'CONTESTED'] : ['OPEN']).map(status =>
        <button key={status} disabled={busy || !reason.trim()} className="button secondary small" onClick={() => update(status, reason)}>
          {status === 'OPEN' ? 'Reopen' : status === 'DISMISSED' ? 'Dismiss' : 'Contest'}
        </button>)}</div>
    </details>}
  </article>
}

function SavedReview({ id, session, queue, revision, reviewId }: { id: string; session: Session; queue: () => void; revision?: string; reviewId?: string }) {
  const endpoint = '/submissions/' + id
  const { data, setData, error, refresh } = useData<Submission>(endpoint)
  const [draft, setDraft] = useState('')
  const [draftVersion, setDraftVersion] = useState('')
  const [selected, setSelected] = useState(revision || '')
  const [selectedReview, setSelectedReview] = useState(reviewId || '')
  const [image, setImage] = useState<Artwork | null>(null)
  const [newCampaign, setNewCampaign] = useState<string | null>(null)
  const [ai, setAi] = useState(false)
  const [comment, setComment] = useState('')
  const task = useTask()
  const current = data?.versions.at(-1)
  useEffect(() => {
    if (current && current.id !== draftVersion) { setDraft(current.content); setImage(current.artwork); setDraftVersion(current.id) }
  }, [current, draftVersion])
  if (error) return <Notice>{error}</Notice>
  if (!data || !current) return <Loading>Loading review…</Loading>
  const shown = data.versions.find(version => version.id === selected || String(version.number) === selected) || current
  const latestReview = shown.reviews.at(-1)
  const assessment = shown.reviews.find(item => item.id === selectedReview) || latestReview
  const findings = assessment?.findings || []
  const issues = findings.filter(finding => finding.evidence_status !== 'SUPPORTED')
  const isCurrent = shown.id === current.id && assessment?.id === latestReview?.id
  const creator = session.role === 'creator' && isCurrent && !data.wordpress
  const changed = draft.trim() !== current.content || image?.id !== current.artwork?.id
  const status = data.status
  const highlightApproval = status === 'REVIEWED' && !changed && !issues.some(item => item.status === 'OPEN')
  function update(path: string, method: string, body: object, success: string) {
    void task.run(async () => {
      const result = await api<Submission>(endpoint + path, method, { ...body, generation: data!.generation })
      setData(result)
      task.setMessage(success)
      if (path === '/reanalyze') { setSelected(''); setSelectedReview('') }
      if (path === '/decision') setComment('')
    })
  }
  return <>
    <PageTitle title={data.title} description={data.campaign + ' · ' + data.content_type + ' · ' + data.platform + ' · Created by ' + data.creator}
      action={<Badge value={status}/>}/>
    {task.error && <Notice>{task.error} <button className="text-button" onClick={refresh}>Reload saved review</button></Notice>}
    {task.message && <div className="success" role="status"><CheckCircle2 size={17}/>{task.message}</div>}
    <div className="panel glass review-summary">
      <div><strong>{issues.length}</strong><span>Issues found</span></div>
      <div className="risk-critical"><strong>{issues.filter(item => item.severity === 'critical').length}</strong><span>Critical</span></div>
      <div className="risk-critical"><strong>{issues.filter(item => item.severity === 'high').length}</strong><span>High risk</span></div>
      <div className="risk-warning"><strong>{issues.filter(item => ['medium','low'].includes(item.severity)).length}</strong><span>Medium / low</span></div>
      <div><strong>{assessment?.rules_checked ?? 0}</strong><span>Rules checked</span></div>
      <div><Badge value={assessment?.mode || 'Awaiting review'}/><span>{assessment ? 'Review complete' : 'Draft'}</span></div>
    </div>
    {assessment?.notice && <Notice>{assessment.notice}</Notice>}
    <div className="review-layout">
      <section className="panel form-card">
        <div className="section-head"><div><h2>Reviewed content</h2><p>{dateLabel(shown.created_at)}</p></div>
          <label>Version<select aria-label="Version" value={shown.id} onChange={event => { setSelected(event.target.value); setSelectedReview('') }}>
            {[...data.versions].reverse().map(version => <option value={version.id} key={version.id}>Version {version.number}{version.id === current.id ? ' (current)' : ''}</option>)}
          </select></label></div>
        {shown.content && <p className="saved-copy">{shown.content}</p>}
        {shown.artwork && <ArtworkEvidence key={assessment?.id || shown.id} image={shown.artwork} findings={findings} policy={assessment?.rules_snapshot}/>}
        {data.wordpress && <details className="source"><summary>Exact WordPress draft</summary><pre className="config-code">{JSON.stringify(data.wordpress, null, 2)}</pre></details>}
        {session.role !== 'reviewer' && <details className="source"><summary>Change campaign</summary>
          <CampaignField value={newCampaign ?? data.campaign} change={setNewCampaign}/>
          <button className="button secondary small" disabled={task.pending || !newCampaign?.trim() || newCampaign.trim() === data.campaign}
            onClick={() => update('/campaign', 'PUT', {campaign: newCampaign?.trim()}, 'Campaign updated.')}>Save campaign</button>
        </details>}
        {creator && <div className="revision-editor">
          <label>Editable draft<textarea rows={7} maxLength={20000} value={draft} disabled={task.pending} onChange={event => setDraft(event.target.value)}/></label>
          <ArtworkPicker image={image} busy={task.pending} select={file => void task.run(async () => setImage(await uploadImage(file, '/artwork')))} remove={() => setImage(null)}/>
          <div className="editor-meta"><FileInput disabled={task.pending} select={file => void task.run(async () => setDraft((await readFile(file)).content))}/><span>{draft.length.toLocaleString()} characters</span></div>
          <OptIn session={session} value={ai} onChange={setAi}/>
          <div className="button-row">
            <button className={'button ' + (highlightApproval || (status === 'PENDING_APPROVAL' && !changed) ? 'secondary' : 'primary')}
              disabled={task.pending || (!draft.trim() && !image) || (!changed && !['DRAFT', 'REVIEWED'].includes(status))} onClick={() => update('/reanalyze', 'POST', { content: draft, artwork_id: image?.id ?? null, use_ai: ai }, 'Analysis saved.')}>
              <Sparkles size={16}/> {task.pending ? 'Working…' : status === 'DRAFT' ? 'Analyze Content' : 'Re-run analysis'}
            </button>
            {status === 'REVIEWED' && <button className={'button ' + (highlightApproval ? 'primary' : 'secondary')} disabled={task.pending || changed} onClick={() => update('/submit-for-approval', 'POST', {}, 'Revision sent for approval.')}>
              <Send size={16}/> Submit for approval
            </button>}
            {status === 'PENDING_APPROVAL' && <button className={'button ' + (changed ? 'secondary' : 'primary')} onClick={queue}>Open approval queue <ArrowRight size={15}/></button>}
          </div>
          {changed && <small className="muted">Run analysis to save your changes as a new version before submitting.</small>}
        </div>}
        {isCurrent && status === 'PENDING_APPROVAL' && session.role === 'reviewer' && <form className="revision-editor" onSubmit={event => event.preventDefault()}>
          <h2>Record a decision</h2><label>Decision rationale<textarea required rows={3} maxLength={2000} value={comment} onChange={event => setComment(event.target.value)}/></label>
          <div className="button-row">{[['APPROVED', 'Approve'], ['CHANGES_REQUESTED', 'Request changes'], ['REJECTED', 'Reject']].map(([action, text]) =>
            <button type="button" key={action} className={'button ' + (action === 'APPROVED' ? 'primary' : 'secondary')}
              disabled={task.pending || !comment.trim()} onClick={() => update('/decision', 'POST', { action, comment }, 'Decision saved.')}>{text}</button>)}</div>
        </form>}
      </section>
      <section className="panel findings-panel">
        <div className="section-head"><div><h2>Findings &amp; evidence</h2><p>Version {shown.number}</p></div>
          {shown.reviews.length > 1 && <label>Assessment<select aria-label="Assessment" value={assessment?.id} onChange={event => setSelectedReview(event.target.value)}>
            {[...shown.reviews].reverse().map(item => <option key={item.id} value={item.id}>{dateLabel(item.created_at)} · {item.mode}</option>)}
          </select></label>}</div>
        {!assessment ? <Empty title="Awaiting analysis">Run analysis to check this version against brand rules.</Empty> :
          !findings.length && <Empty title="No issues detected">This assessment found no issues within the rules it checked.</Empty>}
        {findings.map(finding => <Issue key={finding.id} finding={finding} editable={creator && status === 'REVIEWED'} busy={task.pending}
          apply={() => {
            const index = finding.original_text ? draft.indexOf(finding.original_text) : -1
            if (index >= 0) setDraft(draft.slice(0, index) + finding.suggested_correction + draft.slice(index + finding.original_text.length))
            else if (!finding.original_text) setDraft(draft.trimEnd() + ' ' + finding.suggested_correction)
            else void task.run(async () => { throw new Error('That excerpt is no longer in the draft. Edit the draft or rerun the review.') })
          }} update={(next, reason) => update('/findings/' + finding.id, 'PUT', { status: next, reason }, 'Finding updated.')}/>)}
      </section>
    </div>
    <section className="panel audit"><h2>Decision and activity history</h2>
      {data.actions.length ? <ol>{[...data.actions].reverse().map(action => <li key={action.id}><div className="chips"><Badge value={action.action}/><strong>{action.actor}</strong><small>v{data.versions.find(version => version.id === action.version_id)?.number} · {dateLabel(action.created_at)}</small></div>{action.comment && <p>{action.comment}</p>}</li>)}</ol> : <p className="muted">Approval activity appears after a revision is sent for review.</p>}
    </section>
  </>
}

export function ReviewPage({ id, session, open, queue, revision, reviewId }: { id?: string; session: Session; open: (id: string) => void; queue: () => void; revision?: string; reviewId?: string }) {
  return id ? <SavedReview id={id} session={session} queue={queue} revision={revision} reviewId={reviewId}/> : <NewReview session={session} open={open}/>
}
