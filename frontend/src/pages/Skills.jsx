import { useState, useEffect } from 'react'
import { Wrench, Search, Zap, Loader2 } from 'lucide-react'

export default function Skills() {
  const [skills, setSkills] = useState({})
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/skills')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => {
        // API returns { role: [...skills] } — validate it's an object with arrays
        if (data && typeof data === 'object' && !Array.isArray(data)) {
          setSkills(data)
        } else {
          setSkills({})
        }
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to load skills:', err)
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
      <Wrench size={32} className="text-zinc-800 mb-3" />
      <p className="text-sm text-red-400 mb-1">Failed to load skills</p>
      <p className="text-xs text-zinc-600">{error}</p>
      <button
        onClick={() => window.location.reload()}
        className="mt-4 px-4 py-2 text-xs bg-[#1a1a1e] border border-[#2a2a2e] rounded-lg hover:bg-[#222226] text-zinc-300 transition-colors"
      >
        Retry
      </button>
    </div>
  )

  const entries = Object.entries(skills)
  const totalSkills = entries.reduce((sum, [, arr]) => sum + (Array.isArray(arr) ? arr.length : 0), 0)

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-6 max-w-5xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
              <Wrench size={16} className="text-zinc-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-zinc-100">Skills</h1>
              <p className="text-xs text-zinc-600">{totalSkills} skills across {entries.length} roles</p>
            </div>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-600" />
            <input
              value={filter}
              onChange={e => setFilter(e.target.value)}
              placeholder="Filter skills..."
              className="bg-[#1a1a1e] rounded-lg pl-8 pr-3 py-2 text-xs text-zinc-300 placeholder-zinc-600 border border-[#2a2a2e] focus:border-[#3a3a3e] focus:outline-none w-48"
            />
          </div>
        </div>

        {/* Skills by role */}
        <div className="space-y-6">
          {entries.map(([role, roleSkills]) => {
            if (!Array.isArray(roleSkills)) return null
            const filtered = roleSkills.filter(s =>
              !filter || (s.name && s.name.includes(filter)) || (s.description && s.description.toLowerCase().includes(filter.toLowerCase()))
            )
            if (filtered.length === 0) return null
            return (
              <div key={role}>
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider capitalize">{role}</h2>
                  <span className="text-[10px] text-zinc-700 bg-[#1a1a1e] px-1.5 py-0.5 rounded">{filtered.length}</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {filtered.map((skill, idx) => (
                    <div key={skill.name || idx} className="bg-[#141416] rounded-xl p-3.5 border border-[#1e1e22] hover:border-[#2a2a2e] transition-colors">
                      <div className="flex items-center gap-2 mb-1.5">
                        <Wrench size={12} className="text-zinc-600" />
                        <span className="text-sm font-medium text-zinc-200">{skill.display_name || skill.name || 'Unknown'}</span>
                        {skill.autonomous && (
                          <span className="flex items-center gap-0.5 text-[10px] bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded-md ml-auto">
                            <Zap size={8} /> auto
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-500 line-clamp-2 mb-2">{skill.description || ''}</p>
                      <div className="flex gap-1.5 flex-wrap">
                        {skill.category && <span className="text-[10px] bg-[#1a1a1e] text-zinc-500 px-1.5 py-0.5 rounded-md border border-[#2a2a2e]">{skill.category}</span>}
                        {skill.source && <span className="text-[10px] bg-[#1a1a1e] text-zinc-600 px-1.5 py-0.5 rounded-md border border-[#2a2a2e]">{skill.source}</span>}
                        {skill.runtime && <span className="text-[10px] bg-[#1a1a1e] text-zinc-600 px-1.5 py-0.5 rounded-md border border-[#2a2a2e]">{skill.runtime}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
          {entries.length === 0 && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <Wrench size={32} className="text-zinc-800 mb-3" />
              <p className="text-sm text-zinc-600">No skills configured</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
