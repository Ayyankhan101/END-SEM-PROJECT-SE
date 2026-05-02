import { useEffect, useState } from 'react'
import api from '@/services/api'
import type { BackupInfo } from '@/types'
import { formatSize } from '../utils/format'
import Header from '@/components/Header'
import { Archive, RefreshCw, UploadCloud } from 'lucide-react'
import { useAuth } from '@/App'

export default function Backup() {
  const { isConnected, logout } = useAuth()
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [restoring, setRestoring] = useState(false)

  useEffect(() => {
    loadBackups()
  }, [])

  async function loadBackups() {
    try {
      setLoading(true)
      const data = await api.listBackups() as unknown
      const backupList = (data as Record<string, any>)?.backups
      setBackups(Array.isArray(backupList) ? backupList : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load backups')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreate() {
    try {
      setCreating(true)
      await api.createBackup(true)
      alert('Backup creation started')
      loadBackups()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create backup')
    } finally {
      setCreating(false)
    }
  }

  async function handleRestore(file: File) {
    if (!confirm('Warning: This will overwrite existing data. Continue?')) return
    try {
      setRestoring(true)
      await api.restoreBackup(file)
      alert('Backup restored successfully')
      loadBackups()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to restore backup')
    } finally {
      setRestoring(false)
    }
  }

  return (
    <div className="app-surface">
      <Header title="Backup" icon={<Archive size={24} />} isConnected={isConnected} onLogout={logout} />
      <main className="px-4 py-6 sm:px-6 lg:ml-72 lg:px-8">
      <section className="dashboard-card mb-6 overflow-hidden">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-[#6366f1] to-[#8b5cf6] text-white">
            <Archive className="h-6 w-6" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-indigo-300">Data protection</p>
            <h1 className="mt-1 text-2xl font-semibold text-[#f1f5f9]">Backup & Restore</h1>
          </div>
        </div>
      </section>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-red-200">
          {error}
        </div>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        <div className="dashboard-card">
          <div className="mb-4 flex items-center gap-3">
            <RefreshCw className="h-5 w-5 text-indigo-300" />
            <h2 className="text-lg font-semibold">Create Backup</h2>
          </div>
          <p className="mb-4 text-[#94a3b8]">
            Create a backup of all containers, stacks, hosts, and settings.
          </p>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="btn-primary"
          >
            {creating ? 'Creating...' : 'Create Backup'}
          </button>
        </div>

        <div className="dashboard-card">
          <div className="mb-4 flex items-center gap-3">
            <UploadCloud className="h-5 w-5 text-emerald-300" />
            <h2 className="text-lg font-semibold">Restore Backup</h2>
          </div>
          <p className="mb-4 text-[#94a3b8]">
            Restore from a previously created backup file.
          </p>
          <input
            type="file"
            accept=".tar.gz"
            onChange={e => {
              const file = e.target.files?.[0]
              if (file) handleRestore(file)
            }}
            disabled={restoring}
            className="block w-full rounded-lg border border-[#334155] bg-[#0f172a] p-2 text-sm text-[#94a3b8] file:mr-4 file:rounded-lg file:border-0 file:bg-gradient-to-r file:from-[#6366f1] file:to-[#8b5cf6] file:px-4 file:py-2 file:font-semibold file:text-white"
          />
        </div>
      </div>

      <div className="dashboard-card">
        <h2 className="mb-4 text-lg font-semibold">Available Backups</h2>
        {loading ? (
          <div className="text-[#94a3b8]">Loading...</div>
        ) : backups.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[#334155] px-4 py-8 text-center text-[#94a3b8]">No backups found</div>
        ) : (
        <div className="overflow-hidden rounded-lg border border-[#334155]">
          <table className="w-full min-w-[640px]">
            <thead className="bg-[#0f172a] text-[#94a3b8]">
              <tr>
                <th className="px-4 py-3 text-left">Filename</th>
                <th className="px-4 py-3 text-left">Size</th>
                <th className="px-4 py-3 text-left">Created</th>
              </tr>
            </thead>
            <tbody>
              {backups.map(backup => (
                <tr key={backup.filename} className="border-t border-[#334155] transition hover:bg-slate-700/40">
                  <td className="px-4 py-3">{backup.filename}</td>
                  <td className="px-4 py-3">{formatSize(backup.size)}</td>
                  <td className="px-4 py-3">{new Date(backup.created).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </div>
      </main>
    </div>
  )
}
