import { useEffect, useState } from 'react'
import { api } from '../api'
import { ChunkList, Err, Head, Hits, RawJson, Spinner } from '../components'

const SAMPLE = `Libra Bank issues debit and credit cards to retail customers. A card is blocked automatically after three failed PIN attempts, after the fraud engine flags a suspicious transaction, or at the customer's own request in the mobile application. A blocked card is unblocked in the branch after identity verification, or through the call centre using the phone banking password.

Mortgage loans require a down payment of at least fifteen percent for a first home. Early repayment is free of charge during the variable-rate period; during the fixed-rate period an early repayment fee of one percent applies.

Term deposits can be opened in RON, EUR or USD, with maturities from one month to two years. Breaking a deposit before maturity forfeits the accrued interest.`

export default function Knowledge() {
  const [text, setText] = useState(SAMPLE)
  const [strategy, setStrategy] = useState('dynamic')
  const [size, setSize] = useState(400)
  const [overlap, setOverlap] = useState(80)
  const [sentences, setSentences] = useState(3)
  const [threshold, setThreshold] = useState(0.75)
  const [preview, setPreview] = useState(null)
  const [ingested, setIngested] = useState(null)
  const [collection, setCollection] = useState(null)
  const [busy, setBusy] = useState('')
  const [error, setError] = useState(null)

  const refresh = () => api.collection().then(setCollection).catch(() => setCollection(null))
  useEffect(() => { refresh() }, [])

  const payload = () => ({
    text, strategy,
    chunk_size: Number(size), chunk_overlap: Number(overlap),
    sentences_per_chunk: Number(sentences), semantic_threshold: Number(threshold),
  })

  async function run(kind) {
    setBusy(kind); setError(null)
    try {
      if (kind === 'chunk') { setPreview(await api.chunk(payload())); setIngested(null) }
      else { const r = await api.ingest({ ...payload(), source: 'console' }); setIngested(r); setPreview(null); refresh() }
    } catch (e) { setError(e.message) } finally { setBusy('') }
  }

  async function reset() {
    setBusy('reset'); setError(null)
    try { await api.resetCollection(); setIngested(null); setPreview(null); refresh() }
    catch (e) { setError(e.message) } finally { setBusy('') }
  }

  return (
    <>
      <Head title="Knowledge">
        Split a document into chunks and store them as vectors. Chunking is the highest-leverage
        decision in a RAG pipeline — compare the strategies on the same text and watch the
        boundaries move.
      </Head>

      <div className="card">
        <label>Document</label>
        <textarea value={text} onChange={(e) => setText(e.target.value)} style={{ minHeight: 160 }} />

        <div className="row" style={{ marginTop: '.8rem' }}>
          <div>
            <label>Strategy</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              <option value="static">static — fixed windows</option>
              <option value="sentence">sentence — N per chunk</option>
              <option value="dynamic">dynamic — structure aware</option>
              <option value="semantic">semantic — meaning aware</option>
            </select>
          </div>
          {(strategy === 'static' || strategy === 'dynamic') && (<>
            <div><label>Chunk size</label><input type="number" value={size} onChange={(e) => setSize(e.target.value)} /></div>
            <div><label>Overlap</label><input type="number" value={overlap} onChange={(e) => setOverlap(e.target.value)} /></div>
          </>)}
          {strategy === 'sentence' && (
            <div><label>Sentences / chunk</label><input type="number" value={sentences} onChange={(e) => setSentences(e.target.value)} /></div>
          )}
          {strategy === 'semantic' && (
            <div><label>Similarity threshold</label><input type="number" step="0.05" min="0.05" max="1" value={threshold} onChange={(e) => setThreshold(e.target.value)} /></div>
          )}
        </div>

        <div className="row" style={{ marginTop: '.9rem' }}>
          <button className="btn btn-outline shrink" onClick={() => run('chunk')} disabled={!!busy}>Preview chunks</button>
          <button className="btn btn-primary shrink" onClick={() => run('ingest')} disabled={!!busy}>Chunk + embed + store</button>
          <div className="shrink" style={{ alignSelf: 'center' }}>{busy && <Spinner label={busy} />}</div>
        </div>
        <Err error={error} />
      </div>

      {preview && (
        <div className="card">
          <h3>{preview.count} chunks · strategy “{preview.strategy}” <span className="faint">(nothing stored)</span></h3>
          <ChunkList chunks={preview.chunks} />
          <RawJson data={preview} />
        </div>
      )}

      {ingested && (
        <div className="card">
          <h3>Stored {ingested.count} chunks</h3>
          <p className="muted" style={{ marginTop: 0 }}>
            Embedded with <code>{ingested.embedding_model.model}</code> into{' '}
            <strong>{ingested.vector_dimension}</strong> dimensions. First eight numbers of chunk 0:
          </p>
          <pre className="out">{JSON.stringify(ingested.embedding_preview)}</pre>
          <ChunkList chunks={ingested.chunks} />
          <RawJson data={ingested} />
        </div>
      )}

      <div className="card">
        <h3>Collection</h3>
        {collection ? (
          <div className="row">
            <div><label>name</label><div className="mono">{collection.name}</div></div>
            <div><label>points</label><div className="mono">{collection.points_count}</div></div>
            <div><label>dimensions</label><div className="mono">{collection.vector_dimension ?? '—'}</div></div>
            <div><label>distance</label><div className="mono">{collection.distance ?? '—'}</div></div>
            <button className="btn btn-outline shrink" onClick={reset} disabled={!!busy}>Reset collection</button>
          </div>
        ) : <p className="faint">Vector store unreachable — is Qdrant running?</p>}
      </div>
    </>
  )
}
