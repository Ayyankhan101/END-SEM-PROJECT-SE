import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { ArrowLeft, Terminal as TerminalIcon } from 'lucide-react'
import '@xterm/xterm/css/xterm.css'

function TerminalPage() {
  const { id } = useParams<{ id: string }>()
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<Terminal | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!terminalRef.current || !id) return

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1f2937',
        foreground: '#e5e7eb',
        cursor: '#e5e7eb'
      }
    })
    
    const fitAddon = new FitAddon()
    term.loadAddon(fitAddon)
    
    term.open(terminalRef.current)
    fitAddon.fit()
    
    xtermRef.current = term
    fitAddonRef.current = fitAddon

    const token = localStorage.getItem('token')
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/exec/${id}?token=${token}`
    
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
      term.writeln('\x1b[32mConnected to container terminal\x1b[0m')
      term.writeln('')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.error) {
          term.writeln(`\x1b[31mError: ${data.error}\x1b[0m`)
          setError(data.error)
        }
      } catch {
        term.write(event.data)
      }
    }

    ws.onerror = (e) => {
      console.error('WebSocket error:', e)
      setError('Connection failed')
    }

    ws.onclose = () => {
      setIsConnected(false)
      term.writeln('\x1b[33mDisconnected\x1b[0m')
    }

    term.onData((data) => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(data)
      }
    })

    const handleResize = () => {
      fitAddon.fit()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      ws.close()
      term.dispose()
    }
  }, [id])

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to={`/container/${id}`} className="p-2 hover:bg-gray-700 rounded">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <TerminalIcon className="w-6 h-6 text-green-500" />
            <h1 className="text-xl font-bold">Terminal - {id?.substring(0, 12)}</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <span className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${
              isConnected 
                ? 'bg-green-900/50 text-green-400' 
                : 'bg-red-900/50 text-red-400'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            {error && (
              <span className="text-red-400 text-sm">{error}</span>
            )}
          </div>
        </div>
      </header>

      <div className="p-4 h-[calc(100vh-73px)]">
        <div ref={terminalRef} className="h-full w-full" />
      </div>
    </div>
  )
}

export default TerminalPage