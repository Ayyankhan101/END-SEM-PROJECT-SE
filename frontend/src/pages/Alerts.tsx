import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/services/api'
import { AlertTriangle, ArrowLeft } from 'lucide-react'
import type { Alert, AlertSeverity } from '@/types'

function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const data = await api.getAlerts(50) as unknown
        setAlerts(Array.isArray(data) ? data : (data as Record<string, any>)?.alerts || [])
      } catch (err) {
        console.error('Failed to fetch alerts:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchAlerts()
  }, [])

  const getSeverityColor = (severity: string): string => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-500/20'
      case 'warning': return 'text-yellow-400 bg-yellow-500/20'
      default: return 'text-blue-400 bg-blue-500/20'
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <h1 className="text-2xl font-bold mb-6">Alerts</h1>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading alerts...</div>
        ) : alerts.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            No alerts found
          </div>
        ) : (
          <div className="space-y-3">
            {alerts.map(alert => (
              <div key={alert.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className={`w-5 h-5 mt-0.5 ${alert.severity === 'critical' ? 'text-red-500' : 'text-yellow-500'}`} />
                    <div>
                      <p className="font-medium">{alert.alert_type}</p>
                      <p className="text-gray-400 text-sm">{alert.message}</p>
                      <p className="text-gray-500 text-xs mt-1">{alert.container_id?.substring(0, 12)}</p>
                    </div>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${getSeverityColor(alert.severity)}`}>
                    {alert.severity}
                  </span>
                </div>
                <p className="text-gray-500 text-xs mt-2">
                  {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : 'Unknown time'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Alerts