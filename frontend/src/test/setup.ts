import '@testing-library/jest-dom'
import { vi } from 'vitest'

Storage.prototype.getItem = vi.fn()
Storage.prototype.setItem = vi.fn()
Storage.prototype.removeItem = vi.fn()
Storage.prototype.clear = vi.fn()

Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:3001',
    pathname: '/',
    origin: 'http://localhost:3001',
    assign: vi.fn(),
    replace: vi.fn()
  },
  writable: true
})

window.history = {
  ...window.history,
  pushState: vi.fn(),
  replaceState: vi.fn(),
  go: vi.fn(),
  back: vi.fn()
} as History