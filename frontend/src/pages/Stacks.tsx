import { useEffect, useState, FormEvent, useRef } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { Plus, Play, Square, Trash2, Layers, FileCode, ArrowLeft } from 'lucide-react'
import Editor from '@monaco-editor/react'
import type { Stack } from '@/types'

function Stacks() {
  const { logout } = useAuth() 
  const [stacks, setStacks] = useState<Stack[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [showForm, setShowForm] = useState<boolean>(false)
  const [newStack, setNewStack] = useState<{ name: string; compose_file: string }>({ 
    name: '', 
    compose_file: '' 
  })
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const editorRef = useRef<any>(null)

  const fetchStacks = async () => {
    try {
      const data = await api.getStacks()
      setStacks(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error('Failed to fetch stacks:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStacks()
  }, [])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      await api.createStack({ name: newStack.name, compose_file: newStack.compose_file })
      setSuccess('Stack deployed successfully!')
      setNewStack({ name: '', compose_file: '' })
      setShowForm(false)
      fetchStacks()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to deploy stack')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id: number, name: string) => {
    if (!confirm(`Are you sure you want to delete stack "${name}"?`)) return
    
    try {
      await api.deleteStack(id)
      fetchStacks()
    } catch (err) {
      console.error('Failed to delete stack:', err)
    }
  }

  const handleStart = async (id: number) => {
    try {
      await api.startStack(id)
      fetchStacks()
    } catch (err) {
      console.error('Failed to start stack:', err)
    }
  }

  const handleStop = async (id: number) => {
    try {
      await api.stopStack(id)
      fetchStacks()
    } catch (err) {
      console.error('Failed to stop stack:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Layers className="w-8 h-8 text-blue-500" />
            <h1 className="text-xl font-bold">Docker Stacks</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setShowForm(!showForm)}
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm"
            >
              <Plus className="w-4 h-4" />
              Deploy Stack
            </button>
            <Link to="/" className="text-gray-400 hover:text-white">
              Dashboard
            </Link>
            <button onClick={logout} className="text-gray-400 hover:text-white">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="p-6">
        {showForm && (
          <div className="bg-gray-800 rounded-lg p-6 mb-6">
            <h2 className="text-lg font-bold mb-4">Deploy New Stack</h2>
            
            {error && (
              <div className="bg-red-500/10 border border-red-500 text-red-500 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}
            
            {success && (
              <div className="bg-green-500/10 border border-green-500 text-green-500 px-4 py-3 rounded mb-4">
                {success}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Stack Name *
                </label>
                <input
                  type="text"
                  value={newStack.name}
                  onChange={(e) => setNewStack({ ...newStack, name: e.target.value })}
                  required
                  className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="my-stack"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Docker Compose YAML *
                </label>
                <div className="flex gap-2 mb-2">
                  <button
                    type="button"
                    onClick={() => {
                      const template = `version: '3'
services:
  web:
    image: nginx:latest
    ports:
      - "8088:80"
    restart: unless-stopped
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - db-data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  db-data:`
                      setNewStack({ ...newStack, compose_file: template })
                      if (editorRef.current) {
                        editorRef.current.setValue(template)
                      }
                    }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Load Web Server Example
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      const template = `version: '3'
services:
  app:
    image: node:18
    command: npm start
    working_dir: /app
    volumes:
      - ./:/app
    ports:
      - "3000:3000"
    restart: unless-stopped
    environment:
      - NODE_ENV=development`
                      setNewStack({ ...newStack, compose_file: template })
                      if (editorRef.current) {
                        editorRef.current.setValue(template)
                      }
                    }}
                    className="text-xs text-blue-400 hover:text-blue-300"
                  >
                    Load Node.js Example
                  </button>
                </div>
                <div className="border border-gray-600 rounded overflow-hidden">
                  <Editor
                    height="350px"
                    defaultLanguage="yaml"
                    theme="vs-dark"
                    value={newStack.compose_file}
                    onChange={(value) => setNewStack({ ...newStack, compose_file: value || '' })}
                    onMount={(editor) => { editorRef.current = editor }}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 13,
                      lineNumbers: 'on',
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                      tabSize: 2,
                    }}
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={loading}
                  className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 px-4 py-2 rounded font-medium"
                >
                  {loading ? 'Deploying...' : 'Deploy Stack'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="bg-gray-700 hover:bg-gray-600 px-4 py-2 rounded font-medium"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading && (!stacks || stacks.length === 0) ? (
          <div className="text-center py-12 text-gray-400">Loading stacks...</div>
        ) : !stacks || stacks.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <Layers className="w-16 h-16 mx-auto mb-4 text-gray-600" />
            <p>No stacks deployed yet</p>
            <p className="text-sm mt-2">Click "Deploy Stack" to create your first stack</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {stacks.map(stack => (
              <div key={stack.id} className="bg-gray-800 rounded-lg p-4">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="text-lg font-bold">{stack.name}</h3>
                    <span className={`text-sm ${stack.status === 'running' ? 'text-green-500' : 'text-gray-400'}`}>
                      {stack.status}
                    </span>
                  </div>
                  <div className="flex gap-2">
                    {stack.status === 'running' ? (
                      <button
                        onClick={() => handleStop(stack.id)}
                        className="p-2 hover:bg-gray-700 rounded text-yellow-500"
                        title="Stop"
                      >
                        <Square className="w-4 h-4" />
                      </button>
                    ) : (
                      <button
                        onClick={() => handleStart(stack.id)}
                        className="p-2 hover:bg-gray-700 rounded text-green-500"
                        title="Start"
                      >
                        <Play className="w-4 h-4" />
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(stack.id, stack.name)}
                      className="p-2 hover:bg-gray-700 rounded text-red-500"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <div className="bg-gray-900 rounded p-2 max-h-32 overflow-auto">
                  <pre className="text-xs text-gray-400 font-mono whitespace-pre-wrap">
                    {stack.compose_file.substring(0, 200)}...
                  </pre>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Stacks