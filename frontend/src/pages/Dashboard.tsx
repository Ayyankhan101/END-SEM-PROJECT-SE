import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import {
  Container,
  Cpu,
  HardDrive,
  Activity,
  Search,
  Plus,
  Play,
  Square,
  RotateCw,
  Trash2,
  Download
} from 'lucide-react'

import ContainerCard from '@/components/ContainerCard'
import DashboardCharts from '@/components/DashboardCharts'
import Header from '@/components/Header'
import type { Container as ContainerType } from '@/types'
import { formatSize } from '@/utils/format'

function formatBytes(bytes: number): string {
  return formatSize(bytes)
}

interface Stats {
  total: number
  running: number
  stopped: number
  alerts: number
}

function Dashboard() {
  const { containers, setContainers, logout, isConnected } = useAuth()

  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [groupFilter, setGroupFilter] = useState('all')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [bulkLoading, setBulkLoading] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [resourceSummary, setResourceSummary] = useState<any>(null)
  const [exportLoading, setExportLoading] = useState(false)

  const [stats, setStats] = useState<Stats>({
    total: 0,
    running: 0,
    stopped: 0,
    alerts: 0
  })

  const fetchResourceSummary = useCallback(async () => {
    try {
      const summary = await api.getResourceSummary()
      setResourceSummary(summary)
    } catch (err) {
      console.error(err)
    }
  }, [])

  const fetchContainers = useCallback(async () => {
    try {
      const response = await api.getContainers()
      const data = Array.isArray(response) ? response : (response as any)?.containers || []

      setContainers(data)

      setStats({
        total: data.length,
        running: data.filter((c: any) => c?.status === 'running').length,
        stopped: data.filter((c: any) => c?.status !== 'running').length,
        alerts: 0
      })
    } catch (err) {
      console.error('Failed to fetch containers:', err)
    } finally {
      setLoading(false)
    }
  }, [setContainers])

useEffect(() => {
  fetchContainers()
  fetchResourceSummary()

  const interval = setInterval(fetchContainers, 10000)

  return () => clearInterval(interval)
}, [fetchContainers, fetchResourceSummary])

  const filteredContainers = Array.isArray(containers)
    ? containers.filter((c: ContainerType) =>
        (c.name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.id || '').toLowerCase().includes(searchTerm.toLowerCase())
      )
    : []

  const avgCpu =
    (Array.isArray(containers) ? containers : []).reduce(
      (acc, c) => acc + (c.cpu_percent || 0),
      0
    ) / ((containers?.length || 1))

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      newSet.has(id) ? newSet.delete(id) : newSet.add(id)
      return newSet
    })
  }

  const handleBulkStart = async () => {
    setBulkLoading(true)
    try {
      await api.bulkStartContainers(Array.from(selectedIds))
      setSelectedIds(new Set())
      fetchContainers()
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
    } finally {
      setBulkLoading(false)
    }
  }

  const handleExport = async (format: 'json' | 'csv') => {
    setExportLoading(true)
    try {
      const result = await api.exportMetrics(undefined, 24, format)

      const blob = new Blob(
        [format === 'json'
          ? JSON.stringify(result.jsonData || result.data, null, 2)
          : result.csvData || result.data],
        { type: format === 'json' ? 'application/json' : 'text/csv' }
      )

      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.filename || `export.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExportLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-white">
      <Header
        title="Fleet Overview"
        icon={<Activity size={24} />}
        onRefresh={fetchContainers}
        isConnected={isConnected}
        onLogout={logout}
      />

      <main className="max-w-7xl mx-auto px-4 py-6">

        <div className="grid grid-cols-4 gap-4 mb-6">
          <div>{stats.total}</div>
          <div>{stats.running}</div>
          <div>{stats.stopped}</div>
          <div>{avgCpu.toFixed(1)}%</div>
        </div>

        <DashboardCharts containers={Array.isArray(containers) ? containers : []} />

        <div className="flex gap-2 my-4">
          <input
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="border p-2"
            placeholder="Search..."
          />

          <Link to="/containers/new">Create</Link>
        </div>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            {filteredContainers.map(c => (
              <ContainerCard key={c.id} container={c} />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default Dashboard