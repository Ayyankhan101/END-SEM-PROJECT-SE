import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { 
  Container, 
  ArrowLeft,
  Activity,
  Cpu,
  HardDrive,
  X
} from 'lucide-react'
import MetricsChart from '@/components/MetricsChart'
import type { Container as ContainerType, Metric } from '@/types'

function ContainerCompare() {
  const { containers, logout, isConnected } = useAuth()
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [metricsData, setMetricsData] = useState<Record<string, Metric[]>>({})
  const [loading, setLoading] = useState(false)

  const maxContainers = 4

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(i => i !== id)
      }
      if (prev.length >= maxContainers) {
        return prev
      }
      return [...prev, id]
    })
  }

  const fetchMetrics = async () => {
    if (selectedIds.length === 0) return
    
    setLoading(true)
    try {
      const results: Record<string, Metric[]> = {}
      await Promise.all(
        selectedIds.map(async (id) => {
          const data = (await api.getMetricsHistory(id, 24)) as unknown as Record<string, any>
          results[id] = data?.metrics || []
        })
      )
      setMetricsData(results)
    } catch (err) {
      console.error('Failed to fetch metrics:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedIds.length > 0) {
      fetchMetrics()
    }
  }, [selectedIds])

  const getContainer = (id: string) => containers.find((c: ContainerType) => c.id === id)

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="p-2 hover:bg-gray-700 rounded">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <Activity className="w-8 h-8 text-blue-500" />
            <h1 className="text-xl font-bold">Compare Containers</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <span className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${
              isConnected 
                ? 'bg-green-900/50 text-green-400' 
                : 'bg-red-900/50 text-red-400'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
            <button onClick={logout} className="text-gray-400 hover:text-white">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="p-6">
        <div className="mb-6">
          <h2 className="text-lg font-medium mb-3">Select Containers (max {maxContainers})</h2>
          <div className="flex flex-wrap gap-2">
            {(containers as ContainerType[] || []).map((container: ContainerType) => {
              const isSelected = selectedIds.includes(container.id)
              return (
                <button
                  key={container.id}
                  onClick={() => toggleSelect(container.id)}
                  disabled={!isSelected && selectedIds.length >= maxContainers}
                  className={`px-4 py-2 rounded-lg border transition-colors ${
                    isSelected 
                      ? 'bg-blue-600 border-blue-500 text-white' 
                      : 'bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-700'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  <span className="flex items-center gap-2">
                    {container.name}
                    <span className={`w-2 h-2 rounded-full ${container.status === 'running' ? 'bg-green-400' : 'bg-red-400'}`}></span>
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {selectedIds.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-medium">Comparison ({selectedIds.length} containers)</h2>
              <button
                onClick={() => setSelectedIds([])}
                className="text-gray-400 hover:text-white flex items-center gap-1"
              >
                <X className="w-4 h-4" />
                Clear
              </button>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              {selectedIds.map(id => {
                const container = getContainer(id)
                const metrics = metricsData[id] || []
                const latestMetric = metrics[metrics.length - 1]
                
                return (
                  <div key={id} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <div className="flex items-center gap-2 mb-3">
                      <div className={`w-3 h-3 rounded-full ${container?.status === 'running' ? 'bg-green-500' : 'bg-red-500'}`} />
                      <h3 className="font-medium truncate">{container?.name}</h3>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-400">CPU</span>
                        <span className="font-mono">{latestMetric?.cpu_percent?.toFixed(1) || 0}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Memory</span>
                        <span className="font-mono">{latestMetric?.memory_percent?.toFixed(1) || 0}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Status</span>
                        <span className={`capitalize ${container?.status === 'running' ? 'text-green-400' : 'text-red-400'}`}>
                          {container?.status}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="bg-gray-800 rounded-lg p-4">
              <h3 className="text-md font-medium mb-4">CPU Usage Over Time</h3>
              {loading ? (
                <div className="h-64 flex items-center justify-center text-gray-400">
                  Loading metrics...
                </div>
              ) : (
                <MetricsChart 
                  data={selectedIds.flatMap(id => metricsData[id] || [])} 
                  title=""
                />
              )}
            </div>
          </div>
        )}

        {selectedIds.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            Select containers above to compare their metrics
          </div>
        )}
      </div>
    </div>
  )
}

export default ContainerCompare