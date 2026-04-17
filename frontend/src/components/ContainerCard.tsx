import { Link } from 'react-router-dom'
import { Play, Pause, RotateCw } from 'lucide-react'
import { api } from '@/services/api'
import type { Container } from '@/types'
import { MouseEvent } from 'react'

interface ContainerCardProps {
  container: Container;
}

function ContainerCard({ container }: ContainerCardProps) {
  const isRunning = container.status === 'running'
  
  const handleRestart = async (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await api.restartContainer(container.id)
    } catch (err) {
      console.error('Restart failed:', err)
    }
  }

  const handlePause = async (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      if (isRunning) {
        await api.pauseContainer(container.id)
      } else {
        await api.unpauseContainer(container.id)
      }
    } catch (err) {
      console.error('Pause failed:', err)
    }
  }

  return (
    <Link to={`/container/${container.id}`} className="block">
      <div className="bg-gray-800 p-4 rounded-lg hover:bg-gray-750 transition-colors border border-gray-700">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-500' : 'bg-red-500'}`} />
            <div>
              <h3 className="font-medium text-white">{container.name}</h3>
              <p className="text-xs text-gray-500 font-mono">{container.id.substring(0, 12)}</p>
            </div>
          </div>
          <span className={`text-xs px-2 py-1 rounded ${isRunning ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
            {container.status}
          </span>
        </div>

        <div className="text-sm text-gray-400 mb-3">
          {container.image || 'No image'}
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleRestart}
            className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
            title="Restart"
          >
            <RotateCw className="w-4 h-4" />
          </button>
          <button
            onClick={handlePause}
            className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300"
            title={isRunning ? 'Pause' : 'Resume'}
          >
            {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </Link>
  )
}

export default ContainerCard