import { useState, FormEvent, ChangeEvent } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, Plus } from 'lucide-react'
import { api } from '@/services/api'

interface FormData {
  image: string;
  name: string;
  ports: string;
  memory_limit: string;
  cpu_limit: string;
}

function ContainerCreate() {
  const [formData, setFormData] = useState<FormData>({
    image: '',
    name: '',
    ports: '',
    memory_limit: '',
    cpu_limit: ''
  })
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const ports: Record<string, number> = {}
      if (formData.ports) {
        const portPairs = formData.ports.split(',')
        portPairs.forEach(pair => {
          const [hostPort, containerPort] = pair.trim().split(':')
          if (hostPort && containerPort) {
            ports[containerPort] = parseInt(hostPort)
          }
        })
      }

      const config = {
        image: formData.image,
        name: formData.name,
        ports: Object.keys(ports).length ? ports : undefined,
        memory_limit: formData.memory_limit ? parseInt(formData.memory_limit) : undefined,
        cpu_limit: formData.cpu_limit ? parseFloat(formData.cpu_limit) : undefined
      }

      const result = await api.createContainer(config)
      setSuccess(`Container "${result.container.name}" created successfully!`)
      setFormData({
        image: '',
        name: '',
        ports: '',
        memory_limit: '',
        cpu_limit: ''
      })
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create container')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <Plus className="w-8 h-8 text-blue-500" />
            <h1 className="text-2xl font-bold">Create Container</h1>
          </div>

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

          <form onSubmit={handleSubmit} className="bg-gray-800 rounded-lg p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Container Name *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="my-container"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Image *
              </label>
              <input
                type="text"
                name="image"
                value={formData.image}
                onChange={handleChange}
                required
                className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="nginx:latest"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">
                Port Mappings
              </label>
              <input
                type="text"
                name="ports"
                value={formData.ports}
                onChange={handleChange}
                className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="8080:80"
              />
              <p className="text-gray-500 text-sm mt-1">Format: host_port:container_port</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  Memory Limit (bytes)
                </label>
                <input
                  type="number"
                  name="memory_limit"
                  value={formData.memory_limit}
                  onChange={handleChange}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="512000000"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-1">
                  CPU Limit (cores)
                </label>
                <input
                  type="number"
                  name="cpu_limit"
                  step="0.1"
                  min="0"
                  max="1"
                  value={formData.cpu_limit}
                  onChange={handleChange}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="0.5"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 disabled:cursor-not-allowed px-4 py-2 rounded font-medium"
            >
              {loading ? 'Creating...' : 'Create Container'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ContainerCreate