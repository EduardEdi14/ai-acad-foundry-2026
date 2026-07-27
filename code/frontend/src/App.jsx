import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import Agents from './views/Agents'
import Chat from './views/Chat'
import Knowledge from './views/Knowledge'
import Search from './views/Search'
import Status from './views/Status'
import Tools from './views/Tools'

const VIEWS = [
  { id: 'chat', label: 'Chat', group: 'Assistant' },
  { id: 'knowledge', label: 'Knowledge', group: 'Pipeline' },
  { id: 'search', label: 'Retrieval', group: 'Pipeline' },
  { id: 'agents', label: 'Agents', group: 'Platform' },
  { id: 'tools', label: 'Tools', group: 'Platform' },
  { id: 'status', label: 'Status', group: 'Platform' },
]

export default function App() {
  const [view, setView] = useState('chat')
  const [agents, setAgents] = useState([])
  const [health, setHealth] = useState(null)
  const [theme, setTheme] = useState('dark')

  const loadAgents = useCallback(() => {
    api.agents().then((d) => setAgents(d.personas || [])).catch(() => setAgents([]))
  }, [])
  const loadHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])

  useEffect(() => { loadAgents(); loadHealth() }, [loadAgents, loadHealth])
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])

  const groups = [...new Set(VIEWS.map((v) => v.group))]
  const online = health?.status === 'ok'

  return (
    <div className="app">
      <aside className="side">
        <p className="brand">Libra Assist<small>console</small></p>
        {groups.map((g) => (
          <div key={g}>
            <div className="nav-group">{g}</div>
            {VIEWS.filter((v) => v.group === g).map((v) => (
              <button key={v.id} className={`nav-item ${view === v.id ? 'active' : ''}`} onClick={() => setView(v.id)}>
                <span className="dot" />{v.label}
              </button>
            ))}
          </div>
        ))}
        <div className="side-foot">
          <div style={{ display: 'flex', alignItems: 'center', gap: '.4rem', marginBottom: '.5rem' }}>
            <span className="dot" style={{ width: 7, height: 7, borderRadius: '50%',
              background: online ? 'var(--c-cyan)' : 'var(--c-crimson)', display: 'inline-block' }} />
            {online ? `${health.llm.provider} · ${health.llm.model}` : 'backend offline'}
          </div>
          <button className="btn btn-outline btn-sm" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            ◐ {theme === 'dark' ? 'light' : 'dark'}
          </button>
        </div>
      </aside>

      <main className="main">
        {view === 'chat' && <Chat agents={agents} />}
        {view === 'knowledge' && <Knowledge />}
        {view === 'search' && <Search />}
        {view === 'agents' && <Agents agents={agents} reload={loadAgents} />}
        {view === 'tools' && <Tools />}
        {view === 'status' && <Status health={health} reload={loadHealth} />}
      </main>
    </div>
  )
}
