import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Err, RunsOnBadge } from '../components'

export default function Chat({ agents, hostedOnly = [], foundry }) {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [agent, setAgent] = useState('default')
  const [useRag, setUseRag] = useState(true)
  const [factCheck, setFactCheck] = useState(false)
  const [mode, setMode] = useState('local')
  const [topK, setTopK] = useState(3)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const endRef = useRef(null)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  async function send() {
    const text = question.trim()
    if (!text || busy) return
    setQuestion(''); setError(null); setBusy(true)
    setMessages((m) => [...m, { role: 'user', text }])
    try {
      const data = await api.ask({ question: text, use_rag: useRag, top_k: Number(topK),
                                  agent, agent_mode: mode, fact_check: factCheck })
      setMessages((m) => [...m, { role: 'bot', data }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'err', text: e.message }])
      setError(e.message)
    } finally { setBusy(false) }
  }

  const all = [...agents, ...hostedOnly]
  const current = all.find((a) => a.name === agent)

  // Three states, not two. `available === false` is not "we don't know" — it is a
  // definite no: the Agent Service cannot be reached from here at all, whichever agent
  // you pick, because a key was used where Entra is required. Offering the lane anyway
  // is how you get a 503 in the chat window instead of a greyed-out option.
  const foundryReachable = foundry?.available                 // true | false | undefined
  const isHosted = current?.runs_on === 'both' || current?.runs_on === 'foundry'
  const localImpossible = current?.runs_on === 'foundry'      // no JSON file to run here
  const foundryBlocked =
    foundryReachable === false ||                             // no identity — nothing can
    (foundryReachable === true && !isHosted)                  // reachable, but not deployed
  const foundryWhy =
    foundryReachable === false
      ? (foundry?.reason || 'The Agent Service cannot be reached from here.')
      : 'Not deployed to Foundry — deploy it from the Agents view'

  // Keep the mode legal whenever the selected agent changes.
  useEffect(() => {
    if (foundryBlocked && mode === 'foundry') setMode('local')
    else if (localImpossible && mode !== 'foundry') setMode('foundry')
  }, [agent, localImpossible, foundryBlocked])   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="chat-wrap">
      <div className="chat-bar">
        <select value={agent} onChange={(e) => setAgent(e.target.value)} title="Which persona answers">
          {agents.map((a) => <option key={a.name} value={a.name}>{a.display_name}</option>)}
          {hostedOnly.length > 0 && (
            <optgroup label="hosted in Foundry only">
              {hostedOnly.map((a) => <option key={a.name} value={a.name}>{a.display_name}</option>)}
            </optgroup>
          )}
        </select>
        {current && <RunsOnBadge runsOn={current.runs_on} reason={foundry?.reason} />}
        <label className="check" style={{ margin: 0 }} title="Retrieve from your documents and ground the answer">
          <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} />
          use RAG
        </label>
        <label className="check" style={{ margin: 0 }}
               title="After answering, verify the answer against the open web and attach a verdict">
          <input type="checkbox" checked={factCheck} onChange={(e) => setFactCheck(e.target.checked)} />
          fact-check
        </label>
        <select value={mode} onChange={(e) => setMode(e.target.value)} style={{ minWidth: '9rem' }}
                title="Where the loop executes">
          <option value="local" disabled={localImpossible}
                  title={localImpossible ? 'This agent has no local JSON file' : ''}>
            local agent
          </option>
          <option value="foundry" disabled={foundryBlocked} title={foundryBlocked ? foundryWhy : ''}>
            Foundry agent{foundryReachable === false ? ' — no identity'
                          : foundryBlocked ? ' — not deployed' : ''}
          </option>
        </select>
        <input type="number" min="1" max="10" value={topK} onChange={(e) => setTopK(e.target.value)}
               style={{ width: '4.5rem', flex: '0 0 auto' }} title="Passages to retrieve" />
        {foundryReachable === false && (
          <span className="badge muted" title={foundryWhy}>
            hosted agents off — key auth
          </span>
        )}
        <button className="btn btn-outline btn-sm" onClick={() => setMessages([])}>clear</button>
        {current && <span className="badge muted" title={current.description}>temp {current.temperature ?? '—'}</span>}
      </div>

      <div className="msgs">
        {messages.length === 0 && (
          <div className="card" style={{ alignSelf: 'center', maxWidth: '46rem', textAlign: 'center' }}>
            <h3>Libra Assist</h3>
            <p className="muted" style={{ margin: 0 }}>
              Ask a question about the documents you have ingested. Switch the persona to change how
              it answers, or turn RAG off to see the model answer without grounding.
            </p>
          </div>
        )}

        {messages.map((m, i) => {
          if (m.role === 'user') return <div className="msg user" key={i}>{m.text}</div>
          if (m.role === 'err') return <div className="msg err" key={i}><strong>Request failed:</strong> {m.text}</div>
          const d = m.data
          return (
            <div className="msg bot" key={i}>
              {d.answer}
              <div className="msg-meta">
                <span className="badge">{d.agent?.display_name || 'agent'}</span>
                <span className={`badge ${d.augmented ? 'gold' : 'muted'}`}>{d.augmented ? 'grounded' : 'no retrieval'}</span>
                <span className="badge muted">{d.agent?.mode}</span>
                <span className="badge muted">{d.model}</span>
                {d.usage && <span className="badge muted">{d.usage.prompt_tokens}↑ {d.usage.completion_tokens}↓ tokens</span>}
              </div>
              {d.fact_check && (
                <div className="src" style={{ marginTop: '.55rem',
                     borderLeftColor: d.fact_check.verdict === 'supported' ? 'var(--c-teal)'
                       : d.fact_check.verdict === 'contradicted' ? 'var(--c-crimson)' : 'var(--c-gold)' }}>
                  <span className={`badge ${d.fact_check.verdict === 'contradicted' ? 'crimson'
                    : d.fact_check.verdict === 'supported' ? '' : 'gold'}`}>
                    fact-check: {d.fact_check.verdict}
                  </span>{' '}
                  <span className="faint">{d.fact_check.confidence} confidence · {d.fact_check.evidence_from}</span>
                  {d.fact_check.error
                    ? <div className="faint" style={{ marginTop: '.3rem' }}>{d.fact_check.error}</div>
                    : <div style={{ marginTop: '.3rem' }}>{d.fact_check.reasoning}</div>}
                  {d.fact_check.sources?.length > 0 && (
                    <ul className="faint" style={{ margin: '.35rem 0 0', paddingLeft: '1.1rem' }}>
                      {d.fact_check.sources.map((sc) => (
                        <li key={sc.rank}>
                          <a href={sc.url} target="_blank" rel="noreferrer">{sc.title || sc.url}</a>
                          {' '}{sc.used ? `(${sc.chars_read} chars read)` : '(could not be read)'}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
              {d.retrieved?.length > 0 && (
                <details className="sources">
                  <summary>{d.retrieved.length} retrieved passage{d.retrieved.length > 1 ? 's' : ''}</summary>
                  {d.retrieved.map((h, j) => (
                    <div className="src" key={h.id}>
                      <span className="score">[{j + 1}] score {h.score.toFixed(4)}</span>
                      <div>{h.text}</div>
                    </div>
                  ))}
                </details>
              )}
              <details className="sources">
                <summary>the exact prompt that was sent</summary>
                <pre className="out" style={{ marginTop: '.4rem' }}>{`SYSTEM:\n${d.system_prompt}\n\nUSER:\n${d.prompt_sent}`}</pre>
              </details>
            </div>
          )
        })}
        {busy && <div className="msg bot"><span className="spin" /> thinking…</div>}
        <div ref={endRef} />
      </div>

      <Err error={error} />
      <div className="composer">
        <textarea value={question} placeholder="Ask Libra Assist…  (Enter to send, Shift+Enter for a new line)"
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
        <button className="btn btn-primary" onClick={send} disabled={busy || !question.trim()}>Send</button>
      </div>
    </div>
  )
}
