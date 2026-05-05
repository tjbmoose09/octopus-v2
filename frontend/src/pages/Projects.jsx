import { useState, useEffect } from 'react'
import { FolderKanban, Plus, Clock, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

const COLUMNS = ['pending', 'in_progress', 'completed', 'failed']

const COLUMN_CONFIG = {
  pending: { label: 'To Do', color: 'bg-zinc-500', icon: Clock, headerBg: 'bg-zinc-500/10', headerText: 'text-zinc-400' },
  in_progress: { label: 'In Progress', color: 'bg-blue-500', icon: Loader2, headerBg: 'bg-blue-500/10', headerText: 'text-blue-400' },
  completed: { label: 'Done', color: 'bg-emerald-500', icon: CheckCircle, headerBg: 'bg-emerald-500/10', headerText: 'text-emerald-400' },
  failed: { label: 'Failed', color: 'bg-red-500', icon: AlertCircle, headerBg: 'bg-red-500/10', headerText: 'text-red-400' },
}

export default function Projects() {
  const [tasks, setTasks] = useState([])

  useEffect(() => {
    fetch('/api/tasks').then(r => r.json()).then(data => setTasks(data.tasks || []))
  }, [])

  const grouped = COLUMNS.reduce((acc, col) => {
    acc[col] = tasks.filter(t => t.status === col)
    return acc
  }, {})

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 flex items-center gap-3">
        <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
          <FolderKanban size={16} className="text-zinc-400" />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-zinc-100">Projects</h1>
          <p className="text-xs text-zinc-600">{tasks.length} tasks tracked</p>
        </div>
      </div>

      {/* Kanban board */}
      <div className="flex-1 overflow-x-auto px-6 pb-6">
        <div className="flex gap-3 h-full min-w-[800px]">
          {COLUMNS.map(col => {
            const config = COLUMN_CONFIG[col]
            const Icon = config.icon
            const items = grouped[col] || []
            return (
              <div key={col} className="flex-1 flex flex-col min-w-[200px]">
                {/* Column header */}
                <div className="flex items-center gap-2 px-3 py-2 mb-2">
                  <div className={`w-5 h-5 rounded-md ${config.headerBg} flex items-center justify-center`}>
                    <Icon size={11} className={config.headerText} />
                  </div>
                  <span className="text-xs font-medium text-zinc-400">{config.label}</span>
                  <span className="text-[10px] text-zinc-600 bg-[#1a1a1e] px-1.5 py-0.5 rounded-md ml-auto">
                    {items.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="flex-1 overflow-y-auto space-y-2 scrollbar-thin">
                  {items.map(task => (
                    <div
                      key={task.id}
                      className="bg-[#141416] rounded-xl p-3.5 border border-[#1e1e22] hover:border-[#2a2a2e] transition-colors cursor-default"
                    >
                      <div className="text-sm text-zinc-200 mb-2 leading-snug">{task.title || task.description}</div>
                      <div className="flex items-center gap-2">
                        {task.assigned_agent && (
                          <span className="text-[10px] bg-[#1a1a1e] text-zinc-500 px-1.5 py-0.5 rounded-md border border-[#2a2a2e]">
                            {task.assigned_agent}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                  {items.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-8 text-center">
                      <p className="text-[11px] text-zinc-700">No tasks</p>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
