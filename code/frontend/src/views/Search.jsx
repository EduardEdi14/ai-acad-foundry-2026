import { useState } from 'react'
import { api } from '../api'
import { Err, Head, Hits, RawJson, Spinner } from '../components'

const EXAMPLES = [
  'my card got frozen, what do I do?',
  'can I pay my mortgage back sooner?',
  'what happens if I break a deposit early?',
  'what is the weather in Cluj?',
]

export default function Search() {
  const [query, setQuery] = useState(EXAMPLES[0])
  const [topK, setTopK] = useState(3)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  async function run(q = query) {
    setBusy(true); setError(null)
    try { setResult(await api.search({ query: q, top_k: Number(topK) })) }
    catch (e) { setError(e.message); setResult(null) } finally { setBusy(false) }
  }

  return (
    <>
      <Head title="Retrieval">
        The query is embedded with the same model as the documents, then compared by cosine
        similarity. Try a paraphrase that shares no words with the source text — and an
        off-topic question, to watch the scores collapse.
      </Head>

      <div className="card">
        <div className="row">
          <div style={{ flex: 3 }}>
            <label>Query</label>
            <input type="text" value={query} onChange={(e) => setQuery(e.target.value)}
                   onKeyDown={(e) => e.key === 'Enter' && run()} />
          </div>
          <div style={{ maxWidth: '6rem' }}><label>top k</label>
            <input type="number" min="1" max="20" value={topK} onChange={(e) => setTopK(e.target.value)} /></div>
          <button className="btn btn-primary shrink" onClick={() => run()} disabled={busy}>Search</button>
        </div>
        <div style={{ display: 'flex', gap: '.4rem', flexWrap: 'wrap', marginTop: '.7rem' }}>
          {EXAMPLES.map((e) => (
            <button key={e} className="btn btn-outline btn-sm" onClick={() => { setQuery(e); run(e) }}>{e}</button>
          ))}
        </div>
        {busy && <div style={{ marginTop: '.7rem' }}><Spinner label="searching" /></div>}
        <Err error={error} />
      </div>

      {result && (
        <div className="card">
          <h3>{result.hits.length} hits for “{result.query}”</h3>
          <p className="faint" style={{ marginTop: 0 }}>
            embedded with <code>{result.embedding_model.model}</code> · query vector starts{' '}
            <span className="mono">[{result.query_embedding_preview.slice(0, 4).join(', ')}…]</span>
          </p>
          <Hits hits={result.hits} />
          <RawJson data={result} />
        </div>
      )}
    </>
  )
}
