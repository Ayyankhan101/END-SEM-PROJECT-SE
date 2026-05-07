import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { 
  Container, 
  AlertTriangle, 
  Shield, 
  Search, 
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Info
} from 'lucide-react'
import Header from '@/components/Header'
import { api } from '@/services/api'
import { useAuth } from '@/App'

interface Vulnerability {
  vuln_id: string
  severity: string
  title: string
  package: string
  installed_version: string
  fixed_version: string | null
  description: string
}

interface ScanResult {
  image: string
  vulnerabilities: Vulnerability[]
  critical_count: number
  high_count: number
  medium_count: number
  low_count: number
  total_count: number
}

export default function Security() {
  const { containers, logout, isConnected } = useAuth()
  const [loading, setLoading] = useState<boolean>(true)
  const [scanning, setScanning] = useState<boolean>(false)
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [selectedContainer, setSelectedContainer] = useState<string>('')
  const [trivyHealth, setTrivyHealth] = useState<any>(null)

  const checkTrivyHealth = useCallback(async () => {
    try {
      const health = await api.getTrivyHealth()
      setTrivyHealth(health)
    } catch (err) {
      console.error('Trivy health check failed:', err)
    }
  }, [])

  const scanContainer = useCallback(async () => {
    if (!selectedContainer && !containers[0]) return
    
    const containerId = selectedContainer || containers[0]?.id
    if (!containerId) return

    setScanning(true)
    try {
      const result = await api.scanContainerVulnerabilities(containerId)
      setScanResult(result)
    } catch (err) {
      console.error('Scan failed:', err)
    } finally {
      setScanning(false)
    }
  }, [selectedContainer, containers])

  useEffect(() => {
    checkTrivyHealth()
    setLoading(false)
  }, [checkTrivyHealth])

  useEffect(() => {
    if (containers.length > 0 && !scanResult && !scanning) {
      setSelectedContainer(containers[0].id)
    }
  }, [containers, scanResult, scanning])

  const severityColor = (severity: string) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL': return 'text-red-600 bg-red-50 dark:bg-red-900/20'
      case 'HIGH': return 'text-orange-600 bg-orange-50 dark:bg-orange-900/20'
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-900/20'
      case 'LOW': return 'text-blue-600 bg-blue-50 dark:bg-blue-900/20'
      default: return 'text-gray-600 bg-gray-50'
    }
  }

  return (
    <div className="app-surface relative overflow-hidden">
      <Header 
        title="Security" 
        icon={<Shield size={24} />} 
        onRefresh={checkTrivyHealth}
        isConnected={isConnected}
        onLogout={logout}
      />

      <main className="app-main z-10">
        <div className="dashboard-card mb-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-red-500/20 bg-red-500/10">
              <Shield className="h-6 w-6 text-red-500" />
            </div>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight text-[#111827] dark:text-[#e5e7eb]">
                CVE Scanner
              </h2>
              <p className="text-sm text-[#6b7280] dark:text-[#d1d5db]">
                Scan containers for security vulnerabilities using Trivy
              </p>
            </div>
          </div>
        </div>

        <div className="mb-6 grid gap-4 sm:grid-cols-3">
          <div className="dashboard-card">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Trivy Status</p>
            <div className="mt-2 flex items-center gap-2">
              {trivyHealth?.available ? (
                <CheckCircle className="h-5 w-5 text-emerald-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
              <span className="text-lg font-semibold">
                {trivyHealth?.available ? 'Available' : 'Not Available'}
              </span>
            </div>
          </div>
          <div className="dashboard-card">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Images Scanned</p>
            <p className="mt-2 text-2xl font-semibold text-[#111827] dark:text-white">
              {scanResult ? 1 : 0}
            </p>
          </div>
          <div className="dashboard-card">
            <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Total Vulnerabilities</p>
            <p className="mt-2 text-2xl font-semibold text-[#111827] dark:text-white">
              {scanResult?.total_count || 0}
            </p>
          </div>
        </div>

        <div className="dashboard-card mb-6">
          <h3 className="mb-4 text-lg font-semibold text-[#111827] dark:text-white">
            Scan Container
          </h3>
          <div className="flex flex-col gap-4 sm:flex-row">
            <select
              value={selectedContainer}
              onChange={(e) => setSelectedContainer(e.target.value)}
              className="theme-input flex-1 px-4 py-2.5"
            >
              <option value="">Select container...</option>
              {containers.map((c: any) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.image})
                </option>
              ))}
            </select>
            <button
              onClick={scanContainer}
              disabled={scanning || !selectedContainer}
              className="inline-flex items-center gap-2 rounded-lg bg-red-500 px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-red-500/15 transition hover:bg-red-400 disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${scanning ? 'animate-spin' : ''}`} />
              {scanning ? 'Scanning...' : 'Scan'}
            </button>
          </div>
        </div>

        {scanResult && (
          <>
            <div className="mb-6 grid gap-4 sm:grid-cols-4">
              <div className="dashboard-card border-l-4 border-l-red-500">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Critical</p>
                <p className="mt-2 text-3xl font-semibold text-red-600 dark:text-red-400">
                  {scanResult.critical_count}
                </p>
              </div>
              <div className="dashboard-card border-l-4 border-l-orange-500">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">High</p>
                <p className="mt-2 text-3xl font-semibold text-orange-600 dark:text-orange-400">
                  {scanResult.high_count}
                </p>
              </div>
              <div className="dashboard-card border-l-4 border-l-yellow-500">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Medium</p>
                <p className="mt-2 text-3xl font-semibold text-yellow-600 dark:text-yellow-400">
                  {scanResult.medium_count}
                </p>
              </div>
              <div className="dashboard-card border-l-4 border-l-blue-500">
                <p className="text-sm font-medium text-slate-500 dark:text-slate-400">Low</p>
                <p className="mt-2 text-3xl font-semibold text-blue-600 dark:text-blue-400">
                  {scanResult.low_count}
                </p>
              </div>
            </div>

            <div className="dashboard-card">
              <h3 className="mb-4 text-lg font-semibold text-[#111827] dark:text-white">
                Vulnerabilities ({scanResult.vulnerabilities.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-slate-200 dark:border-slate-700">
                      <th className="pb-3 text-left text-sm font-medium text-slate-500">ID</th>
                      <th className="pb-3 text-left text-sm font-medium text-slate-500">Severity</th>
                      <th className="pb-3 text-left text-sm font-medium text-slate-500">Package</th>
                      <th className="pb-3 text-left text-sm font-medium text-slate-500">Installed</th>
                      <th className="pb-3 text-left text-sm font-medium text-slate-500">Fixed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scanResult.vulnerabilities.map((v: Vulnerability, i: number) => (
                      <tr key={i} className="border-b border-slate-100 dark:border-slate-800">
                        <td className="py-3 font-mono text-sm">{v.vuln_id}</td>
                        <td className="py-3">
                          <span className={`inline-flex rounded px-2 py-1 text-xs font-semibold ${severityColor(v.severity)}`}>
                            {v.severity}
                          </span>
                        </td>
                        <td className="py-3 text-sm">{v.package}</td>
                        <td className="py-3 font-mono text-sm">{v.installed_version}</td>
                        <td className="py-3 font-mono text-sm text-emerald-600">
                          {v.fixed_version || '-'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}

        {!scanResult && !scanning && (
          <div className="dashboard-card flex flex-col items-center justify-center py-12 text-center">
            <Shield className="h-12 w-12 text-slate-300 dark:text-slate-600" />
            <p className="mt-4 text-slate-500">
              Select a container and click Scan to find vulnerabilities
            </p>
          </div>
        )}
      </main>
    </div>
  )
}