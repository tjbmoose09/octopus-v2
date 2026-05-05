import { useState, useEffect } from 'react'
import { Brain, Loader2, Wrench, GitBranch, Database, ChevronRight, X, Circle } from 'lucide-react'

const ROLE_COLORS = {
  orchestrator: { bg: 'bg-purple-500/10', text: 'text-purple-400', dot: 'bg-purple-500', border: 'border-purple-500/30' },
  pm: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', dot: 'bg-cyan-500', border: 'border-cyan-500/30' },
  dev: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-500', border: 'border-emerald-500/30' },
  qa: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', dot: 'bg-yellow-500', border: 'border-yellow-500/30' },
  critic: { bg: 'bg-red-500/10', text: 'text-red-400', dot: 'bg-red-500', border: 'border-red-500/30' },
  review: { bg: 'bg-orange-500/10', text: 'text-orange-400', dot: 'bg-orange-500', border: 'border-orange-500/30' },
  devops: { bg: 'bg-violet-500/10', text: 'text-violet-400', dot: 'bg-violet-500', border: 'border-violet-500/30' },
  automation: { bg: 'bg-teal-500/10', text: 'text-teal-400', dot: 'bg-teal-500', border: 'border-teal-500/30' },
  research: { bg: 'bg-blue-500/10', text: 'text-blue-400', dot: 'bg-blue-500', border: 'border-blue-500/30' },
}

const DEFAULT_COLOR = { bg: 'bg-zinc-500/10', text: 'text-zinc-400', dot: 'bg-zinc-500', border: 'border-zinc-500/30' }

export default function Agents() {
  const [agents, setAgents] = useState([])
  const [selected, setSelected] = useState(null)
  const [agentInfo, setAgentInfo] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/agents').then(r => r.json()).then(data => {
      setAgents(data.agents || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const selectAgent = async (role) => {
    if (selected === role) {
      setSelected(null)
      setAgentInfo(null)
      return
    }
    setSelected(role)
    try {
      const res = await fetch(`/api/agent/${role}/info`)
      setAgentInfo(await res.json())
    } catch { setAgentInfo(null) }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <Loader2 className="animate-spin text-zinc-600" size={24} />
    </div>
  )

  return (
    <div className="flex h-full">
      {/* Agent list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
              <Brain size={16} className="text-zinc-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-zinc-100">Agents</h1>
              <p className="text-xs text-zinc-600">{agents.length} specialized agents available</p>
            </div>
          </div>

          {/* Agent grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {agents.map(agent => {
              const colors = ROLE_COLORS[agent.role] || DEFAULT_COLOR
              const isSelected = selected === agent.role
              return (
                <button
                  key={agent.role}
                  onClick={() => selectAgent(agent.role)}
                  className={`text-left p-4 rounded-xl border transition-all duration-150 ${
                    isSelected
                      ? `${colors.border} bg-[#1a1a1e] shadow-lg`
                      : 'border-[#1e1e22] bg-[#141416] hover:border-[#2a2a2e] hover:bg-[#1a1a1e]'
                  }`}
                >
                  <div className="flex items-center gap-3 mb-2.5">
                    <span className="text-xl">{agent.emoji}</span>
                    <div className="flex-1 min-w-0">
                      <span className="font-medium text-sm text-zinc-200 block">{agent.name}</span>
                      <span className="text-[10px] text-zinc-600">{agent.role}</span>
                    </div>
                    <ChevronRight size={14} className={`text-zinc-600 transition-transform ${isSelected ? 'rotate-90' : ''}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-1.5 h-1.5 rounded-full ${
                        agent.status === 'active' ? 'bg-emerald-500' :
                        agent.status === 'busy' ? 'bg-yellow-500' : 'bg-zinc-600'
                      }`} />
                      <span className="text-[11px] text-zinc-500">{agent.status || 'idle'}</span>
                    </div>
                    <span className="text-[10px] text-zinc-700 ml-auto truncate max-w-[120px]">{agent.model || 'unassigned'}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Detail panel - slides in */}
      {agentInfo && (
        <div className="w-80 border-l border-[#1e1e22] bg-[#141416] overflow-y-auto scrollbar-thin">
          <div className="p-4">
            {/* Panel header */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-semibold text-sm text-zinc-200 capitalize">{agentInfo.role}</h2>
              <button
                onClick={() => { setSelected(null); setAgentInfo(null) }}
                className="w-6 h-6 flex items-center justify-center rounded-lg hover:bg-[#1e1e22] text-zinc-500 transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            <div className="space-y-5">
              {/* Skills */}
              <div>
                <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mb-2 uppercase tracking-wider font-medium">
                  <Wrench size={11} /> Skills
                </div>
                <div className="space-y-1">
                  {agentInfo.skills?.map(s => (
                    <div key={s.name} className="bg-[#1a1a1e] rounded-lg px-3 py-2 border border-[#2a2a2e]">
                      <span className="text-xs text-zinc-300">{s.display_name}</span>
                      <span className="text-[10px] text-zinc-600 ml-1.5">({s.category})</span>
                    </div>
                  ))}
                  {(!agentInfo.skills || agentInfo.skills.length === 0) && (
                    <p className="text-xs text-zinc-600">No skills assigned</p>
                  )}
                </div>
              </div>

              {/* MCP Servers */}
              <div>
                <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mb-2 uppercase tracking-wider font-medium">
                  <GitBranch size={11} /> MCP Servers
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {agentInfo.mcp_servers?.map(s => (
                    <span key={s.name} className={`text-[11px] px-2 py-1 rounded-lg ${
                      s.enabled
                        ? 'bg-[#1a1a1e] text-zinc-300 border border-[#2a2a2e]'
                        : 'bg-[#111113] text-zinc-600 border border-[#1e1e22]'
                    }`}>
                      {s.name}
                    </span>
                  ))}
                  {(!agentInfo.mcp_servers || agentInfo.mcp_servers.length === 0) && (
                    <p className="text-xs text-zinc-600">No servers</p>
                  )}
                </div>
              </div>

              {/* Memory */}
              <div>
                <div className="flex items-center gap-1.5 text-[11px] text-zinc-500 mb-2 uppercase tracking-wider font-medium">
                  <Database size={11} /> Memory Access
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {agentInfo.memory_access?.map(m => (
                    <span key={m} className="text-[11px] bg-[#1a1a1e] text-zinc-400 px-2 py-1 rounded-lg border border-[#2a2a2e]">{m}</span>
                  ))}
                  {(!agentInfo.memory_access || agentInfo.memory_access.length === 0) && (
                    <p className="text-xs text-zinc-600">No memory access</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
