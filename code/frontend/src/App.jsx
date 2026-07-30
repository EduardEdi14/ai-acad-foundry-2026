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
  const [hostedOnly, setHostedOnly] = useState([])
  const [foundry, setFoundry] = useState(null)
  const [health, setHealth] = useState(null)
  const [azure, setAzure] = useState(null)
  const [theme, setTheme] = useState('dark')

  const loadAgents = useCallback(() => {
    api.agents()
      .then((d) => { setAgents(d.personas || []); setHostedOnly(d.hosted_only || []); setFoundry(d.foundry) })
      .catch(() => { setAgents([]); setHostedOnly([]); setFoundry(null) })
  }, [])
  const loadHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => setHealth(null))
  }, [])
  const loadAzure = useCallback(() => {
    api.azure().then(setAzure).catch(() => setAzure(null))
  }, [])

  useEffect(() => { loadAgents(); loadHealth(); loadAzure() }, [loadAgents, loadHealth, loadAzure])
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])

  const groups = [...new Set(VIEWS.map((v) => v.group))]
  const online = health?.status === 'ok'

  return (
    <div className="app">
      <aside className="side">
        <p className="brand">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2 4 5v6c0 5 3.4 8.7 8 10 4.6-1.3 8-5 8-10V5z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
          </span>
          <span className="brand-text">edi-libra<small>console</small></span>
        </p>
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
          <div className="profile-card">
            <div className="profile-row">
              <span className={`status-dot ${online ? 'online' : 'offline'}`} />
              {online ? `${health.llm.provider} · ${health.llm.model}` : 'backend offline'}
            </div>
            {azure?.configured && (
              <div className="profile-badges">
                <span className={`badge ${azure.auth === 'identity' ? '' : 'gold'}`}
                      title={azure.auth === 'identity'
                        ? 'Signed in with Microsoft Entra — the Agent Service and control plane are available'
                        : 'Key authentication — the Agent Service and control plane cannot be queried'}>
                  {azure.auth === 'identity' ? 'Entra identity' : 'key auth'}
                </span>
              </div>
            )}
            <button className="btn btn-outline btn-sm" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
              ◐ {theme === 'dark' ? 'light' : 'dark'}
            </button>
          </div>
        </div>
      </aside>

      <main className="main">
        {view === 'chat' && <Chat agents={agents} hostedOnly={hostedOnly} foundry={foundry} />}
        {view === 'knowledge' && <Knowledge />}
        {view === 'search' && <Search />}
        {view === 'agents' && <Agents agents={agents} hostedOnly={hostedOnly} foundry={foundry}
                                      reload={loadAgents} azure={azure} />}
        {view === 'tools' && <Tools />}
        {view === 'status' && <Status health={health} reload={loadHealth}
                                      azure={azure} reloadAzure={loadAzure} />}
      </main>
    </div>
  )
}
