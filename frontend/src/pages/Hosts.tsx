import { useEffect, useState, FormEvent } from 'react'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { Plus, Trash2, RefreshCw, Server, CheckCircle, XCircle, Play } from 'lucide-react'
import Header from '@/components/Header'
import type { Host } from '@/types'

function Hosts() {
  const { logout, isConnected } = useAuth()
  const [hosts, setHosts] = useState<Host[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [showForm, setShowForm] = useState<boolean>(false)
  const [newHost, setNewHost] = useState<{ 
    name: string; 
    socket_path: string; 
    api_version: string 
  }>({ 
    name: '', 
    socket_path: 'unix:///var/run/docker.sock', 
    api_version: '1.41' 
  })
  const [error, setError] = useState<string>('')

  const fetchHosts = async () => {
    try {
      const data = await api.getHosts() as unknown
      setHosts(Array.isArray(data) ? data : (data as Record<string, any>)?.hosts || [])
    } catch (err) {
      console.error('Failed to fetch hosts:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHosts()
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    try {
      await api.createHost(newHost)
      setNewHost({ name: '', socket_path: 'unix:///var/run/docker.sock', api_version: '1.41' })
      setShowForm(false)
      fetchHosts()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add host')
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to remove host "${name}"?`)) return
    
    try {
      await api.deleteHost(id)
      fetchHosts()
    } catch (err) {
      console.error('Failed to delete host:', err)
    }
  }

  const handleTest = async (id: number) => {
    try {
      await api.testHost(id)
      fetchHosts()
    } catch (err) {
      console.error('Failed to test host:', err)
    }
  }

  const handleActivate = async (id: number) => {
    try {
      const result = await api.activateHost(id)
      if (result.connected) {
        alert(`Activated host: ${result.host}`)
        fetchHosts()
      } else {
        alert('Failed to activate host')
      }
    } catch (err) {
      console.error('Failed to activate host:', err)
    }
  }

  return (
    <div className="app-surface">
      <Header
        title="Docker Hosts"
        icon={<Server size={24} />}
        isConnected={isConnected}
        onLogout={logout}
      />

      <main className="app-main">
        <div className="flex justify-end mb-6">
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm text-white"
          >
            <Plus className="w-4 h-4" />
            {showForm ? 'Cancel' : 'Add Host'}
          </button>
        </div>
        {showForm && (
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-bold mb-4">Add Docker Host</h2>
            
            {error && (
              <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Host Name *
                </label>
                <input
                  type="text"
                  value={newHost.name}
                  onChange={(e) => setNewHost({ ...newHost, name: e.target.value })}
                  required
                  className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Production Server"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Docker Socket Path
                </label>
                <input
                  type="text"
                  value={newHost.socket_path}
                  onChange={(e) => setNewHost({ ...newHost, socket_path: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="unix:///var/run/docker.sock"
                />
                <p className="text-gray-500 text-sm mt-1">
                  Examples: unix:///var/run/docker.sock, tcp://192.168.1.100:2375
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  API Version
                </label>
                <input
                  type="text"
                  value={newHost.api_version}
                  onChange={(e) => setNewHost({ ...newHost, api_version: e.target.value })}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="1.41"
                />
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-500 px-4 py-2 rounded font-medium"
                >
                  Add Host
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading && hosts.length === 0 ? (
          <div className="text-center py-12 text-gray-400">Loading hosts...</div>
        ) : hosts.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Server className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <p>No Docker hosts configured</p>
            <p className="text-sm mt-2">Click "Add Host" to connect a Docker host</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {hosts.map(host => (
              <div key={host.id} className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${host.status === 'connected' ? 'bg-green-500' : 'bg-red-500'}`} />
                    <div>
                      <h3 className="text-lg font-bold">{host.name}</h3>
                      <p className="text-gray-400 text-sm">{host.status}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleActivate(host.id)}
                      className="p-2 hover:bg-gray-700 rounded text-green-500"
                      title="Activate Host"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleTest(host.id)}
                      className="p-2 hover:bg-gray-700 rounded"
                      title="Test Connection"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(host.id, host.name)}
                      className="p-2 hover:bg-gray-700 rounded text-red-500"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="text-sm text-gray-400 space-y-1">
                  <p><span className="text-gray-500">Socket:</span> {host.socket_path}</p>
                  <p><span className="text-gray-500">API:</span> {host.api_version}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default Hosts