import { Link } from 'react-router-dom'
import { Play, Pause, RotateCw, Square, CheckSquare, Square as SquareIcon, Star } from 'lucide-react'
import { api } from '@/services/api'
import type { Container } from '@/types'
import { MouseEvent, useState } from 'react'

const GROUPS = ['default', 'web', 'db', 'backend', 'frontend', 'cache', 'queue', 'dev', 'staging', 'prod']

const groupColors: Record<string, string> = {
  default: 'bg-gray-500/20 text-gray-400',
  web: 'bg-blue-500/20 text-blue-400',
  db: 'bg-green-500/20 text-green-400',
  backend: 'bg-purple-500/20 text-purple-400',
  frontend: 'bg-yellow-500/20 text-yellow-400',
  cache: 'bg-red-500/20 text-red-400',
  queue: 'bg-orange-500/20 text-orange-400',
  dev: 'bg-cyan-500/20 text-cyan-400',
  staging: 'bg-pink-500/20 text-pink-400',
  prod: 'bg-red-600/20 text-red-400',
}

interface ContainerCardProps {
  container: Container;
  selected?: boolean;
  onSelect?: (id: string) => void;
}

function ContainerCard({ container, selected = false, onSelect }: ContainerCardProps) {
  const isRunning = container.status === 'running'
  const isStopped = container.status === 'exited' || container.status === 'stopped'
  const [loadingAction, setLoadingAction] = useState<string | null>(null)
  const [isFavorite, setIsFavorite] = useState((container as any).is_favorite === 1)
  const group = (container as any).group || 'default'
  
  const handleAction = async (action: string, fn: () => Promise<any>) => {
    setLoadingAction(action)
    try {
      await fn()
    } catch (err) {
      console.error(`${action} failed:`, err)
    } finally {
      setLoadingAction(null)
    }
  }

  const handleToggleFavorite = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    handleAction('favorite', async () => {
      await api.toggleContainerFavorite(container.id)
      setIsFavorite(!isFavorite)
    })
  }

  const handleStart = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    handleAction('start', () => api.restartContainer(container.id))
  }

  const handleStop = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    handleAction('stop', () => api.stopContainer(container.id))
  }

  const handleRestart = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    handleAction('restart', () => api.restartContainer(container.id))
  }

  const handlePause = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const action = isRunning ? 'pause' : 'resume'
    handleAction(action, () => isRunning ? api.pauseContainer(container.id) : api.unpauseContainer(container.id))
  }

  const handleSelect = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    onSelect?.(container.id)
  }

  return (
    <Link to={`/container/${container.id}`} className="block">
      <div className={`bg-gray-800 p-4 rounded-lg hover:bg-gray-750 transition-colors border ${selected ? 'border-blue-500' : 'border-gray-700'}`}>
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <button
              onClick={handleSelect}
              className="p-1 hover:bg-gray-700 rounded"
              title="Select"
            >
              {selected ? <CheckSquare className="w-5 h-5 text-blue-500" /> : <SquareIcon className="w-5 h-5 text-gray-500" />}
            </button>
            <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-green-500' : 'bg-red-500'}`} />
            <div>
              <h3 className="font-medium text-white">{container.name}</h3>
              <p className="text-xs text-gray-500 font-mono">{container.id.substring(0, 12)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs px-2 py-1 rounded ${groupColors[group] || groupColors.default}`}>
              {group}
            </span>
            <span className={`text-xs px-2 py-1 rounded ${isRunning ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
              {container.status}
            </span>
          </div>
        </div>

        <div className="text-sm text-gray-400 mb-3">
          {container.image || 'No image'}
        </div>

        <div className="flex gap-2">
          {isStopped && (
            <button
              onClick={handleStart}
              disabled={loadingAction === 'start'}
              className="p-1.5 bg-green-700 hover:bg-green-600 rounded text-gray-300 disabled:opacity-50"
              title="Start"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          {isRunning && (
            <button
              onClick={handleStop}
              disabled={loadingAction === 'stop'}
              className="p-1.5 bg-red-700 hover:bg-red-600 rounded text-gray-300 disabled:opacity-50"
              title="Stop"
            >
              <Square className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleRestart}
            disabled={loadingAction === 'restart'}
            className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 disabled:opacity-50"
            title="Restart"
          >
            <RotateCw className={`w-4 h-4 ${loadingAction === 'restart' ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handlePause}
            disabled={loadingAction === 'pause' || loadingAction === 'resume'}
            className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 disabled:opacity-50"
            title={isRunning ? 'Pause' : 'Resume'}
          >
            {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={handleToggleFavorite}
            className={`p-1.5 rounded ${isFavorite ? 'text-yellow-400' : 'text-gray-500 hover:text-gray-400'}`}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
        </div>
      </div>
    </Link>
  )
}

export default ContainerCard