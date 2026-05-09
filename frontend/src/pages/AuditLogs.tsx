import { useEffect, useState } from 'react'
import { api } from '@/services/api'
import type { AuditLog, AuditStats } from '@/types'
import Header from '@/components/Header'
import { FileText } from 'lucide-react'
import { useAuth } from '@/App'

export default function AuditLogs() {
  const { isConnected, logout } = useAuth()
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [stats, setStats] = useState<AuditStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState({ action: '', resource_type: '', days: 7 })
  const [pagination, setPagination] = useState({ skip: 0, limit: 50, total: 0 })

  useEffect(() => {
    loadData()
  }, [filter, pagination.skip])

  async function loadData() {
    try {
      setLoading(true)
      const [logsRes, statsRes] = await Promise.all([
        api.getAuditLogs({ ...filter, skip: pagination.skip, limit: pagination.limit }),
        api.getAuditStats(filter.days)
      ])
      setLogs(logsRes?.logs || [])
      setStats(statsRes || null)
      setPagination(p => ({ ...p, total: logsRes?.total || 0 }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load audit logs')
    } finally {
      setLoading(false)
    }
  }

  const actionTypes = ['CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'BACKUP', 'RESTORE']
  const resourceTypes = ['container', 'stack', 'host', 'settings', 'notification']

  return (
    <div className="app-surface">
      <Header title="Audit Logs" icon={<FileText size={24} />} isConnected={isConnected} onLogout={logout} />
      <main className="px-4 py-6 sm:px-6 lg:ml-72 lg:px-8">
      <section className="dashboard-card mb-6">
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-300">Governance</p>
        <h1 className="mt-2 text-2xl font-semibold">Audit Logs</h1>
        <p className="mt-1 text-sm text-[#94a3b8]">Review user and system activity across your Docker environment.</p>
      </section>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-red-200">
          {error}
        </div>
      )}

      {stats && (
        <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div className="dashboard-card">
            <div className="text-2xl font-bold">{stats?.total_actions || 0}</div>
            <div className="text-[#94a3b8]">Total Actions</div>
          </div>
          <div className="dashboard-card">
            <div className="text-2xl font-bold">{Object.keys(stats?.actions_by_type || {}).length}</div>
            <div className="text-[#94a3b8]">Action Types</div>
          </div>
          <div className="dashboard-card">
            <div className="text-2xl font-bold">{Object.keys(stats?.resources_by_type || {}).length}</div>
            <div className="text-[#94a3b8]">Resource Types</div>
          </div>
          <div className="dashboard-card">
            <div className="text-2xl font-bold">{stats?.period_days || 7}</div>
            <div className="text-[#94a3b8]">Days</div>
          </div>
        </div>
      )}

      <div className="dashboard-card mb-6 flex flex-col gap-3 md:flex-row">
        <select
          value={filter.action}
          onChange={e => setFilter(f => ({ ...f, action: e.target.value }))}
          className="rounded-lg border border-[#334155] bg-[#0f172a] px-3 py-2 text-[#f1f5f9]"
        >
          <option value="">All Actions</option>
          {actionTypes.map(a => <option key={a} value={a}>{a}</option>)}
        </select>

        <select
          value={filter.resource_type}
          onChange={e => setFilter(f => ({ ...f, resource_type: e.target.value }))}
          className="rounded-lg border border-[#334155] bg-[#0f172a] px-3 py-2 text-[#f1f5f9]"
        >
          <option value="">All Resources</option>
          {resourceTypes.map(r => <option key={r} value={r}>{r}</option>)}
        </select>

        <select
          value={filter.days}
          onChange={e => setFilter(f => ({ ...f, days: parseInt(e.target.value) }))}
          className="rounded-lg border border-[#334155] bg-[#0f172a] px-3 py-2 text-[#f1f5f9]"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading ? (
        <div className="dashboard-card text-[#94a3b8]">Loading...</div>
      ) : (
        <div className="dashboard-card overflow-x-auto p-0">
          <table className="w-full min-w-[900px]">
            <thead className="bg-[#0f172a] text-[#94a3b8]">
              <tr>
                <th className="px-4 py-3 text-left">Timestamp</th>
                <th className="px-4 py-3 text-left">Action</th>
                <th className="px-4 py-3 text-left">Resource</th>
                <th className="px-4 py-3 text-left">Resource ID</th>
                <th className="px-4 py-3 text-left">User</th>
                <th className="px-4 py-3 text-left">IP</th>
                <th className="px-4 py-3 text-left">Details</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <tr key={log.id} className="border-t border-[#334155] transition hover:bg-slate-700/40">
                  <td className="px-4 py-3">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="px-4 py-3">{log.action}</td>
                  <td className="px-4 py-3">{log.resource_type}</td>
                  <td className="px-4 py-3 text-gray-400">{log.resource_id || '-'}</td>
                  <td className="px-4 py-3">{log.user_id || '-'}</td>
                  <td className="px-4 py-3 text-gray-400">{log.ip_address || '-'}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{log.details ? JSON.stringify(log.details).substring(0, 50) : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pagination.total > pagination.limit && (
        <div className="mt-4 flex items-center gap-2">
          <button
            onClick={() => setPagination(p => ({ ...p, skip: Math.max(0, p.skip - p.limit) }))}
            disabled={pagination.skip === 0}
            className="btn-secondary"
          >
            Previous
          </button>
          <span className="px-4 py-2 text-[#94a3b8]">
            {pagination.skip + 1}-{Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total}
          </span>
          <button
            onClick={() => setPagination(p => ({ ...p, skip: p.skip + p.limit }))}
            disabled={pagination.skip + pagination.limit >= pagination.total}
            className="btn-secondary"
          >
            Next
          </button>
        </div>
      )}
      </main>
    </div>
  )
}
