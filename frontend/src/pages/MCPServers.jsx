import { useState, useEffect } from 'react'
import { GitBranch, CheckCircle, XCircle, Lock, Wifi, Loader2 } from 'lucide-react'

export default function MCPServers() {
  const [servers, setServers] = useState({})
  const [routing, setRouting] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/mcp/servers').then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      }),
      fetch('/api/mcp/routing').then(r => r.ok ? r.json() : {}).catch(() => ({}))
    ])
      .then(([serversData, routingData]) => {
        // Validate servers is an object with arrays
        if (serversData && typeof serversData === 'object' && !Array.isArray(serversData)) {
          setServers(serversData)
        } else {
          setServers({})
        }
        setRouting(routingData || {})
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load MCP servers:', err)
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) return (
    <div className="flex items-center justify-center h-full">
      <Loader2 className="animate-spin text-zinc-600" size={24} />
    </div>
  )

  if (error) return (
    <div className="flex flex-col items-center justify-center h-full text-center px-6">
      <GitBranch size={32} className="text-zinc-800 mb-3" />
      <p className="text-sm text-red-400 mb-1">Failed to load MCP servers</p>
      <p className="text-xs text-zinc-600">{error}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 text-xs bg-[#1a1a1e] border border-[#2a2a2e] rounded-lg hover:bg-[#222226] text-zinc-300 transition-colors"
      >
        Retry
      </button>
    </div>
  )

  const entries = Object.entries(servers)
  const totalServers = entries.reduce((sum, [, arr]) => sum + (Array.isArray(arr) ? arr.length : 0), 0)
  const enabledCount = entries.reduce((sum, [, arr]) => sum + (Array.isArray(arr) ? arr.filter(s => s.enabled).length : 0), 0)

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-6 max-w-5xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
            <GitBranch size={16} className="text-zinc-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">MCP Servers</h1>
            <p className="text-xs text-zinc-600">{enabledCount} of {totalServers} enabled</p>
          </div>
        </div>

        {/* Server categories */}
        <div className="space-y-6">
          {entries.map(([category, catServers]) => {
            if (!Array.isArray(catServers)) return null
            return (
              <div key={category}>
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{category}</h2>
                  <span className="text-[10px] text-zinc-700 bg-[#1a1a1e] px-1.5 py-0.5 rounded">{catServers.length}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {catServers.map((server, idx) => (
                    <div
                      key={server.name || idx}
                      className={`bg-[#141416] rounded-xl p-3.5 border transition-colors ${
                        server.enabled
                          ? 'border-[#1e1e22] hover:border-[#2a2a2e]'
                          : 'border-[#1a1a1e] opacity-60'
                      }`}
                    >
                      <div className="flex items-center gap-2.5 mb-2">
                        {server.enabled ? (
                          <CheckCircle size={14} className="text-emerald-500 flex-shrink-0" />
                        ) : (
                          <XCircle size={14} className="text-zinc-600 flex-shrink-0" />
                        )}
                        <span className="text-sm font-medium text-zinc-200 truncate">{server.name || 'Unknown'}</span>
                      </div>
                      <p className="text-xs text-zinc-500 mb-2.5 line-clamp-2">{server.description || ''}</p>
                      <div className="flex items-center gap-1.5">
                        {server.transport && (
                          <span className="flex items-center gap-1 text-[10px] bg-[#1a1a1e] text-zinc-500 px-1.5 py-0.5 rounded-md border border-[#2a2a2e]">
                            <Wifi size={8} /> {server.transport}
                          </span>
                        )}
                        {server.requires_auth && (
                          <span className="flex items-center gap-1 text-[10px] bg-amber-500/10 text-amber-400 px-1.5 py-0.5 rounded-md">
                            <Lock size={8} /> auth
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
          {entries.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <GitBranch size={32} className="text-zinc-800 mb-3" />
              <p className="text-sm text-zinc-600">No MCP servers configured</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
