import { useEffect, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { ArrowLeft, Play, Pause, RotateCw, Cpu, HardDrive, FileText, Terminal as TerminalIcon, Network, Settings as SettingsIcon, Plus, Trash2, Activity, Box, CheckCircle2, Clock3 } from 'lucide-react'
import MetricsChart from '@/components/MetricsChart'
import LogViewer from '@/components/LogViewer'
import Header from '@/components/Header'
import type { ContainerDetail as ContainerDetailType, Metric } from '@/types'

interface StatCardProps {
  icon: ReactNode;
  label: string;
  value: string;
  accent: string;
  detail?: string;
}

function StatCard({ icon, label, value, accent, detail }: StatCardProps) {
  return (
    <div className="dashboard-card stat-card group">
      <div className="flex items-center justify-between gap-4">
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-lg border ${accent}`}>
          {icon}
        </div>
        <div className="h-9 w-16 rounded-full bg-white/[0.03] blur-xl transition group-hover:bg-white/[0.06]" />
      </div>
      <div className="mt-5">
        <p className="text-sm font-medium text-slate-400">{label}</p>
        <p className="mt-1 text-2xl font-semibold tracking-tight text-white">{value}</p>
        {detail && <p className="mt-2 text-xs text-slate-500">{detail}</p>}
      </div>
    </div>
  )
}

function ContainerDetail() {
  const { id } = useParams<{ id: string }>()
  const { socket, logout, isConnected } = useAuth()
  const [container, setContainer] = useState<ContainerDetailType | null>(null)
  const [metrics, setMetrics] = useState<Metric[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [activeTab, setActiveTab] = useState<string>('overview')
  const [timeRange, setTimeRange] = useState<number>(24)
  const [showEnvModal, setShowEnvModal] = useState(false)
  const [showPortModal, setShowPortModal] = useState(false)
  const [newEnvKey, setNewEnvKey] = useState('')
  const [newEnvValue, setNewEnvValue] = useState('')
  const [newPortContainer, setNewPortContainer] = useState('')
  const [newPortHost, setNewPortHost] = useState('') // hours

  const containerId = id || ''

  const fetchData = useCallback(async () => {
    if (!id) return
    try {
      const [containerData, metricsData] = await Promise.all([
        api.getContainer(id),
        api.getMetricsHistory(id, timeRange)
      ])
      setContainer(containerData)
      setMetrics(metricsData?.metrics || [])
    } catch (err) {
      console.error('Failed to fetch container:', err)
    } finally {
      setLoading(false)
    }
  }, [id, timeRange])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  useEffect(() => {
    if (!socket) return
    
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'metrics' && data.container_id === id) {
          setMetrics(prev => {
            const currentMetrics = Array.isArray(prev) ? prev : []
            const newMetric: Metric = {
              id: Date.now(),
              container_id: id || '',
              cpu_percent: data.stats?.cpu_percent,
              memory_percent: data.stats?.memory_percent,
              timestamp: data.timestamp
            }
            return [...currentMetrics.slice(-99), newMetric]
          })
        }
      } catch (err) {
        // Not JSON or other error
      }
    }

    socket.addEventListener('message', handleMessage)
    return () => socket.removeEventListener('message', handleMessage)
  }, [socket, id])

  const handleRestart = async () => {
    if (!id) return
    try {
      await api.restartContainer(id)
    } catch (err) {
      console.error('Restart failed:', err)
    }
  }

  const handlePause = async () => {
    if (!id) return
    try {
      if (container?.status === 'running') {
        await api.pauseContainer(id)
      } else {
        await api.unpauseContainer(id)
      }
    } catch (err) {
      console.error('Pause failed:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 p-6 text-white">
        <div className="mx-auto max-w-7xl space-y-6">
          <div className="h-5 w-40 animate-pulse rounded bg-white/10" />
          <div className="dashboard-card">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
              <div className="space-y-4">
                <div className="h-10 w-72 animate-pulse rounded bg-white/10" />
                <div className="h-4 w-96 max-w-full animate-pulse rounded bg-white/10" />
              </div>
              <div className="flex gap-3">
                <div className="h-10 w-28 animate-pulse rounded-lg bg-white/10" />
                <div className="h-10 w-28 animate-pulse rounded-lg bg-white/10" />
                <div className="h-10 w-28 animate-pulse rounded-lg bg-white/10" />
              </div>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="h-36 animate-pulse rounded-lg bg-white/10" />
            <div className="h-36 animate-pulse rounded-lg bg-white/10" />
            <div className="h-36 animate-pulse rounded-lg bg-white/10" />
          </div>
          <div className="h-96 animate-pulse rounded-lg bg-white/10" />
        </div>
      </div>
    )
  }

  if (!container) {
    return <div className="min-h-screen bg-gray-900 text-white p-6">Container not found</div>
  }

  const isRunning = container.status === 'running'
  const currentMetrics = Array.isArray(metrics) ? metrics : []
  const latestMetric = currentMetrics[currentMetrics.length - 1]
  const currentCpu = latestMetric?.cpu_percent ?? 0
  const currentMemory = latestMetric?.memory_percent ?? 0
  const shortContainerId = container.id?.slice(0, 12) || containerId.slice(0, 12)
  const lastUpdated = latestMetric?.timestamp
    ? new Intl.DateTimeFormat(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).format(new Date(latestMetric.timestamp))
    : 'Waiting for live data'
  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Activity className="h-4 w-4" /> },
    { id: 'logs', label: 'Logs', icon: <FileText className="h-4 w-4" /> },
    { id: 'ports', label: 'Ports', icon: <Network className="h-4 w-4" /> },
    { id: 'env', label: 'Environment', icon: <SettingsIcon className="h-4 w-4" /> }
  ]

  return (
    <div className="min-h-screen bg-slate-50 text-slate-950 dark:bg-slate-950 dark:text-white">
      <Header
        title="Container Details"
        icon={<Box size={24} />}
        isConnected={isConnected}
        onLogout={logout}
      />
      <main className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:ml-72 lg:px-8">
        <Link to="/" className="mb-6 inline-flex items-center gap-2 text-sm font-medium text-slate-400 transition hover:text-white">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <section className="dashboard-card mb-6 overflow-hidden">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-cyan-400/20 bg-cyan-400/10 text-cyan-300">
                  <Box className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3">
                    <h1 className="truncate text-2xl font-semibold tracking-tight text-white sm:text-3xl">{container.name}</h1>
                    <span className={`status-badge ${isRunning ? 'status-badge-running' : 'status-badge-stopped'}`}>
                      <span className="h-2 w-2 rounded-full bg-current" />
                      {container.status}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-sm text-slate-400">{container.image}</p>
                </div>
              </div>
              <div className="mt-5 grid gap-3 text-xs text-slate-400 sm:grid-cols-2">
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                  <span className="block text-slate-500">Container ID</span>
                  <span className="font-mono text-slate-200">{shortContainerId}</span>
                </div>
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                  <span className="block text-slate-500">Last sample</span>
                  <span className="font-mono text-slate-200">{lastUpdated}</span>
                </div>
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-right dark:border-white/10 dark:bg-white/[0.03]">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-500">Samples</p>
              <p className="mt-1 text-2xl font-semibold text-slate-950 dark:text-white">{currentMetrics.length}</p>
            </div>
          </div>
        </section>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <StatCard
            icon={<Cpu className="h-5 w-5" />}
            label="CPU Usage"
            value={`${currentCpu.toFixed(1)}%`}
            detail="Latest container sample"
            accent="border-indigo-400/25 bg-indigo-400/10 text-indigo-300"
          />
          <StatCard
            icon={<HardDrive className="h-5 w-5" />}
            label="Memory Usage"
            value={`${currentMemory.toFixed(1)}%`}
            detail="Latest container sample"
            accent="border-emerald-400/25 bg-emerald-400/10 text-emerald-300"
          />
          <StatCard
            icon={isRunning ? <CheckCircle2 className="h-5 w-5" /> : <Clock3 className="h-5 w-5" />}
            label="Runtime Status"
            value={container.status}
            detail={isRunning ? 'Accepting live metrics' : 'Metrics may be paused'}
            accent={isRunning ? 'border-emerald-400/25 bg-emerald-400/10 text-emerald-300' : 'border-rose-400/25 bg-rose-400/10 text-rose-300'}
          />
        </div>

        <div className="mb-5">
          <div className="flex flex-col gap-4 rounded-lg border border-white/10 bg-white/[0.03] p-2 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex gap-1 overflow-x-auto">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`tab-button ${activeTab === tab.id ? 'tab-button-active' : ''}`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
            {activeTab === 'overview' && (
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(Number(e.target.value))}
                className="rounded-lg border border-white/10 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none transition focus:border-indigo-400"
              >
                <option value={1}>Last 1 hour</option>
                <option value={6}>Last 6 hours</option>
                <option value={24}>Last 24 hours</option>
                <option value={72}>Last 3 days</option>
                <option value={168}>Last 7 days</option>
              </select>
            )}
          </div>
        </div>

        {activeTab === 'overview' && (
          <div className="tab-panel">
            <MetricsChart data={metrics} title={`Resource Usage - Last ${timeRange}h`} />
          </div>
        )}

        {activeTab === 'logs' && id && (
          <div className="tab-panel">
            <LogViewer containerId={id} />
          </div>
        )}

        {activeTab === 'ports' && (
          <div className="dashboard-card tab-panel">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Networking</p>
                <h3 className="mt-1 text-lg font-semibold text-white">Port Mappings</h3>
              </div>
              <button
                onClick={() => setShowPortModal(true)}
                className="action-button action-button-neutral sm:w-auto"
              >
                <Plus className="w-4 h-4" />
                Add Port
              </button>
            </div>
            {(container as any)?.network_settings?.Ports && Object.keys((container as any).network_settings.Ports).length > 0 ? (
              <div className="overflow-x-auto rounded-lg border border-white/10">
                <table className="w-full min-w-[640px] text-sm">
                <thead className="bg-white/[0.04] text-slate-400">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Container Port</th>
                    <th className="px-4 py-3 text-left font-medium">Host Port</th>
                    <th className="px-4 py-3 text-left font-medium">Protocol</th>
                    <th className="px-4 py-3 text-left font-medium">Status</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries((container as any)?.network_settings?.Ports || {}).map(([port, binding]: [string, any]) => (
                    <tr key={port} className="border-t border-white/10 text-slate-200 transition hover:bg-white/[0.03]">
                      <td className="px-4 py-3 font-mono">{port}</td>
                      <td className="px-4 py-3 font-mono">{binding?.[0]?.HostPort || '-'}</td>
                      <td className="px-4 py-3 uppercase text-slate-400">{port.split('/')[1] || 'tcp'}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${binding ? 'bg-emerald-400/10 text-emerald-300 ring-1 ring-emerald-400/20' : 'bg-slate-500/10 text-slate-400 ring-1 ring-slate-500/20'}`}>
                          {binding ? 'Bound' : 'Not Bound'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={async () => {
                            const currentPorts = (container as any).network_settings?.Ports || {}
                            const portObj: Record<string, number> = {}
                            Object.entries(currentPorts).forEach(([k, v]: [string, any]) => {
                              if (v && v[0] && v[0].HostPort && k !== port) portObj[k.split('/')[0]] = parseInt(v[0].HostPort)
                            })
                            try {
                              await api.updateContainerPorts(containerId, portObj)
                              fetchData()
                            } catch (err) {
                              console.error('Failed to delete port:', err)
                            }
                          }}
                          className="rounded-md p-1.5 text-rose-400 transition hover:bg-rose-400/10 hover:text-rose-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-white/10 px-4 py-8 text-center text-slate-400">No ports exposed</p>
            )}
          </div>
        )}

        {activeTab === 'env' && (
          <div className="dashboard-card tab-panel">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Configuration</p>
                <h3 className="mt-1 text-lg font-semibold text-white">Environment Variables</h3>
              </div>
              <button
                onClick={() => setShowEnvModal(true)}
                className="action-button action-button-neutral sm:w-auto"
              >
                <Plus className="w-4 h-4" />
                Add Variable
              </button>
            </div>
            {(container as any)?.config?.Env ? (
              <div className="overflow-x-auto rounded-lg border border-white/10">
                <table className="w-full min-w-[640px] text-sm">
                <thead className="bg-white/[0.04] text-slate-400">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Variable</th>
                    <th className="px-4 py-3 text-left font-medium">Value</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {((container as any)?.config?.Env as string[] || []).map((env: string, idx: number) => {
                    const [key, ...valueParts] = env.split('=')
                    return (
                      <tr key={idx} className="border-t border-white/10 text-slate-200 transition hover:bg-white/[0.03]">
                        <td className="px-4 py-3 font-mono text-indigo-300">{key}</td>
                        <td className="break-all px-4 py-3 font-mono text-slate-300">{valueParts.join('=')}</td>
                        <td className="px-4 py-3 text-right">
                          <button
                            onClick={async () => {
                              const currentEnv = ((container as any).config?.Env || []).map((e: string) => {
                                const [k, ...v] = e.split('=')
                                return { key: k, value: v.join('=') }
                              })
                              const filtered = currentEnv.filter((e: any) => e.key !== key)
                              const envObj: Record<string, string> = {}
                              filtered.forEach((e: any) => { envObj[e.key] = e.value })
                              try {
                                await api.updateContainerEnv(containerId, envObj)
                                fetchData()
                              } catch (err) {
                                console.error('Failed to delete env:', err)
                              }
                            }}
                            className="rounded-md p-1.5 text-rose-400 transition hover:bg-rose-400/10 hover:text-rose-300"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
              </div>
            ) : (
              <p className="rounded-lg border border-dashed border-white/10 px-4 py-8 text-center text-slate-400">No environment variables</p>
            )}
          </div>
        )}

        {showEnvModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg w-96">
              <h3 className="text-lg font-bold mb-4">Add Environment Variable</h3>
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Key</label>
                <input
                  type="text"
                  value={newEnvKey}
                  onChange={(e) => setNewEnvKey(e.target.value.toUpperCase())}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  placeholder="MY_VARIABLE"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Value</label>
                <input
                  type="text"
                  value={newEnvValue}
                  onChange={(e) => setNewEnvValue(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  placeholder="value"
                />
              </div>
              <p className="text-yellow-400 text-sm mb-4">Changes apply immediately to running container</p>
              <div className="flex justify-end gap-3">
                <button onClick={() => { setShowEnvModal(false); setNewEnvKey(''); setNewEnvValue('') }} className="px-4 py-2 bg-gray-700 rounded">Cancel</button>
                <button
                  onClick={async () => {
                    if (!newEnvKey || !newEnvValue || !id) return
                    const currentEnv = ((container as any).config?.Env || []).map((e: string) => {
                      const [k, ...v] = e.split('=')
                      return { key: k, value: v.join('=') }
                    })
                    const existing = currentEnv.find((e: any) => e.key === newEnvKey)
                    if (existing) existing.value = newEnvValue
                    else currentEnv.push({ key: newEnvKey, value: newEnvValue })
                    const envObj: Record<string, string> = {}
                    currentEnv.forEach((e: any) => { envObj[e.key] = e.value })
                    try {
                      await api.updateContainerEnv(containerId, envObj)
                      setShowEnvModal(false)
                      setNewEnvKey('')
                      setNewEnvValue('')
                      fetchData()
                    } catch (err) {
                      console.error('Failed to update env:', err)
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        )}

        {showPortModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg w-96">
              <h3 className="text-lg font-bold mb-4">Add Port Mapping</h3>
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Container Port</label>
                <input
                  type="number"
                  value={newPortContainer}
                  onChange={(e) => setNewPortContainer(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  placeholder="80"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm text-gray-400 mb-1">Host Port</label>
                <input
                  type="number"
                  value={newPortHost}
                  onChange={(e) => setNewPortHost(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  placeholder="8080"
                />
              </div>
              <p className="text-yellow-400 text-sm mb-4">Changes apply immediately to running container</p>
              <div className="flex justify-end gap-3">
                <button onClick={() => { setShowPortModal(false); setNewPortContainer(''); setNewPortHost('') }} className="px-4 py-2 bg-gray-700 rounded">Cancel</button>
                <button
                  onClick={async () => {
                    if (!newPortContainer || !newPortHost || !id) return
                    const currentPorts = (container as any).network_settings?.Ports || {}
                    const portObj: Record<string, number> = {}
                    Object.entries(currentPorts).forEach(([k, v]: [string, any]) => {
                      if (v && v[0] && v[0].HostPort) portObj[k.split('/')[0]] = parseInt(v[0].HostPort)
                    })
                    portObj[newPortContainer] = parseInt(newPortHost)
                    try {
                      await api.updateContainerPorts(containerId, portObj)
                      setShowPortModal(false)
                      setNewPortContainer('')
                      setNewPortHost('')
                      fetchData()
                    } catch (err) {
                      console.error('Failed to update ports:', err)
                    }
                  }}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded"
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default ContainerDetail
