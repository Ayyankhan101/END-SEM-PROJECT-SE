import { useEffect, useState, useCallback } from 'react'
import { api } from '@/services/api'
import { AlertTriangle } from 'lucide-react'
import type { Alert } from '@/types'
import Header from '@/components/Header'
import { useAuth } from '@/App'

function Alerts() {
  const { isConnected, logout } = useAuth()
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  const fetchAlerts = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.getAlerts(50) as unknown
      setAlerts(Array.isArray(data) ? data : (data as Record<string, any>)?.alerts || [])
    } catch (err) {
      console.error('Failed to fetch alerts:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAlerts()
  }, [fetchAlerts])

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-500/20'
      case 'warning': return 'text-yellow-400 bg-yellow-500/20'
      default: return 'text-blue-400 bg-blue-500/20'
    }
  }

  return (
    <div className="app-surface">
      <Header
        title="Alerts"
        icon={<AlertTriangle size={24} />}
        onRefresh={fetchAlerts}
        isConnected={isConnected}
        onLogout={logout}
      />
      <main className="app-main">
        {loading ? (
          <div className="text-center py-12 text-slate-400">Loading alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-12 text-slate-400">No alerts found</div>
        ) : (
          <div className="space-y-3">
            {alerts.map(alert => (
              <div key={alert.id} className="dashboard-card">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className={`w-5 h-5 mt-0.5 ${alert.severity === 'critical' ? 'text-red-500' : 'text-yellow-500'}`} />
                    <div>
                      <p className="font-medium text-[#111827] dark:text-white">{alert.alert_type}</p>
                      <p className="text-slate-500 text-sm">{alert.message}</p>
                      <p className="text-slate-400 text-xs mt-1">{alert.container_id?.substring(0, 12)}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${getSeverityColor(alert.severity)}`}>
                    {alert.severity}
                  </span>
                </div>
                <p className="text-slate-400 text-xs mt-2">
                  {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'Unknown time'}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default Alerts
