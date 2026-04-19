import { useState, useEffect, useRef, useCallback } from 'react'
import { RefreshCw, Play, Pause, Wifi, WifiOff } from 'lucide-react'
import { useAuth } from '@/App'

interface LogViewerProps {
  containerId: string;
}

function LogViewer({ containerId }: LogViewerProps) {
  const { socket } = useAuth()
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState<boolean>(false)
  const [liveMode, setLiveMode] = useState<boolean>(false)
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [lines, setLines] = useState<number>(100)
  const wsRef = useRef<WebSocket | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const isUserScrollingRef = useRef<boolean>(false)
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const maxBuffer = 10000

  const fetchInitialLogs = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/containers/${containerId}/logs?lines=${lines}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
      })
      const data = await res.json()
      if (data.logs) {
        const logLines = data.logs.split('\n').filter((l: string) => l)
        setLogs(logLines.slice(-maxBuffer))
      }
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    } finally {
      setLoading(false)
    }
  }, [containerId, lines])

  useEffect(() => {
    fetchInitialLogs()
  }, [fetchInitialLogs])

  useEffect(() => {
    if (!liveMode) {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      setIsConnected(false)
      return
    }

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs/${containerId}`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      setLogs(prev => {
        const newLogs = [...prev, event.data]
        if (newLogs.length > maxBuffer) {
          return newLogs.slice(-maxBuffer)
        }
        return newLogs
      })
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    return () => {
      ws.close()
    }
  }, [liveMode, containerId])

  useEffect(() => {
    if (!isUserScrollingRef.current && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'auto' })
    }
  }, [logs])

  const handleScroll = () => {
    if (!containerRef.current) return
    
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50
    
    if (!isAtBottom && liveMode) {
      isUserScrollingRef.current = true
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
      scrollTimeoutRef.current = setTimeout(() => {
        isUserScrollingRef.current = false
      }, 1000)
    }
  }

  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current)
      }
    }
  }, [])

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <select
            value={lines}
            onChange={(e) => setLines(Number(e.target.value))}
            className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-3 py-1"
          >
            <option value={50}>50 lines</option>
            <option value={100}>100 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
          </select>
          <button
            onClick={() => setLiveMode(!liveMode)}
            className={`flex items-center gap-2 px-3 py-1 rounded text-sm ${
              liveMode ? 'bg-green-600 hover:bg-green-500' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {liveMode ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            {liveMode ? 'Live' : 'Static'}
          </button>
          {liveMode && (
            <span className={`flex items-center gap-1 text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          )}
        </div>
        <button
          onClick={fetchInitialLogs}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div 
        ref={containerRef}
        onScroll={handleScroll}
        className="bg-gray-900 rounded p-4 h-96 overflow-auto font-mono text-sm"
      >
        {loading && logs.length === 0 ? (
          <div className="text-gray-400">Loading logs...</div>
        ) : logs.length > 0 ? (
          <pre className="text-green-400 whitespace-pre-wrap">{logs.join('\n')}</pre>
        ) : (
          <div className="text-gray-400">No logs available</div>
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}

export default LogViewer