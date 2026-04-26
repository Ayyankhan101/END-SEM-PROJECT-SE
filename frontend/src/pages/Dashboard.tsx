import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { 
  Container, 
  Cpu, 
  HardDrive, 
  AlertTriangle, 
  RefreshCw, 
  Activity, 
  Search, 
  Plus, 
  Layers, 
  Server,
  Bell,
  Save,
  Box,
  FileText,
  Play,
  Square,
  RotateCw,
  Trash2,
  CheckSquare,
  Square as SquareIcon,
  Users as UsersIcon,
  AlertCircle,
  Brain
} from 'lucide-react'
import ContainerCard from '@/components/ContainerCard'
import Header from '@/components/Header'
import type { Container as ContainerType } from '@/types'

interface Stats {
  total: number;
  running: number;
  stopped: number;
  alerts: number;
}

function Dashboard() {
  const { containers, setContainers, logout, isConnected, alerts } = useAuth()
  const [loading, setLoading] = useState<boolean>(true)
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [groupFilter, setGroupFilter] = useState<string>('all')
  const [favoritesOnly, setFavoritesOnly] = useState<boolean>(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [showDeleteModal, setShowDeleteModal] = useState<boolean>(false)
  const [bulkLoading, setBulkLoading] = useState<boolean>(false)
  const [stats, setStats] = useState<Stats>({ 
    total: 0, 
    running: 0, 
    stopped: 0, 
    alerts: alerts?.length || 0 
  })

  const fetchContainers = useCallback(async () => {
    try {
      const data = await api.getContainers() as unknown
      const containerList = Array.isArray(data) ? data : (data as Record<string, any>)?.containers || []
      setContainers(containerList)
      setStats({
        total: containerList.length,
        running: containerList.filter((c: ContainerType) => c.status === 'running').length,
        stopped: containerList.filter((c: ContainerType) => c.status !== 'running').length,
        alerts: alerts?.length || 0
      })
    } catch (err) {
      console.error('Failed to fetch containers:', err)
    } finally {
      setLoading(false)
    }
  }, [setContainers])

  const handleRefresh = useCallback(async () => {
    await api.syncContainers()
    await fetchContainers()
  }, [fetchContainers])

  useEffect(() => {
    fetchContainers()
    const interval = setInterval(fetchContainers, 10000)
    return () => clearInterval(interval)
  }, [fetchContainers])

  const filteredContainers = useMemo(() => 
    Array.isArray(containers) 
      ? containers.filter((c: ContainerType) => {
          const matchesSearch = 
            c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            c.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
            c.image?.toLowerCase().includes(searchTerm.toLowerCase()) ||
            c.status?.toLowerCase().includes(searchTerm.toLowerCase())
          const matchesStatus = statusFilter === 'all' || c.status === statusFilter
          const matchesGroup = groupFilter === 'all' || (c as any).group === groupFilter
          const matchesFavorites = !favoritesOnly || (c as any).is_favorite === 1
          return matchesSearch && matchesStatus && matchesGroup && matchesFavorites
        }) 
      : []
  , [containers, searchTerm, statusFilter, groupFilter, favoritesOnly])

const avgCpuRaw = (
    (Array.isArray(containers) ? containers : [])
      .reduce((acc, c) => acc + (c.cpu_percent || 0), 0) / 
    ((Array.isArray(containers) ? containers : []).length || 1)
  )
  const avgCpu = Number(avgCpuRaw.toFixed(1))

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredContainers.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredContainers.map(c => c.id)))
    }
  }

  const handleBulkStart = async () => {
    setBulkLoading(true)
    try {
      await api.bulkStartContainers(Array.from(selectedIds))
      setSelectedIds(new Set())
      fetchContainers()
    } catch (err) {
      console.error('Bulk start failed:', err)
    } finally {
      setBulkLoading(false)
    }
  }

  const handleBulkStop = async () => {
    setBulkLoading(true)
    try {
      await api.bulkStopContainers(Array.from(selectedIds))
      setSelectedIds(new Set())
      fetchContainers()
    } catch (err) {
      console.error('Bulk stop failed:', err)
    } finally {
      setBulkLoading(false)
    }
  }

  const handleBulkRestart = async () => {
    setBulkLoading(true)
    try {
      await api.bulkRestartContainers(Array.from(selectedIds))
      setSelectedIds(new Set())
      fetchContainers()
    } catch (err) {
      console.error('Bulk restart failed:', err)
    } finally {
      setBulkLoading(false)
    }
  }

  const handleBulkDelete = async () => {
    setBulkLoading(true)
    try {
      await api.bulkDeleteContainers(Array.from(selectedIds))
      setSelectedIds(new Set())
      setShowDeleteModal(false)
      fetchContainers()
    } catch (err) {
      console.error('Bulk delete failed:', err)
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header 
        title="Dashboard" 
        icon={<Container size={24} />} 
        onRefresh={handleRefresh}
        isConnected={isConnected}
        onLogout={logout}
      />

      <div className="p-6">
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <button
                onClick={toggleSelectAll}
                className="p-1 hover:bg-gray-700 rounded"
                title="Select all"
              >
                {selectedIds.size === filteredContainers.length && filteredContainers.length > 0 ? (
                  <CheckSquare className="w-5 h-5 text-blue-500" />
                ) : (
                  <SquareIcon className="w-5 h-5 text-gray-500" />
                )}
              </button>
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
                <p className="text-2xl font-bold">{avgCpu}%</p>
                <p className="text-gray-400 text-sm">Avg CPU</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-6">
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name, id, image, status..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 pl-10 pr-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-white px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Status</option>
              <option value="running">Running</option>
              <option value="stopped">Stopped</option>
              <option value="paused">Paused</option>
              <option value="exited">Exited</option>
            </select>
            <select
              value={groupFilter}
              onChange={(e) => setGroupFilter(e.target.value)}
              className="bg-gray-800 border border-gray-700 text-white px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All Groups</option>
              <option value="web">Web</option>
              <option value="db">DB</option>
              <option value="backend">Backend</option>
              <option value="frontend">Frontend</option>
              <option value="cache">Cache</option>
              <option value="queue">Queue</option>
              <option value="dev">Dev</option>
              <option value="staging">Staging</option>
              <option value="prod">Prod</option>
            </select>
            <button
              onClick={() => setFavoritesOnly(!favoritesOnly)}
              className={`px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                favoritesOnly 
                  ? 'bg-yellow-600 hover:bg-yellow-500 text-white' 
                  : 'bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700'
              }`}
            >
              ★ Favorites
            </button>
          </div>
        </div>

        {selectedIds.size > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-gray-800 border border-gray-600 rounded-lg p-4 shadow-xl flex items-center gap-4 z-50">
            <span className="text-sm text-gray-300">{selectedIds.size} selected</span>
            <button
              onClick={handleBulkStart}
              disabled={bulkLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-green-600 hover:bg-green-500 rounded text-sm disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Start
            </button>
            <button
              onClick={handleBulkStop}
              disabled={bulkLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-yellow-600 hover:bg-yellow-500 rounded text-sm disabled:opacity-50"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>
            <button
              onClick={handleBulkRestart}
              disabled={bulkLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-sm disabled:opacity-50"
            >
              <RotateCw className="w-4 h-4" />
              Restart
            </button>
            <button
              onClick={() => setShowDeleteModal(true)}
              disabled={bulkLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-red-600 hover:bg-red-500 rounded text-sm disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading containers...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 container-scroll">
            {filteredContainers.map(container => (
              <ContainerCard 
                key={container.id} 
                container={container}
                selected={selectedIds.has(container.id)}
                onSelect={toggleSelect}
              />
            ))}
          </div>
        )}

        {!loading && filteredContainers.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            No containers found
          </div>
        )}

        {showDeleteModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg max-w-md">
              <h3 className="text-lg font-bold mb-4">Confirm Bulk Delete</h3>
              <p className="text-gray-400 mb-6">
                Are you sure you want to delete {selectedIds.size} container(s)? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkDelete}
                  disabled={bulkLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded disabled:opacity-50"
                >
                  {bulkLoading ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard