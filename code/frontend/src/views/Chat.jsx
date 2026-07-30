import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { Err, RunsOnBadge } from '../components'

// Two things persist in the browser, per agent:
//  - the ACTIVE conversation (still being added to — survives reloads and agent switches)
//  - the ARCHIVE (past conversations, saved off by "new chat" or by restoring a different one)
const ACTIVE_PREFIX = 'edi-libra-chat:'
const ARCHIVE_PREFIX = 'edi-libra-chat-archive:'

function loadActive(agentName) {
  try {
    const raw = localStorage.getItem(ACTIVE_PREFIX + agentName)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveActive(agentName, messages) {
  try {
    localStorage.setItem(ACTIVE_PREFIX + agentName, JSON.stringify(messages))
  } catch {
    /* storage full or unavailable — history just won't persist this time */
  }
}

function loadArchive(agentName) {
  try {
    const raw = localStorage.getItem(ARCHIVE_PREFIX + agentName)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveArchive(agentName, entries) {
  try {
    localStorage.setItem(ARCHIVE_PREFIX + agentName, JSON.stringify(entries))
  } catch {
    /* storage full or unavailable — archive just won't persist this time */
  }
}

// A short label for an archived conversation — the customer's first message, so the
// list is scannable without opening each one.
function conversationTitle(messages) {
  const firstUser = messages.find((m) => m.role === 'user')
  if (!firstUser) return 'Conversation'
  const t = firstUser.text.trim()
  return t.length > 56 ? t.slice(0, 56) + '…' : t
}

// General security-awareness facts (not this bank's specific numbers, so they never
// contradict a grounded answer) — one is shown when a conversation starts empty.
const CYBER_TIPS = [
  "Most account takeovers don't start with a hacked password — they start with a phone call or text that convinces someone to hand over a one-time code.",
  "An SMS code is better than nothing, but SIM-swapping can intercept it. An authenticator app or hardware key is much harder to steal.",
  "Ransomware rarely triggers the moment it lands on a system — attackers often sit quietly inside a network for days or weeks first, studying what's valuable.",
  "The padlock icon in your browser only means the connection is encrypted — it says nothing about whether the site itself is trustworthy. Phishing sites use HTTPS too.",
  "Password reuse is the single biggest amplifier of a data breach: one leaked password from an unrelated site is often enough to unlock accounts elsewhere.",
  "Public Wi-Fi attacks rarely involve 'hacking' the network itself — more often it's a fake hotspot with a familiar-looking name, waiting for a device to connect automatically.",
  "Organizations often take months to even notice a breach — which is exactly why fast, customer-side reporting matters so much.",
  "Social engineering usually wins through urgency, not technical skill: 'act now or lose access' is designed to short-circuit the moment you'd normally stop and verify.",
  "Encryption 'in transit' (moving over a network) and 'at rest' (stored on a disk) are two separate protections — a system can have one without the other.",
]

function pickTip() {
  return CYBER_TIPS[Math.floor(Math.random() * CYBER_TIPS.length)]
}

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

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ))
}

export default function Chat({ agents, hostedOnly = [], foundry }) {
  const [agent, setAgent] = useState('default')
  const [messages, setMessages] = useState(() => loadActive('default'))
  const [archive, setArchive] = useState(() => loadArchive('default'))
  const [historyOpen, setHistoryOpen] = useState(false)
  const [tip, setTip] = useState(pickTip)
  const [lastCleared, setLastCleared] = useState(null)   // messages wiped by "clear", restorable by "undo"
  const [question, setQuestion] = useState('')
  const [useRag, setUseRag] = useState(true)
  const [factCheck, setFactCheck] = useState(false)
  const [mode, setMode] = useState('local')
  const [topK, setTopK] = useState(3)
  // Below this cosine similarity, a retrieved passage is noise, not grounding evidence —
  // without it, a plain "hello" still returns *something* (Qdrant always returns its
  // nearest neighbours) and the persona treats that as context to answer strictly from.
  // 0.45 was calibrated live against this corpus/embedding model (see NOTES.md #1):
  // real matches score ~0.41-0.55, small talk and off-topic queries top out ~0.22-0.25.
  const [scoreThreshold, setScoreThreshold] = useState(0.45)
  const [product, setProduct] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [speaking, setSpeaking] = useState(null)      // index of the message loading or playing TTS
  const [ttsPlaying, setTtsPlaying] = useState(false)  // true once playback has actually started
  const [ttsPaused, setTtsPaused] = useState(false)    // true while paused mid-playback
  const [ttsSpeed, setTtsSpeed] = useState(1)          // 1 or 2 — a preference, kept across messages
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const endRef = useRef(null)
  const audioCtxRef = useRef(null)
  const streamRef = useRef(null)
  const processorRef = useRef(null)
  const samplesRef = useRef([])
  const ttsAudioRef = useRef(null)
  const speakTokenRef = useRef(0)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  // Switching agents loads THAT agent's active conversation and its archive (not
  // before messages has already been persisted for whichever agent was active —
  // see the save effect).
  useEffect(() => {
    const loaded = loadActive(agent)
    setMessages(loaded)
    setArchive(loadArchive(agent))
    setHistoryOpen(false)
    setLastCleared(null)
    if (loaded.length === 0) setTip(pickTip())
  }, [agent])

  // Every change to messages is persisted under the currently selected agent. This
  // intentionally does not depend on `agent` — only on `messages` — so an agent
  // switch never re-saves the outgoing agent's messages under the incoming agent's key.
  useEffect(() => { saveActive(agent, messages) }, [messages]) // eslint-disable-line react-hooks/exhaustive-deps

  // Text-to-speech for a bot answer, via the Azure Speech tool the backend already
  // exposes at /tools/speak. Each persona can set its own `voice` in its JSON —
  // edi-libra does — so the same message read back sounds like that agent, not a
  // generic default.
  //
  // `speakTokenRef` guards against a stale response landing after the user has
  // already stopped playback or started reading a different message — without it,
  // a slow /tools/speak call could still start playing audio after being "stopped".
  function stopSpeaking() {
    speakTokenRef.current++
    if (ttsAudioRef.current) {
      ttsAudioRef.current.pause()
      ttsAudioRef.current.currentTime = 0
      ttsAudioRef.current = null
    }
    setSpeaking(null)
    setTtsPlaying(false)
    setTtsPaused(false)
  }

  // Pauses/resumes in place — unlike stopSpeaking, this keeps the already-fetched
  // audio and its playback position, so resuming does not re-call /tools/speak.
  function togglePause() {
    const audio = ttsAudioRef.current
    if (!audio) return
    if (ttsPaused) { audio.play(); setTtsPaused(false) }
    else { audio.pause(); setTtsPaused(true) }
  }

  // Toggles 1x/2x. Applies instantly to whatever is currently playing (the browser
  // adjusts playbackRate live, no restart needed) and to whatever plays next.
  function toggleSpeed() {
    const next = ttsSpeed === 1 ? 2 : 1
    setTtsSpeed(next)
    if (ttsAudioRef.current) ttsAudioRef.current.playbackRate = next
  }

  async function startSpeaking(i, text, voice) {
    stopSpeaking()   // only one message speaks at a time; also resets a paused session
    setError(null)
    setSpeaking(i)
    const token = ++speakTokenRef.current
    try {
      const blob = await api.speak({ text, voice })
      if (speakTokenRef.current !== token) return     // superseded while we were fetching
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio.playbackRate = ttsSpeed
      ttsAudioRef.current = audio
      audio.onended = () => { URL.revokeObjectURL(url); if (speakTokenRef.current === token) stopSpeaking() }
      setTtsPlaying(true)
      await audio.play()
    } catch (e) {
      if (speakTokenRef.current === token) { setError(e.message); stopSpeaking() }
    }
  }

  function listen(i, text, voice) {
    if (speaking === i) { stopSpeaking(); return }   // clicking the active message again = stop
    startSpeaking(i, text, voice)
  }

  // Leaving the Chat view (switching to another page) should not leave audio playing.
  useEffect(() => () => { ttsAudioRef.current?.pause() }, [])

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

  // Archives the active conversation into this agent's history list and returns the
  // resulting array — callers that also need to modify the archive right afterwards
  // (restoreConversation) must build on this return value, not on the `archive` state
  // variable, since setState here has not been applied yet within the same call.
  function archiveCurrent() {
    if (messages.length === 0) return archive
    const entry = {
      id: crypto.randomUUID?.() || String(Date.now()),
      title: conversationTitle(messages),
      savedAt: Date.now(),
      messages,
    }
    const next = [entry, ...archive]
    setArchive(next)
    saveArchive(agent, next)
    return next
  }

  function startNewChat() {
    archiveCurrent()
    stopSpeaking()
    setQuestion('')
    setError(null)
    setMessages([])
    setHistoryOpen(false)
    setLastCleared(null)
    setTip(pickTip())
  }

  function restoreConversation(entry) {
    const afterArchiving = archiveCurrent()   // don't lose whatever's active right now
    stopSpeaking()
    setQuestion('')
    setError(null)
    setMessages(entry.messages)
    const next = afterArchiving.filter((e) => e.id !== entry.id)
    setArchive(next)
    saveArchive(agent, next)
    setHistoryOpen(false)
    setLastCleared(null)
  }

  function deleteArchived(id) {
    setArchive((prev) => {
      const next = prev.filter((e) => e.id !== id)
      saveArchive(agent, next)
      return next
    })
  }

  async function send() {
    const text = question.trim()
    if (!text || busy) return
    setQuestion(''); setError(null); setBusy(true); setLastCleared(null)
    setMessages((m) => [...m, { role: 'user', text, at: Date.now() }])
    try {
      const data = await api.ask({
        question: text, use_rag: useRag, top_k: Number(topK), score_threshold: Number(scoreThreshold),
        agent, agent_mode: mode, product: product || undefined, fact_check: factCheck,
      })
      setMessages((m) => [...m, { role: 'bot', data, at: Date.now() }])
    } catch (e) {
      setMessages((m) => [...m, { role: 'err', text: e.message, at: Date.now() }])
      setError(e.message)
    } finally { setBusy(false) }
  }

  // Exports the conversation as a printable HTML document and opens the browser's
  // print dialog, where "Save as PDF" produces the actual file — no PDF-generation
  // library needed, and every browser already knows how to do this reliably.
  function exportConversation() {
    if (messages.length === 0) return
    const win = window.open('', '_blank')
    if (!win) { setError("Could not open the export window — check your browser's popup blocker."); return }

    const rows = messages.map((m) => {
      const when = m.at ? new Date(m.at).toLocaleString() : ''
      if (m.role === 'user') {
        return `<div class="row user"><div class="bubble">
          <div class="who">You <span class="when">${escapeHtml(when)}</span></div>
          <div class="text">${escapeHtml(m.text)}</div>
        </div></div>`
      }
      if (m.role === 'err') {
        return `<div class="row"><div class="bubble err">
          <div class="who">Error <span class="when">${escapeHtml(when)}</span></div>
          <div class="text">${escapeHtml(m.text)}</div>
        </div></div>`
      }
      const d = m.data
      return `<div class="row"><div class="bubble">
        <div class="who">${escapeHtml(d.agent?.display_name || 'Agent')} <span class="when">${escapeHtml(when)}</span></div>
        <div class="text">${escapeHtml(d.answer)}</div>
        <div class="meta">${escapeHtml(d.augmented ? 'grounded' : 'no retrieval')}${d.agent?.mode ? ' · ' + escapeHtml(d.agent.mode) : ''}${d.model ? ' · ' + escapeHtml(d.model) : ''}</div>
      </div></div>`
    }).join('\n')

    win.document.write(`<!doctype html>
<html><head><meta charset="utf-8"><title>edi-libra conversation — ${escapeHtml(new Date().toLocaleDateString())}</title>
<style>
  body { font-family: -apple-system, 'Segoe UI', Arial, sans-serif; max-width: 720px; margin: 2.5rem auto; color: #18181b; line-height: 1.5; }
  h1 { font-size: 1.25rem; margin-bottom: .1rem; }
  .subtitle { color: #71717a; font-size: .85rem; margin-bottom: 2rem; }
  .row { margin: 1rem 0; display: flex; }
  .row.user { justify-content: flex-end; }
  .bubble { max-width: 80%; padding: .7rem 1rem; border-radius: 10px; background: #f4f4f5; }
  .row.user .bubble { background: #b91c1c; color: #fff; }
  .bubble.err { background: #fee2e2; color: #7f1d1d; }
  .who { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; opacity: .65; margin-bottom: .3rem; }
  .when { font-weight: 400; text-transform: none; letter-spacing: 0; margin-left: .4rem; }
  .text { white-space: pre-wrap; word-break: break-word; }
  .meta { margin-top: .4rem; font-size: .72rem; opacity: .6; }
  @media print { body { margin: 0 auto; } }
</style></head>
<body>
  <h1>edi-libra — conversation transcript</h1>
  <div class="subtitle">Exported ${escapeHtml(new Date().toLocaleString())} · ${messages.length} message${messages.length === 1 ? '' : 's'}</div>
  ${rows}
</body></html>`)
    win.document.close()
    win.focus()
    // Give the new document a moment to lay out before the print dialog opens.
    setTimeout(() => win.print(), 300)
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
            <div>
              <label style={{ marginBottom: '.2rem' }}>min. relevance</label>
              <input type="number" min="0" max="1" step="0.05" value={scoreThreshold}
                     onChange={(e) => setScoreThreshold(e.target.value)}
                     title="Below this cosine similarity, a passage is treated as irrelevant — off-topic questions (e.g. a greeting) get no grounding instead of being answered from the nearest, unrelated document" />
            </div>
            {current && <span className="badge muted" title={current.description}>temp {current.temperature ?? '—'}</span>}
          </div>
        </details>

        <div style={{ display: 'flex', gap: '.5rem', marginLeft: 'auto' }}>
          <button className={`btn btn-sm ${historyOpen ? 'btn-primary' : 'btn-outline'}`}
                  onClick={() => setHistoryOpen((o) => !o)}
                  title="Past conversations with this agent, saved in this browser">
            history{archive.length > 0 ? ` (${archive.length})` : ''}
          </button>
          <button className="btn btn-outline btn-sm" onClick={startNewChat}
                  title="Save the current conversation to history and start a blank one">
            + new chat
          </button>
          <button className="btn btn-outline btn-sm" onClick={exportConversation} disabled={messages.length === 0}
                  title="Export this conversation as a PDF (opens the browser's print dialog)">
            export PDF
          </button>
          <button className="btn btn-outline btn-sm"
                  onClick={() => {
                    if (messages.length > 0) setLastCleared(messages)
                    setMessages([]); setTip(pickTip())
                  }}
                  title="Discard the current conversation without saving it to history">
            clear
          </button>
          {lastCleared && (
            <button className="btn btn-outline btn-sm"
                    onClick={() => { setMessages(lastCleared); setLastCleared(null) }}
                    title="Restore the conversation you just cleared">
              ↩ undo
            </button>
          )}
        </div>
      </div>

      {historyOpen && (
        <div className="card" style={{ marginBottom: '.9rem' }}>
          <h3 style={{ marginBottom: '.6rem' }}>Past conversations with {current?.display_name || agent}</h3>
          {archive.length === 0 ? (
            <p className="muted" style={{ margin: 0 }}>
              Nothing saved yet — "+ new chat" or restoring a different conversation archives the
              current one here first.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '.5rem' }}>
              {archive.map((entry) => (
                <div key={entry.id} className="src"
                     style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '.6rem' }}>
                  <button className="btn btn-outline btn-sm"
                          style={{ flex: 1, justifyContent: 'flex-start', textAlign: 'left', textTransform: 'none' }}
                          onClick={() => restoreConversation(entry)}>
                    <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '.15rem' }}>
                      <span>{entry.title}</span>
                      <span className="faint">
                        {new Date(entry.savedAt).toLocaleString()} · {entry.messages.length} message{entry.messages.length === 1 ? '' : 's'}
                      </span>
                    </span>
                  </button>
                  <button className="pill-x" onClick={() => deleteArchived(entry.id)}
                          aria-label="Delete this conversation" title="Delete">×</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="msgs">
        {messages.length === 0 && !historyOpen && (
          <div className="card" style={{ alignSelf: 'center', maxWidth: '46rem', textAlign: 'center' }}>
            <h3>{current?.display_name || 'edi-libra'}</h3>
            <p style={{ margin: 0 }}>💡 {tip}</p>
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
                {speaking === i && ttsPlaying ? (
                  <>
                    <button className="btn btn-outline btn-sm" onClick={togglePause}
                            title={ttsPaused ? 'Resume playback' : 'Pause playback'}>
                      {ttsPaused ? <>▶ resume</> : <>⏸ pause</>}
                    </button>
                    <button className="btn btn-outline btn-sm"
                            onClick={() => startSpeaking(i, d.answer, d.agent?.voice)}
                            title="Restart this answer from the beginning">
                      🔄 reload
                    </button>
                    <button className={`btn btn-sm ${ttsSpeed === 2 ? 'btn-primary' : 'btn-outline'}`}
                            onClick={toggleSpeed}
                            title={ttsSpeed === 2 ? 'Playing at 2x — click for normal speed' : 'Play at 2x speed'}>
                      {ttsSpeed}x
                    </button>
                  </>
                ) : (
                  <button className="btn btn-outline btn-sm" onClick={() => listen(i, d.answer, d.agent?.voice)}
                          disabled={speaking === i} title="Read this answer aloud (Azure Speech)">
                    {speaking === i ? <span className="spin" /> : '🔊'} listen
                  </button>
                )}
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
            <button className={`btn btn-mic ${recording ? 'btn-primary' : 'btn-outline'}`}
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
