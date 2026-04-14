import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const login = async (username, password) => {
  const response = await api.post('/api/auth/token', { username, password })
  return response.data
}

export const getContainers = async () => {
  const response = await api.get('/api/containers')
  return response.data
}

export const getContainer = async (id) => {
  const response = await api.get(`/api/containers/${id}`)
  return response.data
}

export const getContainerMetrics = async (id, limit = 100) => {
  const response = await api.get(`/api/containers/${id}/metrics?limit=${limit}`)
  return response.data
}

export const getMetricsHistory = async (containerId = null, hours = 24) => {
  const params = new URLSearchParams({ hours })
  if (containerId) params.append('container_id', containerId)
  const response = await api.get(`/api/metrics/history?${params}`)
  return response.data
}

export const getAlerts = async (limit = 50, containerId = null) => {
  const params = new URLSearchParams({ limit })
  if (containerId) params.append('container_id', containerId)
  const response = await api.get(`/api/alerts?${params}`)
  return response.data
}

export const restartContainer = async (id) => {
  const response = await api.post(`/api/containers/${id}/restart`)
  return response.data
}

export const pauseContainer = async (id) => {
  const response = await api.post(`/api/containers/${id}/pause`)
  return response.data
}

export const unpauseContainer = async (id) => {
  const response = await api.post(`/api/containers/${id}/unpause`)
  return response.data
}

export const checkHealth = async () => {
  const response = await api.get('/api/health')
  return response.data
}

export default api