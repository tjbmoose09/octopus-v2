import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, Bot, User, Sparkles, ArrowUp } from 'lucide-react'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
    }
  }, [input])

  const sendMessage = async () => {
    if (!input.trim() || loading) return
    const userMsg = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })

      // Guard against empty or non-JSON responses
      const text = await res.text()
      if (!text) {
        throw new Error(`Server returned empty response (HTTP ${res.status})`)
      }

      let data
      try {
        data = JSON.parse(text)
      } catch {
        throw new Error(`Server returned invalid JSON (HTTP ${res.status}): ${text.slice(0, 200)}`)
      }

      // orchestrate() returns { orchestrator_response, response, content, task_id }
      // send_to_agent() returns { response, content, agent, task_id }
      const content = data.response
        || data.orchestrator_response
        || data.content
        || data.error
        || (data.results && data.results.length > 0
          ? data.results.map(r => r.content || r.error || '').filter(Boolean).join('\n\n---\n\n')
          : null)
        || 'No response'
      setMessages(prev => [...prev, {
        role: data.error ? 'error' : 'assistant',
        content,
        agent: data.agent || 'orchestrator',
        task_id: data.task_id
      }])
    } catch (err) {
      let errorMsg = err.message
      if (err.message.includes('502')) {
        errorMsg = 'Backend not reachable (HTTP 502). Make sure the server is running: python api/main.py'
      } else if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        errorMsg = 'Cannot connect to server. Make sure the backend is running on port 8080.'
      }
      setMessages(prev => [...prev, { role: 'error', content: `Error: ${errorMsg}` }])
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const AGENT_COLORS = {
    orchestrator: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20' },
    pm: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20' },
    dev: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
    qa: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/20' },
    critic: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
    review: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/20' },
    devops: { bg: 'bg-violet-500/10', text: 'text-violet-400', border: 'border-violet-500/20' },
    automation: { bg: 'bg-teal-500/10', text: 'text-teal-400', border: 'border-teal-500/20' },
    research: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20' },
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {messages.length === 0 ? (
          /* Empty state - centered like Claude */
          <div className="flex flex-col items-center justify-center h-full px-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#e8564a] to-[#d44030] flex items-center justify-center mb-6 shadow-xl shadow-[#e8564a]/10">
              <Sparkles size={28} className="text-white" />
            </div>
            <h1 className="text-2xl font-semibold text-zinc-100 mb-2">Octopus V2</h1>
            <p className="text-sm text-zinc-500 text-center max-w-md mb-8">
              Your tasks are decomposed and delegated to specialized agents. Describe what you want to build.
            </p>
            <div className="grid grid-cols-2 gap-2 max-w-lg w-full">
              {[
                'Build a REST API with authentication',
                'Create a React dashboard component',
                'Set up CI/CD pipeline with Docker',
                'Write unit tests for the payment module'
              ].map((suggestion, i) => (
                <button
                  key={i}
                  onClick={() => setInput(suggestion)}
                  className="text-left px-4 py-3 rounded-xl bg-[#1a1a1e] border border-[#2a2a2e] hover:border-[#3a3a3e] hover:bg-[#1e1e22] text-sm text-zinc-400 hover:text-zinc-300 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Message thread */
          <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
            {messages.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === 'user' ? '' : ''}`}>
                {/* Avatar */}
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  msg.role === 'user'
                    ? 'bg-[#2a2a2e]'
                    : msg.role === 'error'
                    ? 'bg-red-500/10'
                    : 'bg-gradient-to-br from-[#e8564a] to-[#d44030]'
                }`}>
                  {msg.role === 'user' ? (
                    <User size={14} className="text-zinc-400" />
                  ) : (
                    <Bot size={14} className={msg.role === 'error' ? 'text-red-400' : 'text-white'} />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-zinc-300">
                      {msg.role === 'user' ? 'You' : msg.role === 'error' ? 'Error' : 'Octopus'}
                    </span>
                    {msg.agent && msg.agent !== 'orchestrator' && (
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-md ${
                        (AGENT_COLORS[msg.agent] || AGENT_COLORS.orchestrator).bg
                      } ${(AGENT_COLORS[msg.agent] || AGENT_COLORS.orchestrator).text}`}>
                        {msg.agent}
                      </span>
                    )}
                  </div>
                  <div className={`text-sm leading-relaxed whitespace-pre-wrap ${
                    msg.role === 'error' ? 'text-red-400' : 'text-zinc-300'
                  }`}>
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[#e8564a] to-[#d44030] flex items-center justify-center">
                  <Loader2 size={14} className="animate-spin text-white" />
                </div>
                <div className="flex-1">
                  <span className="text-sm font-medium text-zinc-300 block mb-1">Octopus</span>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse" />
                    <div className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse" style={{ animationDelay: '0.2s' }} />
                    <div className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse" style={{ animationDelay: '0.4s' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area - centered, with rounded container like Claude */}
      <div className="px-6 py-4">
        <div className="max-w-3xl mx-auto">
          <div className="relative bg-[#1a1a1e] rounded-2xl border border-[#2a2a2e] focus-within:border-[#3a3a3e] transition-colors shadow-lg">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  sendMessage()
                }
              }}
              placeholder="Describe what you want to build..."
              rows={1}
              className="w-full bg-transparent rounded-2xl pl-4 pr-14 py-3.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none resize-none scrollbar-thin"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="absolute right-2.5 bottom-2.5 w-8 h-8 flex items-center justify-center bg-[#e8564a] hover:bg-[#d44030] disabled:bg-[#2a2a2e] disabled:text-zinc-600 rounded-lg transition-all text-white"
            >
              <ArrowUp size={16} />
            </button>
          </div>
          <p className="text-[10px] text-zinc-600 text-center mt-2">
            Tasks are decomposed and delegated to specialized agents automatically
          </p>
        </div>
      </div>
    </div>
  )
}
