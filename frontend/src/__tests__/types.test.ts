import { describe, it, expect } from 'vitest'
import type {
  Container,
  ContainerState,
  Schedule,
  ScheduleCreate,
  AlertRule,
  Alert,
  Metric,
  Host,
  User,
  Settings,
  DockerImage,
  DockerVolume,
  DockerNetwork,
  Backup,
  AlertSeverity
} from '../types'

describe('TypeScript Types', () => {
  describe('Container', () => {
    it('should validate container structure', () => {
      const container: Container = {
        id: 'abc123',
        name: 'nginx',
        image: 'nginx:latest',
        status: 'running',
        created: '2024-01-01T00:00:00Z'
      }

      expect(container.id).toBeDefined()
      expect(container.name).toBe('nginx')
      expect(container.status).toBe('running')
    })

    it('should allow optional container fields', () => {
      const container: Container = {
        id: 'abc123',
        name: 'nginx',
        image: 'nginx:latest',
        status: 'running'
      }

      expect(container.created).toBeUndefined()
      expect(container.state).toBeUndefined()
    })
  })

  describe('ContainerState', () => {
    it('should validate container state', () => {
      const state: ContainerState = {
        Status: 'running',
        Running: true,
        Paused: false,
        Restarting: false
      }

      expect(state.Running).toBe(true)
      expect(state.Status).toBe('running')
    })
  })

  describe('Schedule', () => {
    it('should validate schedule structure', () => {
      const schedule: Schedule = {
        id: 1,
        container_id: 'abc123',
        container_name: 'nginx',
        action: 'start',
        time: '09:00',
        enabled: true
      }

      expect(schedule.id).toBe(1)
      expect(schedule.action).toBe('start')
      expect(schedule.time).toBe('09:00')
    })

    it('should allow valid action types', () => {
      const schedule: ScheduleCreate = {
        container_id: 'abc123',
        action: 'stop',
        time: '09:00'
      }

      expect(['start', 'stop', 'restart']).toContain(schedule.action)
    })
  })

  describe('AlertRule', () => {
    it('should validate alert rule structure', () => {
      const rule: AlertRule = {
        id: 1,
        name: 'High CPU',
        cpu_threshold: 80,
        memory_threshold: 90,
        enabled: true
      }

      expect(rule.cpu_threshold).toBe(80)
      expect(rule.memory_threshold).toBe(90)
    })
  })

  describe('Alert', () => {
    it('should validate alert structure', () => {
      const alert: Alert = {
        id: 1,
        container_id: 'abc123',
        alert_type: 'cpu_high',
        message: 'CPU usage above threshold',
        severity: 'warning',
        timestamp: '2024-01-01T00:00:00Z'
      }

      expect(alert.alert_type).toBe('cpu_high')
      expect(alert.severity).toBe('warning')
    })
  })

  describe('Metric', () => {
    it('should validate metric structure', () => {
      const metric: Metric = {
        id: 1,
        container_id: 'abc123',
        cpu_percent: 45.5,
        memory_percent: 62.3,
        memory_usage: 512000000,
        timestamp: '2024-01-01T00:00:00Z'
      }

      expect(metric.cpu_percent).toBe(45.5)
      expect(metric.memory_usage).toBeDefined()
    })
  })

  describe('Host', () => {
    it('should validate host structure', () => {
      const host: Host = {
        id: 1,
        name: 'Production',
        socket_path: '/var/run/docker.sock',
        api_version: '1.44',
        status: 'connected'
      }

      expect(host.name).toBe('Production')
      expect(host.status).toBe('connected')
    })
  })

  describe('User', () => {
    it('should validate user structure', () => {
      const user: User = {
        id: 1,
        username: 'admin',
        role: 'admin',
        must_change_password: false
      }

      expect(user.username).toBe('admin')
      expect(user.role).toBe('admin')
    })
  })

  describe('Settings', () => {
    it('should validate settings structure', () => {
      const settings: Settings = {
        poll_interval: 30,
        cpu_threshold: 80,
        memory_threshold: 80,
        metrics_ttl_days: 7,
        recovery_enabled: true,
        jwt_expiration_hours: 24
      }

      expect(settings.poll_interval).toBe(30)
      expect(settings.recovery_enabled).toBe(true)
    })
  })

  describe('DockerImage', () => {
    it('should validate image structure', () => {
      const image: DockerImage = {
        id: 'sha256:abc123',
        tags: ['nginx:latest', 'nginx:1.25'],
        size: 1024000000,
        created: '2024-01-01T00:00:00Z',
        labels: {}
      }

      expect(image.tags).toHaveLength(2)
      expect(image.tags).toContain('nginx:latest')
    })
  })

  describe('DockerVolume', () => {
    it('should validate volume structure', () => {
      const volume: DockerVolume = {
        name: 'myvolume',
        driver: 'local',
        mountpoint: '/var/lib/docker/volumes/myvolume/_data',
        created: '2024-01-01T00:00:00Z',
        labels: {},
        size: 1024000000
      }

      expect(volume.name).toBe('myvolume')
      expect(volume.driver).toBe('local')
    })
  })

  describe('DockerNetwork', () => {
    it('should validate network structure', () => {
      const network: DockerNetwork = {
        id: 'abc123',
        name: 'mynetwork',
        driver: 'bridge',
        scope: 'local',
        created: '2024-01-01T00:00:00Z',
        labels: {},
        internal: false,
        attachable: true,
        ingress: false,
        containers: []
      }

      expect(network.name).toBe('mynetwork')
      expect(network.driver).toBe('bridge')
    })
  })

  describe('Backup', () => {
    it('should validate backup structure', () => {
      const backup: Backup = {
        filename: 'backup_2024-01-01.db',
        size: 1024000,
        created: '2024-01-01T00:00:00Z',
        path: '/backups/backup_2024-01-01.db'
      }

      expect(backup.filename).toBeDefined()
      expect(backup.size).toBeGreaterThan(0)
    })
  })

  describe('AlertSeverity', () => {
    it('should allow valid severity values', () => {
      const severities: AlertSeverity[] = ['info', 'warning', 'critical']

      expect(severities).toContain('warning')
      expect(severities).toContain('critical')
    })
  })
})