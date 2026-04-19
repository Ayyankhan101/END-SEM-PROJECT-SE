import { useEffect, useState } from 'react'
import api from '@/services/api'
import type { AuditLog, AuditStats } from '@/types'

export default function AuditLogs() {
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
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Audit Logs</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{stats?.total_actions || 0}</div>
            <div className="text-gray-400">Total Actions</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{Object.keys(stats?.actions_by_type || {}).length}</div>
            <div className="text-gray-400">Action Types</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{Object.keys(stats?.resources_by_type || {}).length}</div>
            <div className="text-gray-400">Resource Types</div>
          </div>
          <div className="bg-gray-800 rounded-lg p-4">
            <div className="text-2xl font-bold">{stats?.period_days || 7}</div>
            <div className="text-gray-400">Days</div>
          </div>
        </div>
      )}

      <div className="flex gap-4 mb-6">
        <select
          value={filter.action}
          onChange={e => setFilter(f => ({ ...f, action: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2"
        >
          <option value="">All Actions</option>
          {actionTypes.map(a => <option key={a} value={a}>{a}</option>)}
        </select>

        <select
          value={filter.resource_type}
          onChange={e => setFilter(f => ({ ...f, resource_type: e.target.value }))}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2"
        >
          <option value="">All Resources</option>
          {resourceTypes.map(r => <option key={r} value={r}>{r}</option>)}
        </select>

        <select
          value={filter.days}
          onChange={e => setFilter(f => ({ ...f, days: parseInt(e.target.value) }))}
          className="bg-gray-800 border border-gray-700 rounded px-3 py-2"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {loading ? (
        <div className="text-gray-400">Loading...</div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-900">
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
                <tr key={log.id} className="border-t border-gray-700">
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
        <div className="flex gap-2 mt-4">
          <button
            onClick={() => setPagination(p => ({ ...p, skip: Math.max(0, p.skip - p.limit) }))}
            disabled={pagination.skip === 0}
            className="px-4 py-2 bg-gray-800 rounded disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2">
            {pagination.skip + 1}-{Math.min(pagination.skip + pagination.limit, pagination.total)} of {pagination.total}
          </span>
          <button
            onClick={() => setPagination(p => ({ ...p, skip: p.skip + p.limit }))}
            disabled={pagination.skip + pagination.limit >= pagination.total}
            className="px-4 py-2 bg-gray-800 rounded disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}