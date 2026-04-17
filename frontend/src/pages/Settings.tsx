import { useState, useEffect, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Save, RefreshCw, Settings as SettingsIcon, AlertCircle } from 'lucide-react'
import { api } from '@/services/api'
import type { Settings as SettingsType } from '@/types'

function Settings() {
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [settings, setSettings] = useState<SettingsType>({
    poll_interval: 5,
    cpu_threshold: 90,
    memory_threshold: 90,
    metrics_ttl_days: 7,
    recovery_enabled: true,
    jwt_expiration_hours: 24
  })

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = await api.getSettings()
      setSettings({
        poll_interval: data.poll_interval,
        cpu_threshold: data.cpu_threshold,
        memory_threshold: data.memory_threshold,
        metrics_ttl_days: data.metrics_ttl_days,
        recovery_enabled: data.recovery_enabled,
        jwt_expiration_hours: data.jwt_expiration_hours
      })
    } catch (err) {
      setError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    try {
      setSaving(true)
      setError(null)
      setSuccess(null)
      await api.updateSettings(settings)
      setSuccess('Settings saved successfully')
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleChange = (field: keyof SettingsType, value: number | boolean) => {
    setSettings(prev => ({ ...prev, [field]: value }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <h1 className="text-2xl font-bold mb-6">Settings</h1>

        {error && (
          <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-500/10 border border-green-500 text-green-400 px-4 py-3 rounded-lg mb-4 flex items-center gap-2">
            <SettingsIcon className="w-5 h-5" />
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="bg-gray-800 p-6 rounded-lg max-w-2xl">
          <div className="flex items-center gap-3 mb-6">
            <SettingsIcon className="w-6 h-6 text-blue-500" />
            <h2 className="text-xl font-medium">Configuration</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Poll Interval (seconds)
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={settings.poll_interval}
                onChange={(e) => handleChange('poll_interval', parseInt(e.target.value))}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">How often to check container status</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                CPU Threshold (%)
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.cpu_threshold}
                onChange={(e) => handleChange('cpu_threshold', parseFloat(e.target.value))}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">Alert when CPU usage exceeds this</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Memory Threshold (%)
              </label>
              <input
                type="number"
                min="1"
                max="100"
                value={settings.memory_threshold}
                onChange={(e) => handleChange('memory_threshold', parseFloat(e.target.value))}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">Alert when memory usage exceeds this</p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Metrics TTL (days)
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={settings.metrics_ttl_days}
                onChange={(e) => handleChange('metrics_ttl_days', parseInt(e.target.value))}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-gray-500 mt-1">How long to keep historical metrics</p>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="recovery_enabled"
                checked={settings.recovery_enabled}
                onChange={(e) => handleChange('recovery_enabled', e.target.checked)}
                className="w-5 h-5 rounded bg-gray-700 border-gray-600 text-blue-500 focus:ring-blue-500"
              />
              <label htmlFor="recovery_enabled" className="text-sm font-medium text-gray-300">
                Enable Auto-Recovery
              </label>
            </div>
          </div>

          <div className="mt-6 flex gap-4">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white px-6 py-2 rounded-lg transition-colors"
            >
              {saving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              Save Settings
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default Settings