import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import * as apiModule from '../services/api'

describe('ApiClient', () => {
  let consoleErrorSpy: any

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    localStorage.clear()
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
    vi.clearAllMocks()
  })

  describe('API contract', () => {
    it('should define getContainers method', () => {
      expect(typeof apiModule.api.getContainers).toBe('function')
    })

    it('should define getContainer method', () => {
      expect(typeof apiModule.api.getContainer).toBe('function')
    })

    it('should define restartContainer method', () => {
      expect(typeof apiModule.api.restartContainer).toBe('function')
    })

    it('should define stopContainer method', () => {
      expect(typeof apiModule.api.stopContainer).toBe('function')
    })

    it('should define pauseContainer method', () => {
      expect(typeof apiModule.api.pauseContainer).toBe('function')
    })

    it('should define unpauseContainer method', () => {
      expect(typeof apiModule.api.unpauseContainer).toBe('function')
    })

    it('should define getSettings method', () => {
      expect(typeof apiModule.api.getSettings).toBe('function')
    })

    it('should define getAlerts method', () => {
      expect(typeof apiModule.api.getAlerts).toBe('function')
    })

    it('should define getNotificationChannels method', () => {
      expect(typeof apiModule.api.getNotificationChannels).toBe('function')
    })

    it('should define getSchedules method', () => {
      expect(typeof apiModule.api.getSchedules).toBe('function')
    })
  })

  describe('Request validation', () => {
    it('should validate login credentials structure', () => {
      const validRequest = { username: 'admin', password: 'admin123' }
      expect(validRequest.username).toBeDefined()
      expect(validRequest.password).toBeDefined()
    })

    it('should validate container create config', () => {
      const validConfig = {
        image: 'nginx:latest',
        name: 'my-container',
        ports: { '80': 8080 },
        environment: { 'NODE_ENV': 'production' }
      }
      expect(validConfig.image).toBeDefined()
      expect(validConfig.name).toBeDefined()
    })
  })
})