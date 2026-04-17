import { useState, useEffect, useRef, useCallback } from 'react'
import { RefreshCw, Play, Pause } from 'lucide-react'
import { api } from '@/services/api'

interface LogViewerProps {
  containerId: string;
}

function LogViewer({ containerId }: LogViewerProps) {
  const [logs, setLogs] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [autoRefresh, setAutoRefresh] = useState<boolean>(false)
  const [lines, setLines] = useState<number>(100)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getContainerLogs(containerId, lines)
      setLogs(data.logs || '')
    } catch (err) {
      console.error('Failed to fetch logs:', err)
    } finally {
      setLoading(false)
    }
  }, [containerId, lines])

  useEffect(() => {
    fetchLogs()
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [fetchLogs])

  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchLogs, 3000)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [autoRefresh, fetchLogs])

  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs])

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
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-2 px-3 py-1 rounded text-sm ${
              autoRefresh ? 'bg-green-600 hover:bg-green-500' : 'bg-gray-700 hover:bg-gray-600'
            }`}
          >
            {autoRefresh ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
          </button>
        </div>
        <button
          onClick={fetchLogs}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="bg-gray-900 rounded p-4 h-96 overflow-auto font-mono text-sm">
        {loading && !logs ? (
          <div className="text-gray-400">Loading logs...</div>
        ) : logs ? (
          <pre className="text-green-400 whitespace-pre-wrap">{logs}</pre>
        ) : (
          <div className="text-gray-400">No logs available</div>
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}

export default LogViewer