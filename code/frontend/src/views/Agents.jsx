import { useState } from 'react'
import { api } from '../api'
import { Err, Head, RawJson, Spinner } from '../components'

export default function Agents({ agents, reload }) {
  const [detail, setDetail] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)
  const [deployed, setDeployed] = useState(null)

  async function open(name) {
    setBusy(name); setError(null); setDeployed(null)
    try { setDetail(await api.agent(name)) } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  async function deploy(name) {
    setBusy(name); setError(null)
    try { setDeployed(await api.deployAgent(name)) } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  return (
    <>
      <Head title="Agents">
        Each agent is a JSON file in <code>app/agents/personas/</code>. Edit one, save, and the
        next answer changes — no restart, no redeploy. Behaviour is data, not code.
      </Head>

      <div className="card">
        <div className="row" style={{ marginBottom: '.6rem' }}>
          <h3 style={{ margin: 0 }}>{agents.length} personas</h3>
          <button className="btn btn-outline btn-sm shrink" onClick={reload}>reload from disk</button>
        </div>
        <table>
          <thead>
            <tr><th>name</th><th>description</th><th style={{ width: '5rem' }}>temp</th><th style={{ width: '13rem' }}></th></tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.name}>
                <td><strong>{a.display_name}</strong><div className="faint mono">{a.name}</div></td>
                <td>{a.description}
                  {a.style_rules?.length > 0 && (
                    <ul style={{ margin: '.4rem 0 0', paddingLeft: '1.1rem' }} className="faint">
                      {a.style_rules.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  )}
                </td>
                <td className="mono">{a.temperature ?? '—'}</td>
                <td>
                  <button className="btn btn-outline btn-sm" onClick={() => open(a.name)} disabled={!!busy}>system prompt</button>{' '}
                  <button className="btn btn-outline btn-sm" onClick={() => deploy(a.name)} disabled={!!busy}>deploy to Foundry</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {busy && <div style={{ marginTop: '.7rem' }}><Spinner label={busy} /></div>}
        <Err error={error} />
      </div>

      {deployed && (
        <div className="card">
          <h3>Published to Foundry Agent Service</h3>
          <p className="muted" style={{ marginTop: 0 }}>{deployed.action} · agent id <code>{deployed.agent_id}</code></p>
          <pre className="out">{deployed.next_step}</pre>
        </div>
      )}

      {detail && (
        <div className="card">
          <h3>{detail.display_name} — the prompt this JSON produces</h3>
          <p className="faint" style={{ marginTop: 0 }}>{detail.file}</p>
          <label style={{ marginTop: '.6rem' }}>grounded (retrieval supplied context)</label>
          <pre className="out">{detail.system_prompt_grounded}</pre>
          <label style={{ marginTop: '.8rem' }}>plain (no retrieval)</label>
          <pre className="out">{detail.system_prompt_plain}</pre>
          <RawJson data={detail} label="persona JSON" />
        </div>
      )}
    </>
  )
}
