import { useState, useEffect, createContext, useContext, useRef, useCallback } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ContainerDetail from './pages/ContainerDetail'
import ContainerCreate from './pages/ContainerCreate'
import Stacks from './pages/Stacks'
import Hosts from './pages/Hosts'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import AuditLogs from './pages/AuditLogs'
import Notifications from './pages/Notifications'
import Backup from './pages/Backup'
import DockerResources from './pages/DockerResources'
import Users from './pages/Users'
import TerminalPage from './pages/Terminal'
import AlertRules from './pages/AlertRules'
import ContainerCompare from './pages/ContainerCompare'
import Schedules from './pages/Schedules'
import ErrorBoundary from './components/ErrorBoundary'

type Theme = 'dark' | 'light'

interface AuthContextType {
  token: string | null;
  login: (newToken: string) => void;
  logout: () => void;
  socket: WebSocket | null;
  containers: any[];
  setContainers: React.Dispatch<React.SetStateAction<any[]>>;
  alerts: any[];
  setAlerts: React.Dispatch<React.SetStateAction<any[]>>;
  isConnected: boolean;
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const defaultContext: AuthContextType = {
  token: null,
  login: () => {},
  logout: () => {},
  socket: null,
  containers: [],
  setContainers: () => {},
  alerts: [],
  setAlerts: () => {},
  isConnected: false,
  theme: 'dark',
  setTheme: () => {}
};

const AuthContext = createContext<AuthContextType>(defaultContext)

export const useAuth = () => useContext(AuthContext)

const HEARTBEAT_INTERVAL = 30000
const RECONNECT_DELAY = 5000

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [containers, setContainers] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return (saved === 'light' || saved === 'dark') ? saved : 'dark'
  })

  useEffect(() => {
    localStorage.setItem('theme', theme)
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connectSocket = useCallback(() => {
    if (!token) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/metrics`

    console.log('Connecting to WebSocket:', wsUrl)
    const ws = new WebSocket(wsUrl)
    socketRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      setSocket(ws)
      
      // Start heartbeat
      heartbeatIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send('ping')
        }
      }, HEARTBEAT_INTERVAL)
    }

    ws.onmessage = (event) => {
      if (event.data === 'pong') return

      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'container_update') {
          setContainers(prev => {
            if (!Array.isArray(prev)) return [data.container]
            const idx = prev.findIndex(c => c.id === data.container.id)
            if (idx >= 0) {
              const updated = [...prev]
              updated[idx] = data.container
              return updated
            }
            return [...prev, data.container]
          })
        } else if (data.type === 'alert') {
          setAlerts(prev => {
            const currentAlerts = Array.isArray(prev) ? prev : []
            return [data, ...currentAlerts].slice(0, 50)
          })
        } else if (data.type === 'metrics') {
          // Handle metrics if needed
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      setSocket(null)
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
      }
      
      // Attempt reconnect
      reconnectTimeoutRef.current = setTimeout(connectSocket, RECONNECT_DELAY)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
      ws.close()
    }
  }, [token])

  useEffect(() => {
    if (token) {
      connectSocket()
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
      }
    }
  }, [token, connectSocket])

  const login = (newToken: string) => {
    localStorage.setItem('token', newToken)
    setToken(newToken)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setIsConnected(false)
    if (socketRef.current) {
      socketRef.current.close()
    }
    setSocket(null)
  }

  return (
    <ErrorBoundary>
      <AuthContext.Provider value={{ token, login, logout, socket, containers, setContainers, alerts, setAlerts, isConnected, theme, setTheme }}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={!token ? <Login /> : <Navigate to="/" />} />
            <Route path="/" element={token ? <Dashboard /> : <Navigate to="/login" />} />
            <Route path="/container/:id" element={token ? <ContainerDetail /> : <Navigate to="/login" />} />
            <Route path="/containers/new" element={token ? <ContainerCreate /> : <Navigate to="/login" />} />
            <Route path="/stacks" element={token ? <Stacks /> : <Navigate to="/login" />} />
            <Route path="/hosts" element={token ? <Hosts /> : <Navigate to="/login" />} />
            <Route path="/alerts" element={token ? <Alerts /> : <Navigate to="/login" />} />
            <Route path="/settings" element={token ? <Settings /> : <Navigate to="/login" />} />
            <Route path="/audit" element={token ? <AuditLogs /> : <Navigate to="/login" />} />
            <Route path="/notifications" element={token ? <Notifications /> : <Navigate to="/login" />} />
            <Route path="/backup" element={token ? <Backup /> : <Navigate to="/login" />} />
            <Route path="/docker" element={token ? <DockerResources /> : <Navigate to="/login" />} />
            <Route path="/users" element={token ? <Users /> : <Navigate to="/login" />} />
            <Route path="/container/:id/terminal" element={token ? <TerminalPage /> : <Navigate to="/login" />} />
            <Route path="/alert-rules" element={token ? <AlertRules /> : <Navigate to="/login" />} />
            <Route path="/compare" element={token ? <ContainerCompare /> : <Navigate to="/login" />} />
            <Route path="/schedules" element={token ? <Schedules /> : <Navigate to="/login" />} />
          </Routes>
        </BrowserRouter>
      </AuthContext.Provider>
    </ErrorBoundary>
  )
}

export default App