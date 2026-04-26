import { useState, useEffect, useRef, useCallback } from 'react'
import { RefreshCw, Play, Pause, Wifi, WifiOff, Terminal as TerminalIcon } from 'lucide-react'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

interface LogViewerProps {
  containerId: string;
}

function LogViewer({ containerId }: LogViewerProps) {
  const { socket } = useAuth()
  const [loading, setLoading] = useState<boolean>(false)
  const [liveMode, setLiveMode] = useState<boolean>(false)
  const [isConnected, setIsConnected] = useState<boolean>(false)
  const [lines, setLines] = useState<number>(100)
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!terminalRef.current) return

    const term = new Terminal({
      theme: {
        background: '#111827', // gray-900
        foreground: '#10B981', // green-400
      },
      fontSize: 12,
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
      convertEol: true,
      scrollback: 10000,
      disableStdin: true
    })

    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    term.open(terminalRef.current)
    fitAddon.fit()

    xtermRef.current = term
    fitAddonRef.current = fitAddon

    const handleResize = () => fitAddon.fit()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      term.dispose()
    }
  }, [])

  const fetchInitialLogs = useCallback(async () => {
    if (!xtermRef.current) return
    setLoading(true)
    xtermRef.current.clear()
    try {
      const data = await api.getContainerLogs(containerId, lines)
      if (data.logs) {
        xtermRef.current.write(data.logs)
      }
    } catch (err) {
      xtermRef.current.write('\r\n\x1b[31mFailed to fetch logs\x1b[0m\r\n')
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

    const token = localStorage.getItem('token')
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/logs/${containerId}?token=${token}`

    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setIsConnected(true)
    ws.onmessage = (event) => {
      if (xtermRef.current) {
        xtermRef.current.write(event.data)
      }
    }
    ws.onerror = () => setIsConnected(false)
    ws.onclose = () => setIsConnected(false)

    return () => ws.close()
  }, [liveMode, containerId])

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
        ref={terminalRef}
        className="bg-gray-900 rounded p-2 h-96 overflow-hidden"
      >
        {loading && <div className="text-gray-400 absolute p-2">Loading logs...</div>}
      </div>
    </div>
  )
}

export default LogViewer