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
import AIInsights from './pages/AIInsights'
import ErrorBoundary from './components/ErrorBoundary'

type Theme = 'light' | 'dark' | 'system'

interface AuthContextType {
  token: string | null;
  login: (newToken: string, userId?: number) => void;
  logout: () => void;
  socket: WebSocket | null;
  containers: any[];
  setContainers: React.Dispatch<React.SetStateAction<any[]>>;
  alerts: any[];
  setAlerts: React.Dispatch<React.SetStateAction<any[]>>;
  isConnected: boolean;
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  userId: number | null;
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
  resolvedTheme: 'dark',
  setTheme: () => {},
  toggleTheme: () => {},
  userId: null
};

const AuthContext = createContext<AuthContextType>(defaultContext)

export const useAuth = () => useContext(AuthContext)

const HEARTBEAT_INTERVAL = 30000

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [userId, setUserId] = useState<number | null>(() => {
    const saved = localStorage.getItem('userId')
    return saved ? parseInt(saved) : null
  })
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [containers, setContainers] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [connectionChecked, setConnectionChecked] = useState(false)

  // Check API connectivity (fallback when WS fails)
  useEffect(() => {
    if (token && !connectionChecked) {
      fetch('/api/health', {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(res => {
          setIsConnected(res.ok)
          setConnectionChecked(true)
        })
        .catch(() => {
          setIsConnected(false)
        })
    }
  }, [token])

  // Periodic connectivity check
  useEffect(() => {
    if (token && connectionChecked) {
      const interval = setInterval(() => {
        fetch('/api/health', {
          headers: { Authorization: `Bearer ${token}` }
        })
          .then(res => setIsConnected(res.ok))
          .catch(() => setIsConnected(false))
      }, 30000)
      return () => clearInterval(interval)
    }
  }, [token, connectionChecked])
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('theme')
    return (saved === 'light' || saved === 'dark' || saved === 'system') ? saved : 'dark'
  })
  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('dark')

  useEffect(() => {
    localStorage.setItem('theme', theme)
    
    const applyTheme = (isDark: boolean) => {
      document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
      if (isDark) {
        document.documentElement.classList.add('dark')
        document.documentElement.classList.remove('light')
      } else {
        document.documentElement.classList.add('light')
        document.documentElement.classList.remove('dark')
      }
      setResolvedTheme(isDark ? 'dark' : 'light')
    }

    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      applyTheme(mediaQuery.matches)
      const handler = (e: MediaQueryListEvent) => applyTheme(e.matches)
      mediaQuery.addEventListener('change', handler)
    } else {
      applyTheme(theme === 'dark')
    }
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }, [])

  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptRef = useRef(0)
  const maxReconnectDelay = 30000
  const baseReconnectDelay = 1000
  const MAX_WS_RETRIES = 3

  const [wsFailed, setWsFailed] = useState(false)

  const connectSocket = useCallback(() => {
    if (!token) return

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/metrics?token=${token}`

    console.log('Connecting to WebSocket:', wsUrl)
    const ws = new WebSocket(wsUrl)
    socketRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      setSocket(ws)
      reconnectAttemptRef.current = 0  // Reset backoff counter on successful connect
      
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
        } else if (data.type === 'container_deleted') {
          setContainers(prev => {
            if (!Array.isArray(prev)) return []
            return prev.filter(c => c.id !== data.container_id)
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
      setSocket(null)
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current)
      }
      
      // Check if max retries exceeded - fallback to polling
      if (reconnectAttemptRef.current >= MAX_WS_RETRIES - 1) {
        console.log(`WebSocket failed after ${MAX_WS_RETRIES} attempts, using polling fallback`)
        setWsFailed(true)
        setIsConnected(false)  // Use polling instead
        return
      }
      
      // Exponential backoff reconnect
      const delay = Math.min(
        baseReconnectDelay * Math.pow(2, reconnectAttemptRef.current),
        maxReconnectDelay
      )
      reconnectAttemptRef.current += 1
      console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptRef.current})`)
      reconnectTimeoutRef.current = setTimeout(connectSocket, delay)
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

  const login = (newToken: string, newUserId?: number) => {
    localStorage.setItem('token', newToken)
    setToken(newToken)
    if (newUserId !== undefined && newUserId !== null) {
      localStorage.setItem('userId', String(newUserId))
      setUserId(newUserId)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('userId')
    setToken(null)
    setUserId(null)
    setIsConnected(false)
    if (socketRef.current) {
      socketRef.current.close()
    }
    setSocket(null)
  }

  return (
    <ErrorBoundary>
      <AuthContext.Provider value={{ token, userId, login, logout, socket, containers, setContainers, alerts, setAlerts, isConnected, theme, resolvedTheme, setTheme, toggleTheme }}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={!token ? <Login /> : <Navigate to="/" />} />
            <Route path="/" element={token ? <Dashboard /> : <Navigate to="/login" />} />
            <Route path="/containers" element={token ? <Dashboard /> : <Navigate to="/login" />} />
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
            <Route path="/ai" element={token ? <AIInsights /> : <Navigate to="/login" />} />
          </Routes>
        </BrowserRouter>
      </AuthContext.Provider>
    </ErrorBoundary>
  )
}

export default App