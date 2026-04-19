import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { 
  Container, 
  Plus, 
  Layers, 
  Server,
  Bell,
  Save,
  Box,
  FileText,
  Settings,
  Users as UsersIcon,
  Pencil,
  Trash2,
  ArrowLeft,
  AlertTriangle
} from 'lucide-react'

interface AlertRule {
  id: number
  container_id: string | null
  name: string
  cpu_threshold: number
  memory_threshold: number
  enabled: boolean
  created_at?: string
}

function AlertRules() {
  const { logout, isConnected } = useAuth()
  const [rules, setRules] = useState<AlertRule[]>([])
  const [containers, setContainers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null)
  const [formData, setFormData] = useState({ 
    name: '', 
    container_id: '', 
    cpu_threshold: 80, 
    memory_threshold: 80,
    enabled: true 
  })

  const fetchData = async () => {
    try {
      const [rulesData, containersData] = await Promise.all([
        api.getAlertRules(),
        api.getContainers()
      ])
      setRules(rulesData)
      setContainers(containersData)
    } catch (err) {
      console.error('Failed to fetch data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const data = {
        name: formData.name,
        container_id: formData.container_id || undefined,
        cpu_threshold: formData.cpu_threshold,
        memory_threshold: formData.memory_threshold,
        enabled: formData.enabled
      }
      
      if (editingRule) {
        await api.updateAlertRule(editingRule.id, data)
      } else {
        await api.createAlertRule(data)
      }
      setShowModal(false)
      setEditingRule(null)
      setFormData({ name: '', container_id: '', cpu_threshold: 80, memory_threshold: 80, enabled: true })
      fetchData()
    } catch (err) {
      console.error('Failed to save rule:', err)
    }
  }

  const handleDelete = async (ruleId: number) => {
    if (!confirm('Delete this alert rule?')) return
    try {
      await api.deleteAlertRule(ruleId)
      fetchData()
    } catch (err) {
      console.error('Failed to delete rule:', err)
    }
  }

  const openEdit = (rule: AlertRule) => {
    setEditingRule(rule)
    setFormData({
      name: rule.name,
      container_id: rule.container_id || '',
      cpu_threshold: rule.cpu_threshold,
      memory_threshold: rule.memory_threshold,
      enabled: rule.enabled
    })
    setShowModal(true)
  }

  const getContainerName = (containerId: string | null) => {
    if (!containerId) return 'Global (Default)'
    const container = containers.find(c => c.id === containerId)
    return container ? container.name : containerId
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="p-2 hover:bg-gray-700 rounded">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <AlertTriangle className="w-8 h-8 text-yellow-500" />
            <h1 className="text-xl font-bold">Alert Rules</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <Link to="/stacks" className="p-2 hover:bg-gray-700 rounded">
              <Layers className="w-5 h-5" />
            </Link>
            <Link to="/hosts" className="p-2 hover:bg-gray-700 rounded">
              <Server className="w-5 h-5" />
            </Link>
            <Link to="/alerts" className="p-2 hover:bg-gray-700 rounded">
              <Bell className="w-5 h-5 text-yellow-500" />
            </Link>
            <Link to="/audit" className="p-2 hover:bg-gray-700 rounded" title="Audit Logs">
              <FileText className="w-5 h-5" />
            </Link>
            <Link to="/notifications" className="p-2 hover:bg-gray-700 rounded" title="Notifications">
              <Bell className="w-5 h-5" />
            </Link>
            <Link to="/backup" className="p-2 hover:bg-gray-700 rounded" title="Backup">
              <Save className="w-5 h-5" />
            </Link>
            <Link to="/docker" className="p-2 hover:bg-gray-700 rounded" title="Docker Resources">
              <Box className="w-5 h-5" />
            </Link>
            <Link to="/settings" className="p-2 hover:bg-gray-700 rounded">
              Settings
            </Link>
            <Link to="/users" className="p-2 hover:bg-gray-700 rounded" title="User Management">
              <UsersIcon className="w-5 h-5" />
            </Link>
            <span className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${
              isConnected 
                ? 'bg-green-900/50 text-green-400' 
                : 'bg-red-900/50 text-red-400'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            <button onClick={logout} className="text-gray-400 hover:text-white">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="p-6">
        <div className="flex justify-between items-center mb-6">
          <p className="text-gray-400">Configure CPU/memory thresholds per-container or globally</p>
          <button
            onClick={() => {
              setEditingRule(null)
              setFormData({ name: '', container_id: '', cpu_threshold: 80, memory_threshold: 80, enabled: true })
              setShowModal(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Rule
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Name</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Container</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">CPU Threshold</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Memory Threshold</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                      No alert rules configured. Global defaults from Settings will be used.
                    </td>
                  </tr>
                ) : (
                  rules.map(rule => (
                    <tr key={rule.id} className="border-t border-gray-700">
                      <td className="px-4 py-3">{rule.name}</td>
                      <td className="px-4 py-3">{getContainerName(rule.container_id)}</td>
                      <td className="px-4 py-3">{rule.cpu_threshold}%</td>
                      <td className="px-4 py-3">{rule.memory_threshold}%</td>
                      <td className="px-4 py-3">
                        <span className={`text-xs px-2 py-1 rounded ${rule.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                          {rule.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => openEdit(rule)}
                          className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(rule.id)}
                          className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-red-400 ml-2"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg w-[480px]">
              <h3 className="text-lg font-bold mb-4">
                {editingRule ? 'Edit Alert Rule' : 'Create Alert Rule'}
              </h3>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Rule Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    required
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Container (leave empty for global)</label>
                  <select
                    value={formData.container_id}
                    onChange={(e) => setFormData({ ...formData, container_id: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  >
                    <option value="">Global (Default)</option>
                    {containers.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">CPU Threshold (%)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={formData.cpu_threshold}
                      onChange={(e) => setFormData({ ...formData, cpu_threshold: Number(e.target.value) })}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm text-gray-400 mb-1">Memory Threshold (%)</label>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      value={formData.memory_threshold}
                      onChange={(e) => setFormData({ ...formData, memory_threshold: Number(e.target.value) })}
                      className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    />
                  </div>
                </div>
                <div className="mb-4 flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enabled"
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <label htmlFor="enabled" className="text-sm text-gray-300">Enabled</label>
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false)
                      setEditingRule(null)
                    }}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded"
                  >
                    {editingRule ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AlertRules