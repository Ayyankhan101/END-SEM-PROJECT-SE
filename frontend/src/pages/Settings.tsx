import { useState, useEffect, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Save, RefreshCw, Settings as SettingsIcon, AlertCircle, Sun, Moon, Shield, ShieldCheck, KeyRound, X } from 'lucide-react'
import { api } from '@/services/api'
import { useAuth } from '@/App'
import type { Settings as SettingsType } from '@/types'

function Settings() {
  const { theme, setTheme } = useAuth()
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
  
  const [show2FAModal, setShow2FAModal] = useState(false)
  const [twoFactorCode, setTwoFactorCode] = useState('')
  const [twoFactorLoading, setTwoFactorLoading] = useState(false)
  const [qrCode, setQrCode] = useState<string | null>(null)
  const [secret, setSecret] = useState<string | null>(null)
  const [disablePassword, setDisablePassword] = useState('')
  const [is2FAEnabled, setIs2FAEnabled] = useState(false)

  useEffect(() => {
    loadSettings()
    load2FAStatus()
  }, [])

  const load2FAStatus = async () => {
    try {
      const data = (await api.getSettings()) as unknown as Record<string, any>
      setIs2FAEnabled(data?.two_factor_enabled || false)
    } catch (err) {
      console.error('Failed to load 2FA status:', err)
    }
  }

  const loadSettings = async () => {
    try {
      setLoading(true)
      const data = (await api.getSettings()) as unknown as Record<string, any>
      setSettings({
        poll_interval: data?.poll_interval,
        cpu_threshold: data?.cpu_threshold,
        memory_threshold: data?.memory_threshold,
        metrics_ttl_days: data?.metrics_ttl_days,
        recovery_enabled: data?.recovery_enabled,
        jwt_expiration_hours: data?.jwt_expiration_hours
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

        <div className="bg-gray-800 p-4 rounded-lg mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {theme === 'dark' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            <span className="font-medium">Theme</span>
          </div>
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              theme === 'dark' 
                ? 'bg-gray-700 hover:bg-gray-600 text-yellow-400' 
                : 'bg-blue-600 hover:bg-blue-500 text-white'
            }`}
          >
            {theme === 'dark' ? 'Dark' : 'Light'}
          </button>
        </div>

        <div className="bg-gray-800 p-4 rounded-lg mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {is2FAEnabled ? <ShieldCheck className="w-5 h-5 text-green-500" /> : <Shield className="w-5 h-5 text-gray-400" />}
              <span className="font-medium">Two-Factor Authentication</span>
              {is2FAEnabled && (
                <span className="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded">Enabled</span>
              )}
            </div>
            {is2FAEnabled ? (
              <button
                onClick={() => {
                  setTwoFactorCode('')
                  setDisablePassword('')
                  setShow2FAModal(true)
                }}
                className="px-4 py-2 rounded-lg font-medium bg-red-600 hover:bg-red-500 text-white"
              >
                Disable 2FA
              </button>
            ) : (
              <button
                onClick={async () => {
                  try {
                    const data = await api.setup2FA(1, '')
                    if (data.qr_code) {
                      setQrCode(data.qr_code)
                      setSecret(data.secret)
                      setTwoFactorCode('')
                      setShow2FAModal(true)
                    }
                  } catch (err) {
                    console.error('2FA setup failed:', err)
                  }
                }}
                className="px-4 py-2 rounded-lg font-medium bg-blue-600 hover:bg-blue-500 text-white"
              >
                Enable 2FA
              </button>
            )}
          </div>
          <p className="text-gray-400 text-sm mt-2">
            {is2FAEnabled 
              ? 'Your account is protected with Google Authenticator'
              : 'Add an extra layer of security using Google Authenticator'}
          </p>
        </div>

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

        {show2FAModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg w-[480px]">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-bold">
                  {is2FAEnabled ? 'Disable 2FA' : 'Enable 2FA'}
                </h3>
                <button onClick={() => setShow2FAModal(false)} className="text-gray-400 hover:text-white">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {!is2FAEnabled && qrCode && (
                <div className="mb-4 text-center">
                  <img src={qrCode} alt="QR Code" className="w-48 h-48 mx-auto mb-4" />
                  {secret && (
                    <div className="bg-gray-700 p-2 rounded text-sm font-mono mb-4">
                      Secret: {secret}
                    </div>
                  )}
                  <p className="text-gray-400 text-sm mb-2">
                    Scan QR code with Google Authenticator or enter secret manually
                  </p>
                </div>
              )}

              {is2FAEnabled ? (
              <>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Your Password</label>
                  <input
                    type="password"
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    placeholder="Enter your password"
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Verification Code (OTP)</label>
                  <input
                    type="text"
                    value={twoFactorCode}
                    onChange={(e) => setTwoFactorCode(e.target.value)}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    placeholder="Enter current 6-digit code"
                    maxLength={6}
                  />
                </div>
              </>
            ) : (
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Verification Code</label>
                <input
                  type="text"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  placeholder="Enter 6-digit code from authenticator"
                  maxLength={6}
                />
              </div>
            )}

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShow2FAModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={async () => {
                    if (is2FAEnabled) {
                      if (!disablePassword) {
                        setError('Password required')
                        return
                      }
                      try {
                        await api.disable2FA(1, twoFactorCode, disablePassword)
                        setIs2FAEnabled(false)
                        setShow2FAModal(false)
                        setSuccess('2FA disabled')
                      } catch (err: any) {
                        setError(err.response?.data?.detail || 'Failed to disable 2FA')
                      }
                    } else {
                      if (!twoFactorCode || twoFactorCode.length !== 6) {
                        setError('Enter 6-digit code')
                        return
                      }
                      try {
                        await api.setup2FA(1, twoFactorCode)
                        setIs2FAEnabled(true)
                        setShow2FAModal(false)
                        setSuccess('2FA enabled')
                      } catch (err: any) {
                        setError(err.response?.data?.detail || 'Invalid verification code')
                      }
                    }
                  }}
                  disabled={twoFactorLoading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded disabled:opacity-50"
                >
                  {twoFactorLoading ? 'Processing...' : (is2FAEnabled ? 'Disable 2FA' : 'Verify & Enable')}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Settings