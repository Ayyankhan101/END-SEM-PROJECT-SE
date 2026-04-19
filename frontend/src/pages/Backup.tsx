import { useEffect, useState } from 'react'
import api from '@/services/api'
import type { BackupInfo } from '@/types'

export default function Backup() {
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
      const data = await api.listBackups()
      setBackups(data.backups)
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

  function formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Backup & Restore</h1>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 px-4 py-2 rounded mb-4">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4">Create Backup</h2>
          <p className="text-gray-400 mb-4">
            Create a backup of all containers, stacks, hosts, and settings.
          </p>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Create Backup'}
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-bold mb-4">Restore Backup</h2>
          <p className="text-gray-400 mb-4">
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
            className="block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-600 file:text-white"
          />
        </div>
      </div>

      <h2 className="text-lg font-bold mb-4">Available Backups</h2>

      {loading ? (
        <div className="text-gray-400">Loading...</div>
      ) : backups.length === 0 ? (
        <div className="text-gray-400">No backups found</div>
      ) : (
        <div className="bg-gray-800 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-900">
              <tr>
                <th className="px-4 py-3 text-left">Filename</th>
                <th className="px-4 py-3 text-left">Size</th>
                <th className="px-4 py-3 text-left">Created</th>
              </tr>
            </thead>
            <tbody>
              {backups.map(backup => (
                <tr key={backup.filename} className="border-t border-gray-700">
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
  )
}