import { useState, useEffect } from 'react'
import { Zap, ArrowRight, RefreshCw, CheckCircle, XCircle, MessageCircle, GitCommit } from 'lucide-react'

const TYPE_CONFIG = {
  assign: { color: 'text-blue-400', bg: 'bg-blue-500/10', icon: GitCommit, label: 'Assigned' },
  complete: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', icon: CheckCircle, label: 'Completed' },
  fail: { color: 'text-red-400', bg: 'bg-red-500/10', icon: XCircle, label: 'Failed' },
  message: { color: 'text-zinc-400', bg: 'bg-zinc-500/10', icon: MessageCircle, label: 'Message' },
}

export default function Pipeline() {
  const [events, setEvents] = useState([])
  const [refreshing, setRefreshing] = useState(false)

  const fetchEvents = () => {
    fetch('/api/pipeline').then(r => r.json()).then(data => setEvents(data.events || []))
  }

  useEffect(() => {
    fetchEvents()
    const interval = setInterval(fetchEvents, 3000)
    return () => clearInterval(interval)
  }, [])

  const refresh = () => {
    setRefreshing(true)
    fetchEvents()
    setTimeout(() => setRefreshing(false), 500)
  }

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
              <Zap size={16} className="text-zinc-400" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-zinc-100">Pipeline</h1>
              <p className="text-xs text-zinc-600">{events.length} events</p>
            </div>
          </div>
          <button
            onClick={refresh}
            className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-[#1a1a1e] text-zinc-500 transition-colors"
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Timeline */}
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <Zap size={32} className="text-zinc-800 mb-3" />
            <p className="text-sm text-zinc-600">No pipeline events yet</p>
            <p className="text-xs text-zinc-700 mt-1">Events appear here as agents process tasks</p>
          </div>
        ) : (
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[15px] top-0 bottom-0 w-px bg-[#1e1e22]" />

            <div className="space-y-1">
              {events.map((evt, i) => {
                const config = TYPE_CONFIG[evt.event_type] || TYPE_CONFIG.message
                const Icon = config.icon
                return (
                  <div key={i} className="relative flex items-start gap-4 py-2.5 pl-0">
                    {/* Timeline dot */}
                    <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center flex-shrink-0 z-10 border border-[#1e1e22]`}>
                      <Icon size={14} className={config.color} />
                    </div>

                    {/* Content */}
                    <div className="flex-1 bg-[#141416] rounded-xl px-4 py-3 border border-[#1e1e22] hover:border-[#2a2a2e] transition-colors min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-zinc-300">{evt.from_agent}</span>
                        <ArrowRight size={12} className="text-zinc-700" />
                        <span className="text-sm font-medium text-zinc-200">{evt.to_agent}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-md ml-auto ${config.bg} ${config.color}`}>
                          {config.label}
                        </span>
                      </div>
                      {evt.message && (
                        <p className="text-xs text-zinc-500 mt-1.5 truncate">{evt.message}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
