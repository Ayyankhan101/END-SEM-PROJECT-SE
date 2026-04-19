import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { ArrowLeft, Play, Pause, RotateCw, Cpu, HardDrive, FileText, Terminal as TerminalIcon, Network, Settings as SettingsIcon, Plus, Trash2, X } from 'lucide-react'
import MetricsChart from '@/components/MetricsChart'
import LogViewer from '@/components/LogViewer'
import type { ContainerDetail as ContainerDetailType, Metric } from '@/types'

function ContainerDetail() {
  const { id } = useParams<{ id: string }>()
  const { socket } = useAuth()
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
    return <div className="min-h-screen bg-gray-900 text-white p-6">Loading...</div>
  }

  if (!container) {
    return <div className="min-h-screen bg-gray-900 text-white p-6">Container not found</div>
  }

  const isRunning = container.status === 'running'
  const currentMetrics = Array.isArray(metrics) ? metrics : []

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">{container.name}</h1>
            <p className="text-gray-400 font-mono text-sm">{container.id}</p>
            <p className="text-gray-500 text-sm">{container.image}</p>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/container/${id}/terminal`}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
            >
              <TerminalIcon className="w-4 h-4" />
              Terminal
            </Link>
            <button
              onClick={handleRestart}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
            >
              <RotateCw className="w-4 h-4" />
              Restart
            </button>
            <button
              onClick={handlePause}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
            >
              {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {isRunning ? 'Pause' : 'Resume'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <Cpu className="w-8 h-8 text-blue-500" />
              <div>
                <p className="text-2xl font-bold">
                  {currentMetrics.length > 0 ? Math.round(currentMetrics[currentMetrics.length-1]?.cpu_percent || 0) : 0}%
                </p>
                <p className="text-gray-400 text-sm">CPU Usage</p>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <HardDrive className="w-8 h-8 text-green-500" />
              <div>
                <p className="text-2xl font-bold">
                  {currentMetrics.length > 0 ? Math.round(currentMetrics[currentMetrics.length-1]?.memory_percent || 0) : 0}%
                </p>
                <p className="text-gray-400 text-sm">Memory Usage</p>
              </div>
            </div>
          </div>
          <div className="bg-gray-800 p-4 rounded-lg">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isRunning ? 'bg-green-500' : 'bg-red-500'}`}>
                {isRunning ? '●' : '○'}
              </div>
              <div>
                <p className="text-xl font-bold capitalize">{container.status}</p>
                <p className="text-gray-400 text-sm">Status</p>
              </div>
            </div>
          </div>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between border-b border-gray-700">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-4 py-2 text-sm font-medium ${
                  activeTab === 'overview'
                    ? 'text-blue-500 border-b-2 border-blue-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('logs')}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium ${
                  activeTab === 'logs'
                    ? 'text-blue-500 border-b-2 border-blue-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <FileText className="w-4 h-4" />
                Logs
              </button>
              <button
                onClick={() => setActiveTab('ports')}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium ${
                  activeTab === 'ports'
                    ? 'text-blue-500 border-b-2 border-blue-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Network className="w-4 h-4" />
                Ports
              </button>
              <button
                onClick={() => setActiveTab('env')}
                className={`flex items-center gap-2 px-4 py-2 text-sm font-medium ${
                  activeTab === 'env'
                    ? 'text-blue-500 border-b-2 border-blue-500'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <SettingsIcon className="w-4 h-4" />
                Environment
              </button>
            </div>
            {activeTab === 'overview' && (
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(Number(e.target.value))}
                className="bg-gray-800 border border-gray-700 text-white text-sm px-3 py-1 rounded"
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
          <MetricsChart data={metrics} title={`Resource Usage - Last ${timeRange}h`} />
        )}

        {activeTab === 'logs' && id && (
          <LogViewer containerId={id} />
        )}

        {activeTab === 'ports' && (
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Port Mappings</h3>
              <button
                onClick={() => setShowPortModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Port
              </button>
            </div>
            {(container as any)?.network_settings?.Ports && Object.keys((container as any).network_settings.Ports).length > 0 ? (
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left">Container Port</th>
                    <th className="px-4 py-2 text-left">Host Port</th>
                    <th className="px-4 py-2 text-left">Protocol</th>
                    <th className="px-4 py-2 text-left">Status</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries((container as any)?.network_settings?.Ports || {}).map(([port, binding]: [string, any]) => (
                    <tr key={port} className="border-t border-gray-700">
                      <td className="px-4 py-2">{port}</td>
                      <td className="px-4 py-2">{binding?.[0]?.HostPort || '-'}</td>
                      <td className="px-4 py-2">{port.split('/')[1] || 'tcp'}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-1 rounded text-xs ${binding ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                          {binding ? 'Bound' : 'Not Bound'}
                        </span>
                      </td>
                      <td className="px-4 py-2">
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
                          className="p-1 text-red-400 hover:text-red-300"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-gray-400">No ports exposed</p>
            )}
          </div>
        )}

        {activeTab === 'env' && (
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Environment Variables</h3>
              <button
                onClick={() => setShowEnvModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Variable
              </button>
            </div>
            {(container as any)?.config?.Env ? (
              <table className="w-full">
                <thead className="bg-gray-700">
                  <tr>
                    <th className="px-4 py-2 text-left">Variable</th>
                    <th className="px-4 py-2 text-left">Value</th>
                    <th className="px-4 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {((container as any)?.config?.Env as string[] || []).map((env: string, idx: number) => {
                    const [key, ...valueParts] = env.split('=')
                    return (
                      <tr key={idx} className="border-t border-gray-700">
                        <td className="px-4 py-2 font-mono text-blue-400">{key}</td>
                        <td className="px-4 py-2 font-mono text-gray-300 break-all">{valueParts.join('=')}</td>
                        <td className="px-4 py-2">
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
                            className="p-1 text-red-400 hover:text-red-300"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            ) : (
              <p className="text-gray-400">No environment variables</p>
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
      </div>
    </div>
  )
}

export default ContainerDetail