import { useState, useEffect } from 'react'
import { Database, Search, Loader2, ExternalLink, FileText, Tag } from 'lucide-react'

export default function Memory() {
  const [status, setStatus] = useState(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)

  useEffect(() => {
    fetch('/api/memory/status').then(r => r.json()).then(setStatus)
  }, [])

  const search = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const res = await fetch('/api/memory/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      setResults(await res.json())
    } catch { setResults({ error: 'Search failed' }) }
    setSearching(false)
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
            <Database size={16} className="text-zinc-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">Memory</h1>
            <p className="text-xs text-zinc-600">Obsidian vault knowledge base</p>
          </div>
        </div>

        {/* Status card */}
        {status && (
          <div className="bg-[#141416] rounded-xl p-4 border border-[#1e1e22] mb-6">
            <div className="flex items-center gap-3 mb-3">
              <Database size={16} className="text-zinc-500" />
              <span className="text-sm font-medium text-zinc-200">Obsidian Vault</span>
              <span className={`ml-auto text-[11px] px-2 py-0.5 rounded-lg ${
                status.status === 'connected'
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'bg-red-500/10 text-red-400'
              }`}>
                {status.status}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs mb-3">
              <div className="bg-[#1a1a1e] rounded-lg px-3 py-2 border border-[#2a2a2e]">
                <span className="text-zinc-600 block mb-0.5">URL</span>
                <span className="text-zinc-300 truncate block">{status.obsidian_url}</span>
              </div>
              <div className="bg-[#1a1a1e] rounded-lg px-3 py-2 border border-[#2a2a2e]">
                <span className="text-zinc-600 block mb-0.5">Vault</span>
                <span className="text-zinc-300 truncate block">{status.vault}</span>
              </div>
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {status.memory_types?.map(t => (
                <span key={t} className="flex items-center gap-1 text-[10px] bg-[#1a1a1e] text-zinc-400 px-2 py-1 rounded-lg border border-[#2a2a2e]">
                  <Tag size={8} /> {t}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Search */}
        <div className="mb-6">
          <div className="relative bg-[#1a1a1e] rounded-xl border border-[#2a2a2e] focus-within:border-[#3a3a3e] transition-colors">
            <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-600" />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && search()}
              placeholder="Search memory vault..."
              className="w-full bg-transparent rounded-xl pl-10 pr-20 py-3 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none"
            />
            <button
              onClick={search}
              disabled={searching || !query.trim()}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1.5 text-xs font-medium bg-[#e8564a] hover:bg-[#d44030] disabled:bg-[#2a2a2e] disabled:text-zinc-600 text-white rounded-lg transition-colors"
            >
              {searching ? <Loader2 size={14} className="animate-spin" /> : 'Search'}
            </button>
          </div>
        </div>

        {/* Results */}
        {results && (
          <div className="bg-[#141416] rounded-xl border border-[#1e1e22] overflow-hidden">
            <div className="px-4 py-3 border-b border-[#1e1e22] flex items-center gap-2">
              <FileText size={14} className="text-zinc-500" />
              <span className="text-xs font-medium text-zinc-400">Results</span>
            </div>
            <div className="p-4">
              <pre className="text-xs text-zinc-400 whitespace-pre-wrap font-mono leading-relaxed">{JSON.stringify(results, null, 2)}</pre>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
