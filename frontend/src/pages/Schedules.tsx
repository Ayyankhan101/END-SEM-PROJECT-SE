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
  Clock,
  Play,
  Square,
  RotateCw
} from 'lucide-react'
import Header from '@/components/Header'

interface Schedule {
  id: number
  container_id: string
  container_name: string
  action: string
  time: string
  enabled: boolean
  created_at?: string
}

function Schedules() {
  const { logout, isConnected } = useAuth()
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [containers, setContainers] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingSchedule, setEditingSchedule] = useState<Schedule | null>(null)
  const [formData, setFormData] = useState({ container_id: '', action: 'start', time: '09:00' })
  const [isLoading, setIsLoading] = useState(false)

  const fetchData = async () => {
    try {
      const [schedulesData, containersData] = await Promise.all([
        api.getSchedules(),
        api.getContainers()
      ])
      setSchedules(schedulesData)
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
    setIsLoading(true)
    try {
      if (editingSchedule) {
        await api.updateSchedule(editingSchedule.id, {
          action: formData.action,
          time: formData.time
        })
      } else {
        await api.createSchedule(formData)
      }
      setShowModal(false)
      setEditingSchedule(null)
      setFormData({ container_id: '', action: 'start', time: '09:00' })
      fetchData()
    } catch (err) {
      console.error('Failed to save schedule:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (scheduleId: number) => {
    if (!confirm('Delete this schedule?')) return
    try {
      await api.deleteSchedule(scheduleId)
      fetchData()
    } catch (err) {
      console.error('Failed to delete schedule:', err)
    }
  }

  const handleToggle = async (schedule: Schedule) => {
    try {
      await api.updateSchedule(schedule.id, { enabled: !schedule.enabled })
      fetchData()
    } catch (err) {
      console.error('Failed to toggle schedule:', err)
    }
  }

  const openEdit = (schedule: Schedule) => {
    setEditingSchedule(schedule)
    setFormData({
      container_id: schedule.container_id,
      action: schedule.action,
      time: schedule.time
    })
    setShowModal(true)
  }

  const actionIcon = (action: string) => {
    switch (action) {
      case 'start': return <Play className="w-4 h-4 text-green-400" />
      case 'stop': return <Square className="w-4 h-4 text-red-400" />
      case 'restart': return <RotateCw className="w-4 h-4 text-yellow-400" />
      default: return null
    }
  }

  return (
    <div className="app-surface">
      <Header
        title="Scheduled Actions"
        icon={<Clock size={24} />}
        onRefresh={fetchData}
        isConnected={isConnected}
        onLogout={logout}
      />

      <main className="app-main">
        <div className="flex justify-between items-center mb-6">
          <p className="text-gray-400">Automate container actions at specific times daily</p>
          <button
            onClick={() => {
              setEditingSchedule(null)
              setFormData({ container_id: '', action: 'start', time: '09:00' })
              setShowModal(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm"
          >
            <Plus className="w-4 h-4" />
            Add Schedule
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Container</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Action</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Time</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Status</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {schedules.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-400">
                      No schedules configured. Create one to automate container actions.
                    </td>
                  </tr>
                ) : (
                  schedules.map(schedule => (
                    <tr key={schedule.id} className="border-t border-gray-700">
                      <td className="px-4 py-3">{schedule.container_name}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {actionIcon(schedule.action)}
                          <span className="capitalize">{schedule.action}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono">{schedule.time}</td>
                      <td className="px-4 py-3">
                        <button
                          onClick={() => handleToggle(schedule)}
                          className={`text-xs px-2 py-1 rounded ${schedule.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}
                        >
                          {schedule.enabled ? 'Enabled' : 'Disabled'}
                        </button>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => openEdit(schedule)}
                          className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(schedule.id)}
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
            <div className="bg-gray-800 p-6 rounded-lg w-96">
              <h3 className="text-lg font-bold mb-4">
                {editingSchedule ? 'Edit Schedule' : 'Create Schedule'}
              </h3>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Container</label>
                  <select
                    value={formData.container_id}
                    onChange={(e) => setFormData({ ...formData, container_id: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    required
                    disabled={!!editingSchedule}
                  >
                    <option value="">Select container</option>
                    {containers.map(c => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Action</label>
                  <select
                    value={formData.action}
                    onChange={(e) => setFormData({ ...formData, action: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  >
                    <option value="start">Start</option>
                    <option value="stop">Stop</option>
                    <option value="restart">Restart</option>
                  </select>
                </div>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Time (HH:MM)</label>
                  <input
                    type="time"
                    value={formData.time}
                    onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    required
                  />
                </div>
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false)
                      setEditingSchedule(null)
                    }}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded"
                  >
                    {editingSchedule ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default Schedules