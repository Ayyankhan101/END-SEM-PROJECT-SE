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
import ErrorBoundary from './components/ErrorBoundary'

const AuthContext = createContext(null)

export const useAuth = () => useContext(AuthContext)

const HEARTBEAT_INTERVAL = 30000
const RECONNECT_DELAY = 5000

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [socket, setSocket] = useState(null)
  const [containers, setContainers] = useState([])
  const [alerts, setAlerts] = useState([])
  const [isConnected, setIsConnected] = useState(false)

  const socketRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const heartbeatIntervalRef = useRef(null)

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

  const login = (newToken) => {
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
      <AuthContext.Provider value={{ token, login, logout, socket, containers, setContainers, alerts, setAlerts, isConnected }}>
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
          </Routes>
        </BrowserRouter>
      </AuthContext.Provider>
    </ErrorBoundary>
  )
}

export default App