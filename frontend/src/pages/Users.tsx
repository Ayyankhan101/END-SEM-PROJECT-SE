import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { 
  Container, 
  Plus, 
  Layers, 
  Server,
  Bell,
  Save,
  Box,
  FileText,
  Settings,
  Users as UsersIcon,
  Pencil,
  Trash2,
  ArrowLeft
} from 'lucide-react'

interface User {
  id: number
  username: string
  role: string
  created_at?: string
  must_change_password: boolean
}

function Users() {
  const { logout, isConnected } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState<User | null>(null)
  const [formData, setFormData] = useState({ username: '', password: '', role: 'user', forcePasswordChange: false })
  const [deleteConfirm, setDeleteConfirm] = useState<number | null>(null)

  const fetchUsers = async () => {
    try {
      const data = await api.getUsers() as unknown
      setUsers(Array.isArray(data) ? data : (data as Record<string, any>)?.users || [])
    } catch (err) {
      console.error('Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (editingUser) {
        await api.updateUser(editingUser.id, {
          password: formData.password || undefined,
          role: formData.role,
          force_password_change: formData.forcePasswordChange
        })
      } else {
        await api.createUser({
          username: formData.username,
          password: formData.password,
          role: formData.role
        })
      }
      setShowModal(false)
      setEditingUser(null)
      setFormData({ username: '', password: '', role: 'user', forcePasswordChange: false })
      fetchUsers()
    } catch (err) {
      console.error('Failed to save user:', err)
    }
  }

  const handleDelete = async (userId: number) => {
    try {
      await api.deleteUser(userId)
      setDeleteConfirm(null)
      fetchUsers()
    } catch (err) {
      console.error('Failed to delete user:', err)
    }
  }

  const openEdit = (user: User) => {
    setEditingUser(user)
    setFormData({ username: user.username, password: '', role: user.role, forcePasswordChange: false })
    setShowModal(true)
  }

  const roleBadge = (role: string) => {
    const colors: Record<string, string> = {
      admin: 'bg-red-500/20 text-red-400',
      user: 'bg-blue-500/20 text-blue-400',
      viewer: 'bg-gray-500/20 text-gray-400'
    }
    return colors[role] || colors.user
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/" className="p-2 hover:bg-gray-700 rounded">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <UsersIcon className="w-8 h-8 text-blue-500" />
            <h1 className="text-xl font-bold">User Management</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <Link to="/stacks" className="p-2 hover:bg-gray-700 rounded">
              <Layers className="w-5 h-5" />
            </Link>
            <Link to="/hosts" className="p-2 hover:bg-gray-700 rounded">
              <Server className="w-5 h-5" />
            </Link>
            <Link to="/alerts" className="p-2 hover:bg-gray-700 rounded">
              <Bell className="w-5 h-5 text-yellow-500" />
            </Link>
            <Link to="/audit" className="p-2 hover:bg-gray-700 rounded" title="Audit Logs">
              <FileText className="w-5 h-5" />
            </Link>
            <Link to="/notifications" className="p-2 hover:bg-gray-700 rounded" title="Notifications">
              <Bell className="w-5 h-5" />
            </Link>
            <Link to="/backup" className="p-2 hover:bg-gray-700 rounded" title="Backup">
              <Save className="w-5 h-5" />
            </Link>
            <Link to="/docker" className="p-2 hover:bg-gray-700 rounded" title="Docker Resources">
              <Box className="w-5 h-5" />
            </Link>
            <Link to="/settings" className="p-2 hover:bg-gray-700 rounded">
              Settings
            </Link>
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
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-medium">Users</h2>
          <button
            onClick={() => {
              setEditingUser(null)
              setFormData({ username: '', password: '', role: 'user', forcePasswordChange: false })
              setShowModal(true)
            }}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm"
          >
            <Plus className="w-4 h-4" />
            Add User
          </button>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-400">Loading...</div>
        ) : (
          <div className="bg-gray-800 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Username</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Role</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Created</th>
                  <th className="px-4 py-3 text-left text-sm font-medium text-gray-300">Password</th>
                  <th className="px-4 py-3 text-right text-sm font-medium text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map(user => (
                  <tr key={user.id} className="border-t border-gray-700">
                    <td className="px-4 py-3">{user.username}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-1 rounded ${roleBadge(user.role)}`}>
                        {user.role}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-sm">
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {user.must_change_password === true ? (
                        <span className="text-yellow-400 text-sm">Change required</span>
                      ) : (
                        <span className="text-gray-500 text-sm">Set</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => openEdit(user)}
                        className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-white"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      {user.username !== 'admin' && (
                        <button
                          onClick={() => setDeleteConfirm(user.id)}
                          className="p-1.5 hover:bg-gray-700 rounded text-gray-400 hover:text-red-400 ml-2"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {showModal && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg w-96">
              <h3 className="text-lg font-bold mb-4">
                {editingUser ? 'Edit User' : 'Create User'}
              </h3>
              <form onSubmit={handleSubmit}>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Username</label>
                  <input
                    type="text"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    required={!editingUser}
                    disabled={!!editingUser}
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">
                    Password {editingUser && '(leave blank to keep current)'}
                  </label>
                  <input
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                    required={!editingUser}
                  />
                </div>
                <div className="mb-4">
                  <label className="block text-sm text-gray-400 mb-1">Role</label>
                  <select
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2"
                  >
                    <option value="admin">Admin</option>
                    <option value="user">User</option>
                    <option value="viewer">Viewer</option>
                  </select>
                </div>
                {editingUser && (
                  <div className="mb-4 flex items-center gap-2">
                    <input
                      type="checkbox"
                      id="forcePasswordChange"
                      checked={formData.forcePasswordChange}
                      onChange={(e) => setFormData({ ...formData, forcePasswordChange: e.target.checked })}
                      className="w-4 h-4"
                    />
                    <label htmlFor="forcePasswordChange" className="text-sm text-gray-300">
                      Force password change on next login
                    </label>
                  </div>
                )}
                <div className="flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false)
                      setEditingUser(null)
                    }}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded"
                  >
                    {editingUser ? 'Update' : 'Create'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 p-6 rounded-lg max-w-md">
              <h3 className="text-lg font-bold mb-4">Confirm Delete</h3>
              <p className="text-gray-400 mb-6">
                Are you sure you want to delete this user? This action cannot be undone.
              </p>
              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirm)}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Users