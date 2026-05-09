import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import Header from '@/components/Header'
import {
  Cpu,
  MemoryStick,
  AlertTriangle,
  RefreshCw,
  Activity,
  Zap,
  Brain,
  CheckCircle,
  XCircle
} from 'lucide-react'

interface Anomaly {
  id: string
  container_id: string
  container_name: string
  anomaly_type: string
  severity: string
  message: string
  metric_value: number
  threshold: number
  timestamp: string
  recommendations: string[]
}

interface RemediationPlan {
  anomaly: Anomaly
  remediation: {
    action: string
    reasoning: string
    steps: string[]
  }
}

interface SeverityBreakdown {
  critical: number
  high: number
  medium: number
  low: number
}

interface InsightsSummary {
  total_containers: number
  anomaly_count: number
  severity_breakdown: SeverityBreakdown
}

function AIInsights() {
  const { logout, isConnected } = useAuth()
  const [loading, setLoading] = useState<boolean>(true)
  const [insights, setInsights] = useState<{
    summary: InsightsSummary
    anomalies: RemediationPlan[]
    provider_available: boolean
    provider_name: string
  } | null>(null)
  const [error, setError] = useState<string>('')

  const fetchInsights = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await api.getAIInsights() as any
      const health = await api.getAIHealth()
      const providerName = Object.keys(health)[0] || 'ai'
      const providerAvailable = Object.values(health)[0]?.available || false
      setInsights({ ...data, provider_name: providerName, provider_available: providerAvailable })
    } catch (err) {
      setError('Failed to load AI insights')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInsights()
    const interval = setInterval(fetchInsights, 30000)
    return () => clearInterval(interval)
  }, [fetchInsights])

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-500 bg-red-500/10 border-red-500/30'
      case 'high': return 'text-orange-500 bg-orange-500/10 border-orange-500/30'
      case 'medium': return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30'
      default: return 'text-blue-500 bg-blue-500/10 border-blue-500/30'
    }
  }

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical': return <XCircle className="w-4 h-4" />
      case 'high': return <AlertTriangle className="w-4 h-4" />
      default: return <Activity className="w-4 h-4" />
    }
  }

  if (loading && !insights) {
    return (
      <div className="app-surface">
        <Header title="AI Insights" icon={<Brain size={24} />} isConnected={isConnected} onLogout={logout} />
        <main className="app-main">
          <div className="flex items-center justify-center min-h-[400px]">
            <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="app-surface">
      <Header
        title="AI Insights"
        icon={<Brain size={24} />}
        onRefresh={fetchInsights}
        isConnected={isConnected}
        onLogout={logout}
      />
      <main className="app-main">
      <div className="space-y-6">
      <div className="flex items-center gap-2 p-3 bg-slate-100 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
        <div className={`w-2 h-2 rounded-full ${insights?.provider_available ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-sm text-slate-700 dark:text-slate-300">
          {insights?.provider_name?.toUpperCase() || 'AI'}: {insights?.provider_available ? 'Connected' : 'Unavailable'}
        </span>
      </div>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="dashboard-card p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
            <Cpu className="w-4 h-4" /> Containers
          </div>
          <div className="text-2xl font-bold mt-1 text-[#111827] dark:text-white">{insights?.summary.total_containers || 0}</div>
        </div>
        <div className="dashboard-card p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
            <AlertTriangle className="w-4 h-4" /> Anomalies
          </div>
          <div className="text-2xl font-bold mt-1 text-[#111827] dark:text-white">{insights?.summary.anomaly_count || 0}</div>
        </div>
        <div className="dashboard-card p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
            <Zap className="w-4 h-4" /> Critical
          </div>
          <div className="text-2xl font-bold text-red-500">{insights?.summary.severity_breakdown.critical || 0}</div>
        </div>
        <div className="dashboard-card p-4">
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-sm">
            <MemoryStick className="w-4 h-4" /> High
          </div>
          <div className="text-2xl font-bold text-orange-500">{insights?.summary.severity_breakdown.high || 0}</div>
        </div>
      </div>

      <div className="dashboard-card overflow-hidden">
        <div className="p-4 border-b border-slate-200 dark:border-slate-700">
          <h2 className="font-semibold text-[#111827] dark:text-white">Detected Anomalies</h2>
        </div>

        {(!insights?.anomalies || insights.anomalies.length === 0) ? (
          <div className="p-8 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <p className="text-slate-500 dark:text-slate-400">No anomalies detected</p>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">All containers are healthy</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-200 dark:divide-slate-700">
            {insights.anomalies.map((item, idx) => (
              <div key={idx} className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      {getSeverityIcon(item.anomaly.severity)}
                      <span className="font-medium text-[#111827] dark:text-white">{item.anomaly.container_name}</span>
                      <span className={`px-2 py-0.5 text-xs rounded border ${getSeverityColor(item.anomaly.severity)}`}>
                        {item.anomaly.severity}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{item.anomaly.message}</p>

                    <div className="mt-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded border border-slate-200 dark:border-slate-700">
                      <p className="text-sm font-medium mb-2 text-[#111827] dark:text-white">Remediation</p>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{item.remediation.reasoning}</p>
                      <ol className="mt-2 space-y-1">
                        {item.remediation.steps.map((step, sIdx) => (
                          <li key={sIdx} className="text-sm text-slate-500 dark:text-slate-400 flex items-start gap-2">
                            <span className="text-blue-500">{sIdx + 1}.</span>
                            {step.replace(/^\d+\.\s*/, '')}
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      </div>
      </main>
    </div>
  )
}

export default AIInsights