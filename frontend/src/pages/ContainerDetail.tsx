import { useEffect, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { ArrowLeft, Play, Pause, RotateCw, Cpu, HardDrive, FileText } from 'lucide-react'
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

  const fetchData = useCallback(async () => {
    if (!id) return
    try {
      const [containerData, metricsData] = await Promise.all([
        api.getContainer(id),
        api.getContainerMetrics(id, 50)
      ])
      setContainer(containerData)
      setMetrics(metricsData?.metrics || [])
    } catch (err) {
      console.error('Failed to fetch container:', err)
    } finally {
      setLoading(false)
    }
  }, [id])

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
            return [...currentMetrics.slice(-49), {
              cpu_percent: data.stats?.cpu_percent,
              memory_percent: data.stats?.memory_percent,
              timestamp: data.timestamp
            }]
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
          <div className="flex gap-2">
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
          <div className="flex gap-2 border-b border-gray-700">
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
          </div>
        </div>

        {activeTab === 'overview' && (
          <MetricsChart data={metrics} title="Resource Usage Over Time" />
        )}

        {activeTab === 'logs' && (
          <LogViewer containerId={id} />
        )}
      </div>
    </div>
  )
}

export default ContainerDetail