import { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { io } from 'socket.io-client'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ContainerDetail from './pages/ContainerDetail'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const AuthContext = createContext(null)

export const useAuth = () => useContext(AuthContext)

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'))
  const [socket, setSocket] = useState(null)
  const [containers, setContainers] = useState([])
  const [alerts, setAlerts] = useState([])

  useEffect(() => {
    if (token) {
      const newSocket = io(`${API_URL}/ws/metrics`, {
        auth: { token },
        transports: ['websocket'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000
      })

      newSocket.on('connect', () => {
        console.log('WebSocket connected')
      })

      newSocket.on('metrics', (data) => {
        console.log('Metrics received:', data)
      })

      newSocket.on('container_update', (data) => {
        setContainers(prev => {
          const idx = prev.findIndex(c => c.id === data.container.id)
          if (idx >= 0) {
            const updated = [...prev]
            updated[idx] = data.container
            return updated
          }
          return [...prev, data.container]
        })
      })

      newSocket.on('alert', (data) => {
        setAlerts(prev => [data, ...prev].slice(0, 50))
      })

      setSocket(newSocket)

      return () => {
        newSocket.close()
      }
    }
  }, [token])

  const login = (newToken) => {
    localStorage.setItem('token', newToken)
    setToken(newToken)
  }

  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    if (socket) {
      socket.close()
    }
  }

  return (
    <AuthContext.Provider value={{ token, login, logout, socket, containers, setContainers, alerts, setAlerts }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={!token ? <Login /> : <Navigate to="/" />} />
          <Route path="/" element={token ? <Dashboard /> : <Navigate to="/login" />} />
          <Route path="/container/:id" element={token ? <ContainerDetail /> : <Navigate to="/login" />} />
          <Route path="/alerts" element={token ? <Alerts /> : <Navigate to="/login" />} />
          <Route path="/settings" element={token ? <Settings /> : <Navigate to="/login" />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}

export default App