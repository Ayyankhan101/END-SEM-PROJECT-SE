import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../App'
import { getContainers } from '../services/api'
import { Container, Cpu, HardDrive, AlertTriangle, RefreshCw, Activity, Search } from 'lucide-react'
import ContainerCard from '../components/ContainerCard'
import MetricsChart from '../components/MetricsChart'

function Dashboard() {
  const { containers, setContainers, logout } = useAuth()
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [stats, setStats] = useState({ total: 0, running: 0, stopped: 0, alerts: 0 })

  const fetchContainers = async () => {
    try {
      const data = await getContainers()
      setContainers(data)
      setStats({
        total: data.length,
        running: data.filter(c => c.status === 'running').length,
        stopped: data.filter(c => c.status !== 'running').length,
        alerts: 0
      })
    } catch (err) {
      console.error('Failed to fetch containers:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchContainers()
    const interval = setInterval(fetchContainers, 10000)
    return () => clearInterval(interval)
  }, [])

  const filteredContainers = containers.filter(c => 
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.id.toLowerCase().includes(searchTerm.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Container className="w-8 h-8 text-blue-500" />
            <h1 className="text-xl font-bold">DockWatch</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <button onClick={fetchContainers} className="p-2 hover:bg-gray-700 rounded">
              <RefreshCw className="w-5 h-5" />
            </button>
            <Link to="/alerts" className="p-2 hover:bg-gray-700 rounded">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
            </Link>
            <Link to="/settings" className="p-2 hover:bg-gray-700 rounded">
              Settings
            </Link>
            <button onClick={logout} className="text-gray-400 hover:text-white">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="p-6">
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <Activity className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-gray-400 text-sm">Total Containers</p>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <Container className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">{stats.running}</p>
                <p className="text-gray-400 text-sm">Running</p>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <HardDrive className="w-8 h-8 text-red-500" />
              <div>
                <p className="text-2xl font-bold">{stats.stopped}</p>
                <p className="text-gray-400 text-sm">Stopped</p>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <Cpu className="w-8 h-8 text-purple-500" />
              <div>
                <p className="text-2xl font-bold">{Math.round(containers.reduce((acc, c) => acc + (c.cpu_percent || 0), 0) / (containers.length || 1))}%</p>
                <p className="text-gray-400 text-sm">Avg CPU</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search containers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 pl-10 pr-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading containers...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredContainers.map(container => (
              <ContainerCard key={container.id} container={container} />
            ))}
          </div>
        )}

        {!loading && filteredContainers.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            No containers found
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard