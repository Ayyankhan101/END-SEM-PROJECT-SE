import { useEffect, useState, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
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
  Brain,
  TrendingDown,
  DollarSign,
  Download
} from 'lucide-react'
import ContainerCard from '@/components/ContainerCard'
import Header from '@/components/Header'
import DashboardCharts from '@/components/DashboardCharts'
import ThreeLoginBackground from '@/components/ThreeLoginBackground'
import type { Container as ContainerType } from '@/types'
import { formatSize } from '@/utils/format'

function formatBytes(bytes: number): string {
  return formatSize(bytes)
}

interface Stats {
  total: number;
  running: number;
  stopped: number;
  alerts: number;
}

interface DashboardMetricCardProps {
  label: string;
  value: string | number;
  detail: string;
  icon: ReactNode;
  accent: string;
  action?: ReactNode;
}

function DashboardMetricCard({ label, value, detail, icon, accent, action }: DashboardMetricCardProps) {
  return (
    <div className="dashboard-card stat-card">
      <div className="flex items-start justify-between gap-3">
        <div className={`flex h-11 w-11 items-center justify-center rounded-lg border ${accent}`}>
          {icon}
        </div>
        {action}
      </div>
      <div className="mt-5">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
        <p className="mt-1 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white">{value}</p>
        <p className="mt-2 text-xs text-[#6b7280] dark:text-[#9ca3af]">{detail}</p>
      </div>
    </div>
  )
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
  const [resourceSummary, setResourceSummary] = useState<any>(null)
  const [exportLoading, setExportLoading] = useState<boolean>(false)
  const [stats, setStats] = useState<Stats>({ 
    total: 0, 
    running: 0, 
    stopped: 0, 
    alerts: alerts?.length || 0 
  })

  const fetchResourceSummary = useCallback(async () => {
    try {
      const summary = await api.getResourceSummary()
      setResourceSummary(summary)
    } catch (err) {
      console.error('Error fetching resource summary:', err)
    }
  }, [])

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
      console.error('Error fetching containers:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleRefresh = useCallback(async () => {
    await api.syncContainers()
  }, [])

  // Initial load once, then WebSocket handles real-time CPU updates
  useEffect(() => {
    fetchContainers()
    fetchResourceSummary()
  }, [fetchContainers, fetchResourceSummary])

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
  const avgCpu = Math.max(Number(avgCpuRaw.toFixed(2)), 0.01)
  // avgCpu calculation without logging

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

  const handleExport = async (format: 'json' | 'csv') => {
    setExportLoading(true)
    try {
      const result = await api.exportMetrics(undefined, 24, format)
      if (format === 'json') {
        const blob = new Blob([JSON.stringify(result.jsonData || result.data, null, 2)], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = result.filename || 'metrics.json'
        a.click()
        URL.revokeObjectURL(url)
      } else {
        const blob = new Blob([result.csvData || result.data], { type: 'text/csv' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = result.filename || 'metrics.csv'
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (err) {
      console.error('Export failed:', err)
    } finally {
      setExportLoading(false)
    }
  }

  return (
    <div className="app-surface relative overflow-hidden">
      <div className="pointer-events-none fixed inset-0 z-0 opacity-[0.09] dark:opacity-[0.12] pink:opacity-[0.08]">
        <ThreeLoginBackground />
      </div>
      <Header 
        title="Dashboard" 
        icon={<Container size={24} />} 
        onRefresh={handleRefresh}
        isConnected={isConnected}
        onLogout={logout}
      />

      <main className="app-main z-10">
        <section className="dashboard-card mb-6 flex flex-col gap-4 overflow-hidden">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-4">
              <div className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-500 sm:flex">
                <Layers className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-500">Operations overview</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#111827] dark:text-[#e5e7eb]">Container fleet</h2>
                <p className="mt-1 text-sm text-[#6b7280] dark:text-[#d1d5db]">Search, filter, and operate Docker containers from one workspace.</p>
              </div>
            </div>
            <Link
              to="/containers/new"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-blue-500 to-violet-600 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-blue-500/15 transition hover:-translate-y-0.5"
            >
              <Plus className="h-4 w-4" />
              New Container
            </Link>
          </div>
        </section>

        <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <DashboardMetricCard
            label="Total Containers"
            value={stats.total}
            detail={`${filteredContainers.length} visible after filters`}
            icon={<Activity className="h-5 w-5" />}
            accent="border-blue-500/25 bg-blue-500/10 text-blue-500"
            action={
              <button
                onClick={toggleSelectAll}
                className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-blue-500 dark:hover:bg-white/10"
                title="Select all"
              >
                {selectedIds.size === filteredContainers.length && filteredContainers.length > 0 ? (
                  <CheckSquare className="h-5 w-5 text-blue-500" />
                ) : (
                  <SquareIcon className="h-5 w-5" />
                )}
              </button>
            }
          />
          <DashboardMetricCard
            label="Running"
            value={stats.running}
            detail="Containers accepting workload"
            icon={<Container className="h-5 w-5" />}
            accent="border-emerald-500/25 bg-emerald-500/10 text-emerald-500"
          />
          <DashboardMetricCard
            label="Stopped"
            value={stats.stopped}
            detail="Exited, paused, or unavailable"
            icon={<HardDrive className="h-5 w-5" />}
            accent="border-red-500/25 bg-red-500/10 text-red-500"
          />
          <DashboardMetricCard
            label="Avg CPU"
            value={`${avgCpu}%`}
            detail="Average across known samples"
            icon={<Cpu className="h-5 w-5" />}
            accent="border-violet-500/25 bg-violet-500/10 text-violet-500"
          />
        </div>

        {resourceSummary && (
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <DashboardMetricCard
              label="Memory Waste"
              value={`${resourceSummary.memory_waste_percent || 0}%`}
              detail={`${resourceSummary.idle_containers?.length || 0} idle containers`}
              icon={<TrendingDown className="h-5 w-5" />}
              accent="border-amber-500/25 bg-amber-500/10 text-amber-500"
            />
            <DashboardMetricCard
              label="Potential Savings"
              value={`$${(resourceSummary.potential_savings || 0).toFixed(2)}`}
              detail="From idle resources"
              icon={<DollarSign className="h-5 w-5" />}
              accent="border-green-500/25 bg-green-500/10 text-green-500"
            />
            <DashboardMetricCard
              label="CPU Usage"
              value={`${resourceSummary.total_cpu_usage?.toFixed(1) || 0}%`}
              detail="Total across running"
              icon={<Activity className="h-5 w-5" />}
              accent="border-blue-500/25 bg-blue-500/10 text-blue-500"
            />
            <DashboardMetricCard
              label="Memory Used"
              value={formatBytes(resourceSummary.total_memory_usage || 0)}
              detail={`of ${formatBytes(resourceSummary.total_memory_limit || 0)}`}
              icon={<HardDrive className="h-5 w-5" />}
              accent="border-purple-500/25 bg-purple-500/10 text-purple-500"
            />
          </div>
        )}

        <DashboardCharts containers={Array.isArray(containers) ? containers : []} />

        <div className="dashboard-card mb-6">
          <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search by name, id, image, status..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="theme-input py-2.5 pl-10 pr-4 text-sm"
              />
            </div>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="theme-input px-4 py-2.5 text-sm"
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
              className="theme-input px-4 py-2.5 text-sm"
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
              className={`rounded-lg px-4 py-2.5 text-sm font-semibold transition focus:outline-none focus:ring-4 focus:ring-blue-500/10 ${
                favoritesOnly 
                  ? 'bg-amber-500 text-white shadow-lg shadow-amber-500/20 hover:bg-amber-400' 
                  : 'border border-[#e5e7eb] bg-white text-[#6b7280] hover:bg-blue-50 hover:text-[#111827] dark:border-[#374151] dark:bg-[#111827] dark:text-[#d1d5db] dark:hover:bg-[#1f2937]'
              }`}
            >
              Favorites
            </button>
            <div className="relative group">
              <button
                disabled={exportLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-white px-4 py-2.5 text-sm font-semibold text-[#6b7280] transition hover:bg-blue-50 hover:text-[#111827] dark:border-[#374151] dark:bg-[#111827] dark:text-[#d1d5db] dark:hover:bg-[#1f2937] disabled:opacity-50"
              >
                <Download className="h-4 w-4" />
                Export
              </button>
              <div className="absolute right-0 top-full mt-1 hidden w-32 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg group-hover:block dark:border-[#374151] dark:bg-[#1f2937]">
                <button
                  onClick={() => handleExport('json')}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
                >
                  JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full px-4 py-2 text-left text-sm hover:bg-slate-100 dark:hover:bg-slate-700"
                >
                  CSV
                </button>
              </div>
            </div>
          </div>
        </div>

        {selectedIds.size > 0 && (
          <div className="fixed bottom-6 left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2 flex-wrap items-center justify-center gap-3 rounded-lg border border-slate-200 bg-white/92 p-3 shadow-2xl shadow-slate-300/50 backdrop-blur dark:border-white/10 dark:bg-slate-900/92 dark:shadow-black/40 lg:left-[calc(50%+9rem)]">
            <span className="text-sm font-medium text-slate-600 dark:text-slate-300">{selectedIds.size} selected</span>
            <button
              onClick={handleBulkStart}
              disabled={bulkLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-sm font-semibold text-emerald-500 transition hover:bg-emerald-500/20 disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Start
            </button>
            <button
              onClick={handleBulkStop}
              disabled={bulkLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-amber-500/10 px-3 py-2 text-sm font-semibold text-amber-500 transition hover:bg-amber-500/20 disabled:opacity-50"
            >
              <Square className="w-4 h-4" />
              Stop
            </button>
            <button
              onClick={handleBulkRestart}
              disabled={bulkLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-orange-500/10 px-3 py-2 text-sm font-semibold text-orange-500 transition hover:bg-orange-500/20 disabled:opacity-50"
            >
              <RotateCw className="w-4 h-4" />
              Restart
            </button>
            <button
              onClick={() => setShowDeleteModal(true)}
              disabled={bulkLoading}
              className="inline-flex items-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-sm font-semibold text-red-500 transition hover:bg-red-500/20 disabled:opacity-50"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
        )}

        {loading ? (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((item) => (
              <div key={item} className="h-48 animate-pulse rounded-lg border border-slate-200 bg-white dark:border-white/10 dark:bg-white/[0.04]" />
            ))}
          </div>
        ) : (
          <div className="container-scroll grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
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
          <div className="dashboard-card py-12 text-center text-slate-500">
            No containers found
          </div>
        )}

        {showDeleteModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm">
            <div className="max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-2xl dark:border-white/10 dark:bg-slate-900">
              <h3 className="mb-4 text-lg font-bold">Confirm Bulk Delete</h3>
              <p className="mb-6 text-slate-500 dark:text-slate-400">
                Are you sure you want to delete {selectedIds.size} container(s)? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="rounded-lg border border-slate-200 px-4 py-2 text-slate-600 transition hover:bg-slate-100 dark:border-white/10 dark:text-slate-300 dark:hover:bg-white/10"
                >
                  Cancel
                </button>
                <button
                  onClick={handleBulkDelete}
                  disabled={bulkLoading}
                  className="rounded-lg bg-red-500 px-4 py-2 font-semibold text-white transition hover:bg-red-400 disabled:opacity-50"
                >
                  {bulkLoading ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default Dashboard
