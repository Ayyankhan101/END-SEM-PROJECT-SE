import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import type { NotificationChannel } from '@/types'
import Header from '@/components/Header'
import { Bell } from 'lucide-react'
import { useAuth } from '@/App'

export default function Notifications() {
  const { isConnected, logout } = useAuth()
  const [channels, setChannels] = useState<NotificationChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState<{
    name: string;
    channel_type: string;
    config: Record<string, string>;
  }>({
    name: '',
    channel_type: 'webhook',
    config: { url: '' }
  })

  useEffect(() => {
    loadChannels()
  }, [])

  async function loadChannels() {
    try {
      setLoading(true)
      const data = await api.getNotificationChannels() as unknown
      setChannels(Array.isArray(data) ? data : (data as Record<string, any>)?.channels || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load channels')
    } finally {
      setLoading(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.createNotificationChannel(formData)
      setShowForm(false)
      setFormData({ name: '', channel_type: 'webhook', config: { url: '' } })
      loadChannels()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create channel')
    }
  }

  async function handleDelete(id: number) {
    if (!confirm('Delete this channel?')) return
    try {
      await api.deleteNotificationChannel(id)
      loadChannels()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete channel')
    }
  }

  async function handleTest(id: number) {
    try {
      await api.testNotificationChannel(id)
      alert('Test notification sent')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to send test notification')
    }
  }

  const defaultConfigs: Record<string, Record<string, string>> = {
    webhook: { url: '' },
    slack: { webhook_url: '' },
    discord: { webhook_url: '' },
    email: { smtp_host: '', from: '', to: '' }
  }

  const channelTypes = [
    { value: 'webhook', label: 'Webhook', fields: [{ name: 'url', label: 'URL' }] },
    { value: 'slack', label: 'Slack', fields: [{ name: 'webhook_url', label: 'Webhook URL' }] },
    { value: 'discord', label: 'Discord', fields: [{ name: 'webhook_url', label: 'Webhook URL' }] },
    { value: 'email', label: 'Email', fields: [{ name: 'smtp_host', label: 'SMTP Host' }, { name: 'from', label: 'From' }, { name: 'to', label: 'To' }] }
  ]

  const handleTypeChange = (newType: string) => {
    setFormData(f => ({
      ...f,
      channel_type: newType,
      config: { ...defaultConfigs[newType] }
    }))
  }

  return (
    <div className="app-surface">
      <Header
        title="Notifications"
        icon={<Bell size={24} />}
        isConnected={isConnected}
        onLogout={logout}
      />
      <main className="app-main">
      <div className="dashboard-card">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-[#111827] dark:text-white">Notification Channels</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 text-white"
        >
          {showForm ? 'Cancel' : 'Add Channel'}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 rounded-lg p-6 mb-6">
          <div className="grid gap-4">
            <div>
              <label className="block mb-2">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={e => setFormData(f => ({ ...f, name: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2"
                required
              />
            </div>

            <div>
              <label className="block mb-2">Type</label>
              <select
                value={formData.channel_type}
                onChange={e => handleTypeChange(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2"
              >
                {channelTypes.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block mb-2">Configuration</label>
              {channelTypes.find(t => t.value === formData.channel_type)?.fields.map(field => (
                <input
                  key={field.name}
                  type="text"
                  placeholder={field.label}
                  value={formData.config[field.name] || ''}
                  onChange={e => setFormData(f => ({
                    ...f,
                    config: { ...f.config, [field.name]: e.target.value }
                  }))}
                  className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 mb-2"
                />
              ))}
            </div>

            <button type="submit" className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700">
              Create Channel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="text-gray-400">Loading...</div>
      ) : channels.length === 0 ? (
        <div className="text-gray-400">No notification channels configured</div>
      ) : (
        <div className="grid gap-4">
          {channels.map(channel => (
            <div key={channel.id} className="bg-gray-800 rounded-lg p-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-bold">{channel.name}</h3>
                  <span className={`px-2 py-1 rounded text-sm ${
                    channel.channel_type === 'email' ? 'bg-blue-900' :
                    channel.channel_type === 'slack' ? 'bg-purple-900' :
                    channel.channel_type === 'discord' ? 'bg-indigo-900' :
                    'bg-gray-700'
                  }`}>
                    {channel.channel_type}
                  </span>
                  <span className={`ml-2 px-2 py-1 rounded text-sm ${
                    channel.is_enabled ? 'bg-green-900' : 'bg-red-900'
                  }`}>
                    {channel.is_enabled ? 'Enabled' : 'Disabled'}
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleTest(channel.id)}
                    className="px-3 py-1 bg-gray-700 rounded hover:bg-gray-600"
                  >
                    Test
                  </button>
                  <button
                    onClick={() => handleDelete(channel.id)}
                    className="px-3 py-1 bg-red-900 rounded hover:bg-red-800"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      </div>
      </main>
    </div>
  )
}