import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios'
import type { 
  Container, 
  ContainerDetail, 
  Metric, 
  MetricsHistory,
  Alert, 
  RecoveryAction,
  Stack,
  StackCreate,
  Host,
  HostCreate,
  Settings,
  SettingsUpdate,
  LoginRequest,
  TokenResponse,
  ContainerCreateConfig,
  ApiResponse 
} from '@/types'

const API_URL = import.meta.env.VITE_API_URL || ''

interface ApiErrorResponse {
  error?: string;
  details?: Record<string, unknown>;
  status_code?: number;
}

class ApiClient {
  private client: AxiosInstance;
  private refreshPromise: Promise<string> | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 30000
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError<ApiErrorResponse>) => {
        const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

        // Handle 401 Unauthorized
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true

          // Clear token and redirect to login
          localStorage.removeItem('token')
          window.location.href = '/login'
          return Promise.reject(error)
        }

        // Handle rate limiting
        if (error.response?.status === 429) {
          const retryAfter = error.response.headers['retry-after']
          if (retryAfter) {
            const delay = parseInt(retryAfter) * 1000
            await new Promise(resolve => setTimeout(resolve, delay))
            return this.client(originalRequest)
          }
        }

        // Log error details
        console.error('API Error:', {
          status: error.response?.status,
          data: error.response?.data,
          url: originalRequest.url
        })

        return Promise.reject(error)
      }
    )
  }

  // Auth endpoints
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await this.client.post<TokenResponse>('/auth/token', credentials)
    return response.data
  }

  // Container endpoints
  async getContainers(): Promise<Container[]> {
    const response = await this.client.get<Container[]>('/containers')
    return response.data
  }

  async getContainer(id: string): Promise<ContainerDetail> {
    const response = await this.client.get<ContainerDetail>(`/containers/${id}`)
    return response.data
  }

  async getContainerMetrics(id: string, limit: number = 100): Promise<MetricsHistory> {
    const response = await this.client.get<MetricsHistory>(`/containers/${id}/metrics`, {
      params: { limit }
    })
    return response.data
  }

  async getContainerLogs(id: string, lines: number = 100): Promise<{ container_id: string; logs: string }> {
    const response = await this.client.get(`/containers/${id}/logs`, {
      params: { lines }
    })
    return response.data
  }

  async restartContainer(id: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/containers/${id}/restart`)
    return response.data
  }

  async pauseContainer(id: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/containers/${id}/pause`)
    return response.data
  }

  async unpauseContainer(id: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/containers/${id}/unpause`)
    return response.data
  }

  async createContainer(config: ContainerCreateConfig): Promise<{ status: string; container: Container }> {
    const response = await this.client.post('/containers', config)
    return response.data
  }

  // Metrics endpoints
  async getMetricsHistory(containerId?: string, hours: number = 24): Promise<MetricsHistory> {
    const params = new URLSearchParams({ hours: hours.toString() })
    if (containerId) params.append('container_id', containerId)
    const response = await this.client.get<MetricsHistory>(`/metrics/history?${params}`)
    return response.data
  }

  // Alert endpoints
  async getAlerts(limit: number = 50, containerId?: string): Promise<Alert[]> {
    const params: Record<string, string | number> = { limit }
    if (containerId) params.container_id = containerId
    const response = await this.client.get<Alert[]>('/alerts', { params })
    return response.data
  }

  // Stack endpoints
  async getStacks(): Promise<Stack[]> {
    const response = await this.client.get<Stack[]>('/stacks')
    return response.data
  }

  async createStack(stack: StackCreate): Promise<Stack> {
    const response = await this.client.post<Stack>('/stacks', stack)
    return response.data
  }

  async deleteStack(id: number): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/stacks/${id}`)
    return response.data
  }

  async startStack(id: number): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/stacks/${id}/start`)
    return response.data
  }

  async stopStack(id: number): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/stacks/${id}/stop`)
    return response.data
  }

  // Host endpoints
  async getHosts(): Promise<Host[]> {
    const response = await this.client.get<Host[]>('/hosts')
    return response.data
  }

  async createHost(host: HostCreate): Promise<Host> {
    const response = await this.client.post<Host>('/hosts', host)
    return response.data
  }

  async deleteHost(id: number): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/hosts/${id}`)
    return response.data
  }

  async testHost(id: number): Promise<{ status: string; connected: boolean }> {
    const response = await this.client.post(`/hosts/${id}/test`)
    return response.data
  }

  // Settings endpoints
  async getSettings(): Promise<Settings> {
    const response = await this.client.get<Settings>('/settings')
    return response.data
  }

  async updateSettings(settings: SettingsUpdate): Promise<Settings> {
    const response = await this.client.put<Settings>('/settings', settings)
    return response.data
  }

  // Health check
  async checkHealth(): Promise<{ status: string; timestamp: string }> {
    const response = await this.client.get('/health')
    return response.data
  }
}

// Export singleton instance
export const api = new ApiClient()

// Export for use in components
export default api