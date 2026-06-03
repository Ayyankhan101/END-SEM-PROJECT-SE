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
  ApiResponse,
  Schedule,
  ScheduleCreate,
  AlertRule,
  AlertRuleCreate,
  Backup,
  DockerImage,
  DockerVolume,
  DockerNetwork,
  AuditLog
} from '@/types'

const API_URL = '/api'  // Use relative paths - nginx handles proxying in production, vite in dev

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
          // Don't intercept login endpoint — let the component handle auth errors
          if (originalRequest.url === '/auth/token') {
            return Promise.reject(error)
          }

          originalRequest._retry = true
          
          const refreshToken = localStorage.getItem('refresh_token')
          if (refreshToken) {
            try {
              if (!this.refreshPromise) {
                this.refreshPromise = this.client.post('/auth/refresh', null, {
                  params: { refresh_token: refreshToken },
                  _retry: true // Don't retry the refresh request itself
                } as any).then(res => (res.data as any).access_token)
              }
              
              const newToken = await this.refreshPromise
              this.refreshPromise = null
              
              localStorage.setItem('token', newToken)
              if (originalRequest.headers) {
                originalRequest.headers.Authorization = `Bearer ${newToken}`
              }
              return this.client(originalRequest)
            } catch (refreshError) {
              this.refreshPromise = null
              console.error('Refresh token failed', refreshError)
            }
          }

          // Clear token and redirect to login if refresh fails
          localStorage.removeItem('token')
          localStorage.removeItem('refresh_token')
          window.location.href = '/login'
          return Promise.reject(error)
        }

        // Handle rate limiting (max 3 retries)
        if (error.response?.status === 429) {
          const config = originalRequest as AxiosRequestConfig & { _retryCount?: number }
          config._retryCount = (config._retryCount ?? 0) + 1
          if (config._retryCount <= 3) {
            const retryAfter = error.response.headers['retry-after']
            if (retryAfter) {
              const delay = parseInt(retryAfter) * 1000
              await new Promise(resolve => setTimeout(resolve, delay))
              return this.client(config)
            }
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
  async getContainers(search?: string, statusFilter?: string): Promise<Container[]> {
    const params = new URLSearchParams()
    if (search) params.append('search', search)
    if (statusFilter) params.append('status_filter', statusFilter)
    const query = params.toString() ? `?${params}` : ''
    const response = await this.client.get<Container[]>(`/containers${query}`)
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

  async getContainerStats(id: string): Promise<{ container_id: string; cpu_percent: number; memory_percent: number; memory_usage: number; memory_limit: number }> {
    const response = await this.client.get(`/containers/${id}/stats`)
    return response.data
  }

  async getAllContainerStats(): Promise<{ containers: Array<{ container_id: string; name: string; cpu_percent: number; memory_percent: number; memory_usage: number; memory_limit: number }> }> {
    const response = await this.client.get('/batch-stats')
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

  async stopContainer(id: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/containers/${id}/stop`)
    return response.data
  }

  async syncContainers(): Promise<{ status: string; message: string }> {
    const response = await this.client.post('/containers/sync')
    return response.data
  }

  async startContainer(id: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/containers/${id}/start`)
    return response.data
  }

  async deleteContainer(id: string): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/containers/${id}`)
    return response.data
  }

  async createContainer(config: ContainerCreateConfig): Promise<{ status: string; container: Container }> {
    const response = await this.client.post('/containers', config)
    return response.data
  }

  async bulkStartContainers(containerIds: string[]): Promise<{ status: string; results: { id: string; success: boolean }[] }> {
    const response = await this.client.post('/containers/bulk/start', { container_ids: containerIds })
    return response.data
  }

  async bulkStopContainers(containerIds: string[]): Promise<{ status: string; results: { id: string; success: boolean }[] }> {
    const response = await this.client.post('/containers/bulk/stop', { container_ids: containerIds })
    return response.data
  }

  async bulkRestartContainers(containerIds: string[]): Promise<{ status: string; results: { id: string; success: boolean }[] }> {
    const response = await this.client.post('/containers/bulk/restart', { container_ids: containerIds })
    return response.data
  }

  async bulkDeleteContainers(containerIds: string[]): Promise<{ status: string; results: { id: string; success: boolean; error?: string }[] }> {
    const response = await this.client.post('/containers/bulk/delete', { container_ids: containerIds })
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

  async activateHost(id: number): Promise<{ status: string; connected: boolean; host: string }> {
    const response = await this.client.post(`/hosts/${id}/activate`)
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

  // Audit endpoints
  async getAuditLogs(params: {
    skip?: number;
    limit?: number;
    action?: string;
    resource_type?: string;
    user_id?: number;
    days?: number;
  } = {}): Promise<{ logs: any[]; total: number; skip: number; limit: number }> {
    const response = await this.client.get('/audit/logs', { params })
    return response.data
  }

  async getAuditStats(days: number = 7): Promise<{
    period_days: number;
    total_actions: number;
    actions_by_type: Record<string, number>;
    resources_by_type: Record<string, number>;
    daily_activity: { date: string; count: number }[];
  }> {
    const response = await this.client.get('/audit/stats', { params: { days } })
    return response.data
  }

  // Notification channel endpoints
  async getNotificationChannels(): Promise<any[]> {
    const response = await this.client.get('/notifications/channels')
    return response.data
  }

  async createNotificationChannel(data: {
    name: string;
    channel_type: string;
    config: Record<string, any>;
    is_enabled?: boolean;
  }): Promise<any> {
    const response = await this.client.post('/notifications/channels', data)
    return response.data
  }

  async deleteNotificationChannel(channelId: number): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/notifications/channels/${channelId}`)
    return response.data
  }

  async testNotificationChannel(channelId: number): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/notifications/channels/${channelId}/test`)
    return response.data
  }

  // Backup endpoints
  async listBackups(): Promise<{ backups: { filename: string; size: number; created: string; path: string }[] }> {
    const response = await this.client.get('/backup/list')
    return response.data
  }

  async createBackup(includeMetrics: boolean = true): Promise<{ status: string; message: string; filename: string }> {
    const response = await this.client.post('/backup/create', null, { params: { include_metrics: includeMetrics } })
    return response.data
  }

  async restoreBackup(file: File): Promise<{ status: string; message: string; restored: any }> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await this.client.post('/backup/restore', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  }

  // Docker resource endpoints
  async getImages(all: boolean = false): Promise<any[]> {
    const response = await this.client.get('/docker/images', { params: { all } })
    return response.data
  }

  async pullImage(imageName: string, tag: string = 'latest'): Promise<{ status: string; message: string; image_id?: string }> {
    const response = await this.client.post('/docker/images/pull', null, { params: { image_name: imageName, tag } })
    return response.data
  }

  async deleteImage(imageId: string, force: boolean = false): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/docker/images/${imageId}`, { params: { force } })
    return response.data
  }

  async tagImage(imageId: string, newTag: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post(`/docker/images/${imageId}/tag`, null, { params: { tag: newTag } })
    return response.data
  }

  async getImageHistory(imageId: string): Promise<any[]> {
    const response = await this.client.get(`/docker/images/${imageId}/history`)
    return response.data
  }

  async getVolumes(): Promise<any[]> {
    const response = await this.client.get('/docker/volumes')
    return response.data
  }

  async createVolume(name: string, driver: string = 'local', labels?: Record<string, string>): Promise<any> {
    const response = await this.client.post('/docker/volumes', null, { params: { name, driver, labels } })
    return response.data
  }

  async deleteVolume(name: string, force: boolean = false): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/docker/volumes/${name}`, { params: { force } })
    return response.data
  }

  // User endpoints
  async getUsers(): Promise<any[]> {
    const response = await this.client.get('/users')
    return response.data
  }

  async createUser(data: { username: string; password: string; role: string }): Promise<any> {
    const response = await this.client.post('/users', data)
    return response.data
  }

  async updateUser(userId: number, data: { password?: string; role?: string; must_change_password?: boolean; force_password_change?: boolean }): Promise<any> {
    const response = await this.client.put(`/users/${userId}`, data)
    return response.data
  }

  async deleteUser(userId: number): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/users/${userId}`)
    return response.data
  }

  async updateContainerGroup(containerId: string, group: string): Promise<any> {
    const response = await this.client.put(`/containers/${containerId}`, { group })
    return response.data
  }

  async toggleContainerFavorite(containerId: string): Promise<{ status: string; is_favorite: number; message: string }> {
    const response = await this.client.post(`/containers/${containerId}/favorite`)
    return response.data
  }

  async updateContainerEnv(containerId: string, envVars: Record<string, string>): Promise<{ status: string; message: string }> {
    const response = await this.client.put(`/containers/${containerId}/env`, envVars)
    return response.data
  }

  async updateContainerPorts(containerId: string, ports: Record<string, number>): Promise<{ status: string; message: string }> {
    const response = await this.client.put(`/containers/${containerId}/ports`, ports)
    return response.data
  }

  async getAlertRules(containerId?: string): Promise<any[]> {
    const params = containerId ? { container_id: containerId } : {}
    const response = await this.client.get('/alert-rules', { params })
    return response.data
  }

  async createAlertRule(data: { container_id?: string; name: string; cpu_threshold: number; memory_threshold: number; enabled: boolean }): Promise<any> {
    const response = await this.client.post('/alert-rules', data)
    return response.data
  }

  async updateAlertRule(ruleId: number, data: { name?: string; cpu_threshold?: number; memory_threshold?: number; enabled?: boolean }): Promise<any> {
    const response = await this.client.put(`/alert-rules/${ruleId}`, data)
    return response.data
  }

  async deleteAlertRule(ruleId: number): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/alert-rules/${ruleId}`)
    return response.data
  }

  async getSchedules(containerId?: string): Promise<any[]> {
    const params = containerId ? { container_id: containerId } : {}
    const response = await this.client.get('/schedules', { params })
    return response.data
  }

  async createSchedule(data: { container_id: string; action: string; time: string }): Promise<any> {
    const response = await this.client.post('/schedules', data)
    return response.data
  }

  async updateSchedule(scheduleId: number, data: { action?: string; time?: string; enabled?: boolean }): Promise<any> {
    const response = await this.client.put(`/schedules/${scheduleId}`, data)
    return response.data
  }

  async deleteSchedule(scheduleId: number): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/schedules/${scheduleId}`)
    return response.data
  }

  async verify2FA(userId: number, code: string): Promise<{ access_token: string }> {
    const response = await this.client.post('/auth/2fa/verify', null, { params: { user_id: userId, code } })
    return response.data
  }

  async setup2FA(userId: number, code: string): Promise<{ secret: string; qr_code: string }> {
    const response = await this.client.post('/auth/2fa/setup', null, { params: { user_id: userId, code } })
    return response.data
  }

    async disable2FA(userId: number, code: string, password: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post('/auth/2fa/disable', null, { params: { user_id: userId, code, password } })
    return response.data
  }

    // Password change endpoints
    async changePasswordFirstLogin(username: string, oldPassword: string, newPassword: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post('/auth/change-password-first-login', {
      username,
      old_password: oldPassword,
      new_password: newPassword
    })
    return response.data
  }

  async logoutAllDevices(newPassword: string): Promise<{ status: string; message: string }> {
    const response = await this.client.post('/auth/logout-all', null, { params: { new_password: newPassword } })
    return response.data
  }

  async getNetworks(): Promise<any[]> {
    const response = await this.client.get('/docker/networks')
    return response.data
  }

  async createNetwork(
    name: string,
    driver: string = 'bridge',
    internal: boolean = false,
    attachable: boolean = false,
    labels?: Record<string, string>
  ): Promise<any> {
    const response = await this.client.post('/docker/networks', null, {
      params: { name, driver, internal, attachable, labels }
    })
    return response.data
  }

  async deleteNetwork(networkId: string): Promise<{ status: string; message: string }> {
    const response = await this.client.delete(`/docker/networks/${networkId}`)
    return response.data
  }

  // AI endpoints
  async getAIHealth(): Promise<Record<string, { available: boolean; model: string; endpoint: string }>> {
    const response = await this.client.get('/ai/health')
    return response.data
  }

  async getAIAnomalies(): Promise<{ anomalies: any[] }> {
    const response = await this.client.get('/ai/anomalies')
    return response.data
  }

  async getAIInsights(): Promise<any> {
    const response = await this.client.get('/ai/insights')
    return response.data
  }

  async analyzeContainer(containerId: string): Promise<any> {
    const response = await this.client.post(`/ai/analyze/${containerId}`)
    return response.data
  }

  async getAIRemediation(containerId: string): Promise<any> {
    const response = await this.client.get(`/ai/remediation/${containerId}`)
    return response.data
  }

  // Resource summary endpoint
  async getResourceSummary(): Promise<{
    total_containers: number;
    running_containers: number;
    stopped_containers: number;
    total_cpu_usage: number;
    total_memory_usage: number;
    total_memory_limit: number;
    memory_waste_percent: number;
    potential_savings: number;
    idle_containers: Array<{ container_id: string; name: string; cpu_percent: number; memory_percent: number }>;
    high_usage_containers: Array<{ container_id: string; name: string; status: string; cpu_percent: number; memory_percent: number }>;
  }> {
    const response = await this.client.get('/metrics/summary')
    return response.data
  }

  // Export metrics
  async exportMetrics(containerId?: string, hours: number = 24, format: 'json' | 'csv' = 'json'): Promise<any> {
    const params = new URLSearchParams({ hours: hours.toString(), format })
    if (containerId) params.append('container_id', containerId)
    const response = await this.client.get(`/metrics/export?${params}`)
    return response.data
  }

  // Trivy CVE scanner endpoints
  async scanContainerVulnerabilities(containerId: string): Promise<any> {
    const response = await this.client.get(`/trivy/scan/${containerId}`)
    return response.data
  }

  async scanImageVulnerabilities(imageName: string): Promise<any> {
    const response = await this.client.get(`/trivy/scan/image/${encodeURIComponent(imageName)}`)
    return response.data
  }

  async getTrivyHealth(): Promise<any> {
    const response = await this.client.get('/trivy/health')
    return response.data
  }
}

// Export singleton instance
export const api = new ApiClient()

// Export for use in components
export default api