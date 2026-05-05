import { useState, useEffect } from 'react'
import { Cpu, HardDrive, Activity, Wifi, WifiOff, RefreshCw } from 'lucide-react'

function MetricCard({ icon: Icon, label, value, subValue, color = 'text-zinc-100' }) {
  return (
    <div className="bg-[#141416] rounded-xl p-4 border border-[#1e1e22]">
      <div className="flex items-center gap-2 text-[11px] text-zinc-500 mb-3 uppercase tracking-wider font-medium">
        <Icon size={12} /> {label}
      </div>
      <div className={`text-3xl font-semibold tracking-tight ${color}`}>{value}</div>
      {subValue && <div className="text-xs text-zinc-600 mt-1">{subValue}</div>}
    </div>
  )
}

function ProgressBar({ value, max, color = 'bg-[#e8564a]' }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="w-full h-1.5 bg-[#1e1e22] rounded-full overflow-hidden mt-2">
      <div
        className={`h-full rounded-full transition-all duration-500 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

export default function SystemStatus() {
  const [system, setSystem] = useState(null)
  const [providers, setProviders] = useState(null)

  const fetchData = () => {
    fetch('/api/system').then(r => r.json()).then(setSystem).catch(() => {})
    fetch('/api/providers').then(r => r.json()).then(setProviders).catch(() => {})
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  const cpuColor = system?.cpu_percent > 80 ? 'text-red-400' : system?.cpu_percent > 50 ? 'text-yellow-400' : 'text-emerald-400'
  const ramPct = system ? (system.ram_used_gb / system.ram_total_gb) * 100 : 0
  const ramColor = ramPct > 80 ? 'text-red-400' : ramPct > 50 ? 'text-yellow-400' : 'text-emerald-400'

  return (
    <div className="h-full overflow-y-auto scrollbar-thin">
      <div className="p-6 max-w-4xl">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] flex items-center justify-center">
            <Cpu size={16} className="text-zinc-400" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-zinc-100">System</h1>
            <p className="text-xs text-zinc-600">Real-time resource monitoring</p>
          </div>
        </div>

        {/* Metrics grid */}
        {system && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            <div className="bg-[#141416] rounded-xl p-4 border border-[#1e1e22]">
              <div className="flex items-center gap-2 text-[11px] text-zinc-500 mb-3 uppercase tracking-wider font-medium">
                <Cpu size={12} /> CPU
              </div>
              <div className={`text-3xl font-semibold tracking-tight ${cpuColor}`}>{system.cpu_percent || 0}%</div>
              <ProgressBar
                value={system.cpu_percent || 0}
                max={100}
                color={system.cpu_percent > 80 ? 'bg-red-500' : system.cpu_percent > 50 ? 'bg-yellow-500' : 'bg-emerald-500'}
              />
            </div>

            <div className="bg-[#141416] rounded-xl p-4 border border-[#1e1e22]">
              <div className="flex items-center gap-2 text-[11px] text-zinc-500 mb-3 uppercase tracking-wider font-medium">
                <HardDrive size={12} /> RAM
              </div>
              <div className={`text-3xl font-semibold tracking-tight ${ramColor}`}>{system.ram_used_gb || 0} <span className="text-lg text-zinc-600">GB</span></div>
              <div className="text-xs text-zinc-600 mt-0.5">of {system.ram_total_gb || 0} GB</div>
              <ProgressBar
                value={system.ram_used_gb || 0}
                max={system.ram_total_gb || 1}
                color={ramPct > 80 ? 'bg-red-500' : ramPct > 50 ? 'bg-yellow-500' : 'bg-emerald-500'}
              />
            </div>

            <div className="bg-[#141416] rounded-xl p-4 border border-[#1e1e22]">
              <div className="flex items-center gap-2 text-[11px] text-zinc-500 mb-3 uppercase tracking-wider font-medium">
                <Activity size={12} /> GPU
              </div>
              <div className="text-3xl font-semibold tracking-tight text-zinc-100">{system.gpu_usage || 'N/A'}</div>
              {system.gpu_name && <div className="text-xs text-zinc-600 mt-1">{system.gpu_name}</div>}
            </div>
          </div>
        )}

        {/* Providers */}
        {providers && (
          <div>
            <div className="flex items-center gap-2 mb-3">
              <h2 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Providers</h2>
              <span className="text-[10px] text-zinc-700 bg-[#1a1a1e] px-1.5 py-0.5 rounded">{Object.keys(providers).length}</span>
            </div>
            <div className="space-y-2">
              {Object.entries(providers).map(([name, info]) => (
                <div key={name} className="bg-[#141416] rounded-xl px-4 py-3 border border-[#1e1e22] flex items-center gap-3 hover:border-[#2a2a2e] transition-colors">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    info.healthy ? 'bg-emerald-500/10' : 'bg-red-500/10'
                  }`}>
                    {info.healthy ? (
                      <Wifi size={14} className="text-emerald-400" />
                    ) : (
                      <WifiOff size={14} className="text-red-400" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium text-zinc-200 block">{name}</span>
                    <span className="text-[11px] text-zinc-600 truncate block">{info.model || info.default_model || 'No model assigned'}</span>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-lg ${
                    info.healthy
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-red-500/10 text-red-400'
                  }`}>
                    {info.healthy ? 'Healthy' : 'Offline'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
