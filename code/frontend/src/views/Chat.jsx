import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Err, RunsOnBadge } from '../components'

// Float32 samples (from the Web Audio API) -> a 16-bit PCM mono WAV blob.
function encodeWav(chunks, sampleRate) {
  const length = chunks.reduce((n, c) => n + c.length, 0)
  const pcm = new Int16Array(length)
  let offset = 0
  for (const chunk of chunks) {
    for (let i = 0; i < chunk.length; i++) {
      const s = Math.max(-1, Math.min(1, chunk[i]))
      pcm[offset++] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
  }
  const buffer = new ArrayBuffer(44 + pcm.length * 2)
  const view = new DataView(buffer)
  const writeStr = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)) }
  writeStr(0, 'RIFF'); view.setUint32(4, 36 + pcm.length * 2, true); writeStr(8, 'WAVE')
  writeStr(12, 'fmt '); view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  writeStr(36, 'data'); view.setUint32(40, pcm.length * 2, true)
  new Int16Array(buffer, 44).set(pcm)
  return new Blob([buffer], { type: 'audio/wav' })
}

// Renders an answer line by line so numbered-list digits and [n] citation
// markers can be styled distinctly from the surrounding prose.
function formatAnswer(text) {
  function renderInline(str, keyPrefix) {
    const re = /\[(\d+)\]/g
    const parts = []
    let last = 0, m, i = 0
    while ((m = re.exec(str))) {
      if (m.index > last) parts.push(str.slice(last, m.index))
      parts.push(<span className="citation" key={`${keyPrefix}-c${i++}`}>[{m[1]}]</span>)
      last = m.index + m[0].length
    }
    if (last < str.length) parts.push(str.slice(last))
    return parts
  }
  return (text || '').split('\n').map((line, i) => {
    const numbered = line.match(/^(\d+)\.\s+(.*)$/)
    if (numbered) {
      return (
        <div className="ans-line ans-numbered" key={i}>
          <span className="ans-digit">{numbered[1]}.</span>
          <span>{renderInline(numbered[2], i)}</span>
        </div>
      )
    }
    return <div className="ans-line" key={i}>{line.trim() ? renderInline(line, i) : ' '}</div>
  })
}

export default function Chat({ agents, hostedOnly = [], foundry }) {
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [agent, setAgent] = useState('default')
  const [useRag, setUseRag] = useState(true)
  const [factCheck, setFactCheck] = useState(false)
  const [mode, setMode] = useState('local')
  const [topK, setTopK] = useState(3)
  const [product, setProduct] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [speaking, setSpeaking] = useState(null)
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const endRef = useRef(null)
  const audioCtxRef = useRef(null)
  const streamRef = useRef(null)
  const processorRef = useRef(null)
  const samplesRef = useRef([])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  // Text-to-speech for a bot answer, via the Azure Speech tool the backend already
  // exposes at /tools/speak. Each persona can set its own `voice` in its JSON —
  // edi-libra does — so the same message read back sounds like that agent, not a
  // generic default.
  async function listen(i, text, voice) {
    setSpeaking(i); setError(null)
    try {
      const blob = await api.speak({ text, voice })
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.onended = () => URL.revokeObjectURL(url)
      await audio.play()
    } catch (e) {
      setError(e.message)
    } finally {
      setSpeaking(null)
    }
  }

  // Speech-to-text: capture the mic as raw PCM via the Web Audio API and encode a
  // plain WAV ourselves, instead of MediaRecorder's webm/opus output — the backend's
  // /tools/transcribe (Azure Speech) is what already round-trips WAV successfully
  // for the "Tools" page, so this keeps the same, known-working format.
  async function toggleRecording() {
    if (recording) { stopRecording(); return }
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 })
      const source = audioCtx.createMediaStreamSource(stream)
      const processor = audioCtx.createScriptProcessor(4096, 1, 1)
      samplesRef.current = []
      processor.onaudioprocess = (e) => samplesRef.current.push(new Float32Array(e.inputBuffer.getChannelData(0)))
      source.connect(processor)
      processor.connect(audioCtx.destination)
      streamRef.current = stream
      audioCtxRef.current = audioCtx
      processorRef.current = processor
      setRecording(true)
    } catch (e) {
      setError(e.message || 'Microphone access was denied.')
    }
  }

  async function stopRecording() {
    processorRef.current?.disconnect()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    const sampleRate = audioCtxRef.current?.sampleRate || 16000
    audioCtxRef.current?.close()
    setRecording(false)

    if (samplesRef.current.length === 0) return
    setTranscribing(true)
    try {
      const file = new File([encodeWav(samplesRef.current, sampleRate)], 'question.wav', { type: 'audio/wav' })
      const result = await api.transcribe(file)
      setQuestion((q) => (q ? `${q} ${result.text}` : result.text))
    } catch (e) {
      setError(e.message)
    } finally {
      setTranscribing(false)
    }
  }

  async function send() {
    const text = question.trim()
    if (!text || busy) return
    setQuestion(''); setError(null); setBusy(true)
    setMessages((m) => [...m, { role: 'user', text }])
    try {
      const data = await api.ask({
        question: text, use_rag: useRag, top_k: Number(topK), agent, agent_mode: mode,
        product: product || undefined, fact_check: factCheck,
      })
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

  // A persona can scope itself to one corner of the knowledge base (edi-libra ->
  // "cybersecurity", set in its JSON as default_product). Switching to it re-scopes the
  // filter automatically so it never answers from unrelated documents; switching away
  // clears it. The field stays editable — this is a default, not a lock.
  useEffect(() => {
    setProduct(current?.default_product || '')
  }, [agent])   // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="chat-wrap">
      <div className="control-bar">
        <div className="control-group">
          <select value={agent} onChange={(e) => setAgent(e.target.value)} title="Which persona answers">
            {agents.map((a) => <option key={a.name} value={a.name}>{a.display_name}</option>)}
            {hostedOnly.length > 0 && (
              <optgroup label="hosted in Foundry only">
                {hostedOnly.map((a) => <option key={a.name} value={a.name}>{a.display_name}</option>)}
              </optgroup>
            )}
          </select>
          {current && <RunsOnBadge runsOn={current.runs_on} reason={foundry?.reason} />}
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
        </div>

        <div className="control-group">
          <label className="toggle" title="Retrieve from your documents and ground the answer">
            <input type="checkbox" checked={useRag} onChange={(e) => setUseRag(e.target.checked)} />
            <span className="toggle-track"><span className="toggle-thumb" /></span>
            use RAG
          </label>
          <label className="toggle" title="After answering, verify the answer against the open web and attach a verdict">
            <input type="checkbox" checked={factCheck} onChange={(e) => setFactCheck(e.target.checked)} />
            <span className="toggle-track"><span className="toggle-thumb" /></span>
            fact-check
          </label>
        </div>

        <div className="control-group">
          <div className="pill-input" title={current?.default_product
            ? `${current.display_name} defaults to product="${current.default_product}" — clear to search everything`
            : 'Scope retrieval to one metadata product; empty = search the whole knowledge base'}>
            <span className="pill-input-label">scope</span>
            <input type="text" value={product} onChange={(e) => setProduct(e.target.value)}
                   placeholder="all documents" />
            {product && <button className="pill-x" onClick={() => setProduct('')} aria-label="Clear product filter">×</button>}
          </div>
          {foundryReachable === false && (
            <span className="badge muted" title={foundryWhy}>hosted agents off — key auth</span>
          )}
        </div>

        <details className="inspector">
          <summary><span className="chevron">▸</span> inspector</summary>
          <div className="inspector-body">
            <div>
              <label style={{ marginBottom: '.2rem' }}>top K</label>
              <input type="number" min="1" max="10" value={topK} onChange={(e) => setTopK(e.target.value)}
                     title="Passages to retrieve" />
            </div>
            {current && <span className="badge muted" title={current.description}>temp {current.temperature ?? '—'}</span>}
          </div>
        </details>

        <button className="btn btn-outline btn-sm" onClick={() => setMessages([])} style={{ marginLeft: 'auto' }}>
          clear
        </button>
      </div>

      <div className="msgs">
        {messages.length === 0 && (
          <div className="card" style={{ alignSelf: 'center', maxWidth: '46rem', textAlign: 'center' }}>
            <h3>edi-libra</h3>
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
              {formatAnswer(d.answer)}
              <div className="msg-meta">
                <span className="badge">{d.agent?.display_name || 'agent'}</span>
                <span className={`badge ${d.augmented ? 'gold' : 'muted'}`}>{d.augmented ? 'grounded' : 'no retrieval'}</span>
                <span className="badge muted">{d.agent?.mode}</span>
                <span className="badge muted">{d.model}</span>
                {d.product_filter && <span className="badge" title="Retrieval was scoped to this metadata product">scoped: {d.product_filter}</span>}
                {d.usage && <span className="badge muted">{d.usage.prompt_tokens}↑ {d.usage.completion_tokens}↓ tokens</span>}
                <button className="btn btn-outline btn-sm" onClick={() => listen(i, d.answer, d.agent?.voice)}
                        disabled={speaking === i} title="Read this answer aloud (Azure Speech)">
                  {speaking === i ? <span className="spin" /> : '🔊'} listen
                </button>
              </div>
              {d.fact_check && (
                <div className="src" style={{ marginTop: '.55rem',
                     borderLeftColor: d.fact_check.verdict === 'supported' ? 'var(--red-800)'
                       : d.fact_check.verdict === 'contradicted' ? 'var(--crimson)' : 'var(--c-gold)' }}>
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
      <div className="composer-card">
        <textarea value={question} placeholder="Ask edi-libra…"
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }} />
        <div className="composer-bar">
          <span className="composer-hint">Enter to send · Shift+Enter for a new line</span>
          <div className="composer-actions">
            <button className={`btn btn-sm ${recording ? 'btn-primary' : 'btn-outline'}`}
                    onClick={toggleRecording} disabled={transcribing}
                    title={recording ? 'Stop recording' : 'Dictate your question (Azure Speech)'}>
              {transcribing ? <span className="spin" /> : recording ? '⏹' : '🎙'}
            </button>
            <button className="btn btn-primary" onClick={send} disabled={busy || !question.trim()}>Send</button>
          </div>
        </div>
      </div>
    </div>
  )
}
