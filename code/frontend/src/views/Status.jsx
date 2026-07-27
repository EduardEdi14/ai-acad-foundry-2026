import { useEffect, useState } from 'react'
import { api } from '../api'
import { Err, Head, RawJson, Spinner } from '../components'

export default function Status({ health, reload }) {
  const [config, setConfig] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(true)

  useEffect(() => {
    api.config().then(setConfig).catch((e) => setError(e.message)).finally(() => setBusy(false))
  }, [])

  const rows = health ? [
    ['API', health.status, health.status === 'ok'],
    ['Vector store', `${health.qdrant} · ${health.qdrant_url}`, health.qdrant === 'ok'],
    ['Chat model', `${health.llm.provider} · ${health.llm.model}`, true],
    ['Embeddings', `${health.embeddings.provider} · ${health.embeddings.model}`, true],
    ['Agent mode', `${health.agents?.mode} · default “${health.agents?.default_persona}”`, true],
    ['Personas', (health.agents?.available || []).join(', ') || '—', true],
    ['Speech', health.speech?.configured ? `configured · ${health.speech.region}` : 'not configured', !!health.speech?.configured],
  ] : []

  return (
    <>
      <Head title="Status">
        What this console is talking to. Every value here comes from the backend's own
        <code> /health</code> and <code>/config</code> endpoints.
      </Head>

      <div className="card">
        <div className="row" style={{ marginBottom: '.5rem' }}>
          <h3 style={{ margin: 0 }}>Health</h3>
          <button className="btn btn-outline btn-sm shrink" onClick={reload}>refresh</button>
        </div>
        {health ? (
          <table>
            <tbody>
              {rows.map(([k, v, ok]) => (
                <tr key={k}>
                  <td style={{ width: '11rem' }} className="muted">{k}</td>
                  <td className="mono">{v}</td>
                  <td style={{ width: '3rem' }}>
                    <span className={`badge ${ok ? '' : 'crimson'}`}>{ok ? 'ok' : '!'}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="faint">Backend unreachable — is it running on port 7799?</p>}
      </div>

      <div className="card">
        <h3>Configuration <span className="faint">(secrets masked by the API)</span></h3>
        {busy && <Spinner label="loading" />}
        <Err error={error} />
        {config && (
          <div className="grid2">
            <div>
              <label>chunking</label>
              <pre className="out">{JSON.stringify(config.chunking, null, 2)}</pre>
              <label style={{ marginTop: '.7rem' }}>retrieval</label>
              <pre className="out">{JSON.stringify(config.retrieval, null, 2)}</pre>
            </div>
            <div>
              <label>generation</label>
              <pre className="out">{JSON.stringify(config.generation, null, 2)}</pre>
              <label style={{ marginTop: '.7rem' }}>providers</label>
              <pre className="out">{JSON.stringify(config.providers, null, 2)}</pre>
            </div>
          </div>
        )}
        <RawJson data={health} label="raw /health" />
      </div>
    </>
  )
}
