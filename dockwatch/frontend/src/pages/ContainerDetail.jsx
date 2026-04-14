import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../App'
import { getContainer, getContainerMetrics, restartContainer, pauseContainer, unpauseContainer } from '../services/api'
import { ArrowLeft, Play, Pause, RotateCw, Cpu, HardDrive } from 'lucide-react'
import MetricsChart from '../components/MetricsChart'

function ContainerDetail() {
  const { id } = useParams()
  const { socket } = useAuth()
  const [container, setContainer] = useState(null)
  const [metrics, setMetrics] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [containerData, metricsData] = await Promise.all([
          getContainer(id),
          getContainerMetrics(id, 50)
        ])
        setContainer(containerData)
        setMetrics(metricsData.metrics || [])
      } catch (err) {
        console.error('Failed to fetch container:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [id])

  useEffect(() => {
    if (!socket) return
    socket.on('metrics', (data) => {
      if (data.container_id === id) {
        setMetrics(prev => [...prev.slice(-49), {
          cpu_percent: data.stats?.cpu_percent,
          memory_percent: data.stats?.memory_percent,
          timestamp: data.timestamp
        }])
      }
    })
    return () => socket.off('metrics')
  }, [socket, id])

  const handleRestart = async () => {
    try {
      await restartContainer(id)
    } catch (err) {
      console.error('Restart failed:', err)
    }
  }

  const handlePause = async () => {
    try {
      if (container?.status === 'running') {
        await pauseContainer(id)
      } else {
        await unpauseContainer(id)
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
                  {metrics.length > 0 ? Math.round(metrics[metrics.length-1]?.cpu_percent || 0) : 0}%
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
                  {metrics.length > 0 ? Math.round(metrics[metrics.length-1]?.memory_percent || 0) : 0}%
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

        <MetricsChart data={metrics} title="Resource Usage Over Time" />
      </div>
    </div>
  )
}

export default ContainerDetail