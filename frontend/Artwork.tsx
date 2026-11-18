import { useState } from 'react'
import { FileImage } from 'lucide-react'
import { api, useData, useTask, type Artwork, type Finding, type RuleSnapshot, type Session } from './api'
import { Loading, Notice } from './ui'

export async function uploadImage(file: File, endpoint: string) {
  if (file.size > 5 * 1024 * 1024) throw new Error('The image exceeds the 5 MB limit.')
  const form = new FormData()
  form.append('file', file)
  return api<Artwork>(endpoint, 'POST', form)
}

export function ImagePicker({ title, busy, select }: { title: string; busy: boolean; select: (file: File) => void }) {
  return <label className="file-button"><FileImage size={16}/>{title}
    <input type="file" accept="image/png,image/jpeg" aria-label={title} disabled={busy} onChange={event => {
      const file = event.target.files?.[0]
      if (file) select(file)
      event.target.value = ''
    }}/>
  </label>
}

export function ArtworkPicker({ image, busy, select, remove }: {
  image: Artwork | null; busy: boolean; select: (file: File) => void; remove: () => void
}) {
  return <div className="art-picker">
    <div><strong>Marketing artwork</strong><small>PNG or JPG · up to 5 MB</small></div>
    {image && <div className="art-thumb"><img src={'/api/assets/' + image.id} alt="Attached artwork"/><span>{image.name}</span></div>}
    <div className="button-row"><ImagePicker title={image ? 'Replace artwork' : 'Attach artwork'} busy={busy} select={select}/>
      {image && <button className="text-button" type="button" disabled={busy} onClick={remove}>Remove artwork</button>}</div>
  </div>
}

export function ArtworkEvidence({ image, findings, policy }: { image: Artwork; findings: Finding[]; policy?: RuleSnapshot[] }) {
  const [selected, setSelected] = useState('')
  const marked = findings.filter(item => item.regions?.length)
  return <section className="art-evidence"><h3>Reviewed artwork</h3>
    <small>{image.name} · {image.width} × {image.height}</small>
    <div className="art-canvas"><img src={'/api/assets/' + image.id} alt={image.name}/>
      {marked.map((item, index) => (!selected || selected === item.id) && item.regions!.map(([x,y,r,b], i) =>
        <span aria-hidden="true" className={'art-box ' + (item.evidence_status === 'SUPPORTED' ? 'match' : '')}
          style={{left: x*100+'%', top: y*100+'%', width: (r-x)*100+'%', height: (b-y)*100+'%'}}
          key={item.id+i}>{i === 0 && <b>{index+1}</b>}</span>))}
    </div>
    {!!marked.length && <label>Highlighted region<select value={selected} onChange={e => setSelected(e.target.value)}>
      <option value="">All regions</option>{marked.map((item, i) => <option value={item.id} key={item.id}>{i+1}. {item.original_text || item.category}</option>)}
    </select></label>}
    {selected && <p>{marked.find(item => item.id === selected)?.explanation}</p>}
    <details className="source"><summary>Text recognised in artwork</summary><p className="saved-copy">{image.text || 'No readable text detected.'}</p></details>
    {policy && <details className="source"><summary>Approved visual references used</summary>
      {policy.filter(check => check.colors || check.references).map(check =>
        <div key={check.id}><strong>{check.title} · v{check.version}</strong>
          {check.colors && <div className="chips">{check.colors.map((value, i) =>
            <span key={i}><i className="colour-swatch" style={{backgroundColor:value}}/>{value}</span>)}</div>}
          {check.references && <ul className="logo-list">{check.references.map(ref =>
            <li key={ref.id}><img src={'/api/assets/'+ref.id} alt=""/>{ref.name}</li>)}</ul>}
        </div>)}
    </details>}
  </section>
}

export function AssetSettings({ session }: { session: Session }) {
  const logos = useData<Artwork[]>('/logos')
  const task = useTask()
  return <section className="panel form-card settings-card"><h2>Approved logos</h2>
    <p className="muted">Artwork reviews look for one of these logo variants and compare colours with the brand profile.</p>
    {logos.error && <Notice>{logos.error}</Notice>}{task.error && <Notice>{task.error}</Notice>}
    {!logos.data ? <Loading/> : !logos.data.length ? <p>No approved logos yet.</p> : <ul className="logo-list">{logos.data.map(item =>
      <li key={item.id}><img src={'/api/assets/'+item.id} alt=""/><span>{item.name}</span>
        {session.role === 'admin' && <button className="text-button" disabled={task.pending} onClick={() => void task.run(async () => {
          await api('/logos/'+item.id, 'DELETE'); logos.refresh()
        })}>Retire logo</button>}</li>)}</ul>}
    {session.role === 'admin' && <ImagePicker title="Add approved logo" busy={task.pending} select={file => void task.run(async () => {
      await uploadImage(file, '/logos'); logos.refresh()
    })}/>}
  </section>
}

export function WordPressSettings() {
  const connection = useData<{connected: boolean}>('/integrations/wordpress')
  const task = useTask()
  const [key, setKey] = useState('')
  return <section className="panel form-card settings-card"><h2>WordPress connection</h2>
    <p>Install the plugin on one WordPress site and add these constants to its wp-config.php file. The connection key is shown once.</p>
    {connection.error && <Notice>{connection.error}</Notice>}{task.error && <Notice>{task.error}</Notice>}
    <pre className="config-code">{`define( 'BRANDGUARD_URL', '${location.origin}' );\ndefine( 'BRANDGUARD_KEY', '${key || 'YOUR_CONNECTION_KEY'}' );`}</pre>
    <div className="button-row">
      <a className="button secondary" href="/api/integrations/wordpress/plugin.zip" download>Download plugin</a>
      {connection.data && (connection.data.connected
        ? <button className="button secondary" disabled={task.pending} onClick={() => void task.run(async () => {
          await api('/integrations/wordpress', 'DELETE'); setKey(''); connection.refresh()
        })}>Revoke connection key</button>
        : <button className="button primary" disabled={task.pending} onClick={() => void task.run(async () => {
          const result = await api<{key: string}>('/integrations/wordpress', 'POST'); setKey(result.key); connection.refresh()
        })}>Create connection key</button>)}
    </div>
  </section>
}
