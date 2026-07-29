import { useState } from 'react'
import { api } from '../api'
import { Err, Head, RawJson, RUNS_ON, RunsOnBadge, Spinner } from '../components'

export default function Agents({ agents, hostedOnly = [], foundry, reload, azure }) {
  const [detail, setDetail] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [confirming, setConfirming] = useState(null)

  const all = [...agents, ...hostedOnly]

  async function act(name, fn, done) {
    setBusy(name); setError(null); setNotice(null)
    try { const r = await fn(); if (done) setNotice(done(r)); reload() }
    catch (e) { setError(e.message) } finally { setBusy(''); setConfirming(null) }
  }

  async function showPrompt(name) {
    setBusy(name); setError(null)
    try { setDetail(await api.agent(name)) }
    catch (e) { setError(e.message) } finally { setBusy('') }
  }

  return (
    <>
      <Head title="Agents">
        Each agent is a JSON file in <code>app/agents/personas/</code> — edit one, save, and the
        next answer changes. The badge tells you <strong>where each one can run</strong>: on this
        machine, in Azure, or both.
      </Head>

      <div className="card">
        <div className="row" style={{ marginBottom: '.7rem' }}>
          <h3 style={{ margin: 0 }}>{all.length} agents</h3>
          <button className="btn btn-outline btn-sm shrink" onClick={reload}>refresh</button>
          {azure?.foundry_url && (
            <a className="btn btn-outline btn-sm shrink" href={azure.foundry_url} target="_blank" rel="noreferrer">
              open Foundry portal ↗
            </a>
          )}
        </div>

        <div style={{ display: 'flex', gap: '.5rem', flexWrap: 'wrap', marginBottom: '.9rem' }}>
          {Object.entries(RUNS_ON).map(([k, s]) => (
            <span key={k} className="faint" style={{ display: 'inline-flex', alignItems: 'center', gap: '.35rem' }}>
              <span className={`badge ${s.tone}`}>{s.label}</span> {s.hint}
            </span>
          ))}
        </div>

        {foundry && !foundry.available && (
          <div className="err" style={{ marginBottom: '.9rem', borderLeftColor: 'var(--c-gold)',
                                        background: 'rgba(217,83,106,.12)' }}>
            <strong>Hosted state is unknown.</strong> {foundry.reason}
          </div>
        )}

        <table>
          <thead>
            <tr>
              <th>agent</th><th style={{ width: '11rem' }}>runs on</th>
              <th>description</th><th style={{ width: '5rem' }}>temp</th>
              <th style={{ width: '16rem' }}>actions</th>
            </tr>
          </thead>
          <tbody>
            {all.map((a) => (
              <tr key={a.name}>
                <td>
                  <strong>{a.display_name}</strong>
                  <div className="faint mono">{a.name}</div>
                  {a.hosted && <div className="faint mono" style={{ fontSize: '.68rem' }}>{a.hosted.agent_id}</div>}
                </td>
                <td>
                  <RunsOnBadge runsOn={a.runs_on} reason={foundry?.reason} />
                  {a.hosted?.model && <div className="faint mono" style={{ marginTop: '.3rem' }}>{a.hosted.model}</div>}
                </td>
                <td>
                  {a.description}
                  {a.style_rules?.length > 0 && (
                    <ul style={{ margin: '.4rem 0 0', paddingLeft: '1.1rem' }} className="faint">
                      {a.style_rules.map((r, i) => <li key={i}>{r}</li>)}
                    </ul>
                  )}
                </td>
                <td className="mono">{a.temperature ?? '—'}</td>
                <td>
                  <div style={{ display: 'flex', gap: '.3rem', flexWrap: 'wrap' }}>
                    {a.runs_on !== 'foundry' && (
                      <button className="btn btn-outline btn-sm" disabled={!!busy}
                              title="Show the system prompt this JSON produces"
                              onClick={() => showPrompt(a.name)}>
                        prompt
                      </button>
                    )}
                    {a.runs_on !== 'foundry' && (
                      <button className="btn btn-outline btn-sm" disabled={!!busy}
                              title={a.runs_on === 'both' ? 'Update the hosted copy from this JSON' : 'Publish to the Foundry Agent Service'}
                              onClick={() => act(a.name, () => api.deployAgent(a.name),
                                (r) => `${r.action} in Foundry — ${r.agent_id}`)}>
                        {a.runs_on === 'both' ? 'update in Foundry' : 'deploy to Foundry'}
                      </button>
                    )}
                    {a.hosted && (
                      confirming === a.name ? (
                        <>
                          <button className="btn btn-sm" style={{ background: 'var(--grad-cta)', color: '#fff' }}
                                  disabled={!!busy}
                                  onClick={() => act(a.name, () => api.deleteHostedAgent(a.hosted.agent_id),
                                    () => `removed ${a.name} from Foundry`)}>
                            confirm delete
                          </button>
                          <button className="btn btn-outline btn-sm" onClick={() => setConfirming(null)}>cancel</button>
                        </>
                      ) : (
                        <button className="btn btn-outline btn-sm" disabled={!!busy}
                                title="Remove the hosted copy. The local JSON file is untouched."
                                onClick={() => setConfirming(a.name)}>
                          remove from Foundry
                        </button>
                      )
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {busy && <div style={{ marginTop: '.7rem' }}><Spinner label={busy} /></div>}
        {notice && <div className="card" style={{ marginTop: '.8rem', padding: '.6rem .8rem' }}>
          <span className="badge">done</span> <span className="mono">{notice}</span>
        </div>}
        <Err error={error} />
      </div>

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
