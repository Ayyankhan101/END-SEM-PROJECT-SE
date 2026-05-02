import { Link } from 'react-router-dom'
import { Play, Pause, RotateCw, Square, CheckSquare, Square as SquareIcon, Star, Trash2, Box } from 'lucide-react'
import { api } from '@/services/api'
import type { Container } from '@/types'
import { MouseEvent, useState } from 'react'

const GROUPS = ['default', 'web', 'db', 'backend', 'frontend', 'cache', 'queue', 'dev', 'staging', 'prod']

const groupColors: Record<string, string> = {
  default: 'bg-slate-500/10 text-slate-500 ring-slate-500/20',
  web: 'bg-blue-500/10 text-blue-500 ring-blue-500/20',
  db: 'bg-emerald-500/10 text-emerald-500 ring-emerald-500/20',
  backend: 'bg-violet-500/10 text-violet-500 ring-violet-500/20',
  frontend: 'bg-amber-500/10 text-amber-500 ring-amber-500/20',
  cache: 'bg-red-500/10 text-red-500 ring-red-500/20',
  queue: 'bg-orange-500/10 text-orange-500 ring-orange-500/20',
  dev: 'bg-cyan-500/10 text-cyan-500 ring-cyan-500/20',
  staging: 'bg-pink-500/10 text-pink-500 ring-pink-500/20',
  prod: 'bg-red-600/10 text-red-500 ring-red-600/20',
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
    handleAction('start', () => api.startContainer(container.id))
  }

  const handleDelete = (e: MouseEvent<HTMLButtonElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (confirm(`Delete container "${container.name}"?`)) {
      handleAction('delete', () => api.deleteContainer(container.id))
    }
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
      <div className={`group relative overflow-hidden rounded-xl border bg-white p-5 shadow-md shadow-slate-200/70 transition duration-200 hover:-translate-y-1 hover:scale-[1.01] hover:shadow-xl hover:shadow-blue-950/10 dark:bg-[#111827] dark:shadow-black/25 dark:hover:shadow-blue-950/30 ${selected ? 'border-[#2563eb] ring-4 ring-blue-500/10' : 'border-[#e5e7eb] dark:border-[#374151]'}`}>
        <div className="pointer-events-none absolute inset-x-0 top-0 h-24 bg-gradient-to-br from-blue-500/10 via-transparent to-indigo-500/10 opacity-80" />
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={handleSelect}
              className="rounded-md p-1 text-slate-400 transition hover:bg-slate-100 hover:text-blue-500 dark:hover:bg-white/10"
              title="Select"
            >
              {selected ? <CheckSquare className="h-5 w-5 text-blue-500" /> : <SquareIcon className="h-5 w-5" />}
            </button>
            <div className={`relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border ${isRunning ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-500' : 'border-red-500/20 bg-red-500/10 text-red-500'}`}>
              <Box className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="truncate text-base font-bold text-[#111827] dark:text-[#e5e7eb]">{container.name}</h3>
              <p className="font-mono text-xs text-[#6b7280] dark:text-[#9ca3af]">{container.id.substring(0, 12)}</p>
            </div>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ring-1 ${groupColors[group] || groupColors.default}`}>
              {group}
            </span>
            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${isRunning ? 'bg-emerald-500/10 text-emerald-500 ring-emerald-500/20' : 'bg-red-500/10 text-red-500 ring-red-500/20'}`}>
              {container.status}
            </span>
          </div>
        </div>

        <div className="mb-4 truncate rounded-xl border border-[#e5e7eb] bg-[#f9fafb] px-3 py-2 text-sm text-[#6b7280] dark:border-[#374151] dark:bg-[#1f2937] dark:text-[#9ca3af]">
          {container.image || 'No image'}
        </div>

        <div className="flex items-center gap-2">
          {isStopped && (
            <button
              onClick={handleStart}
              disabled={loadingAction === 'start'}
              className="icon-action bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20 disabled:opacity-50"
              title="Start"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          {isRunning && (
            <button
              onClick={handleStop}
              disabled={loadingAction === 'stop'}
              className="icon-action bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-50"
              title="Stop"
            >
              <Square className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleRestart}
            disabled={loadingAction === 'restart'}
            className="icon-action bg-orange-500/10 text-orange-500 hover:bg-orange-500/20 disabled:opacity-50"
            title="Restart"
          >
            <RotateCw className={`w-4 h-4 ${loadingAction === 'restart' ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handlePause}
            disabled={loadingAction === 'pause' || loadingAction === 'resume'}
            className="icon-action bg-amber-500/10 text-amber-500 hover:bg-amber-500/20 disabled:opacity-50"
            title={isRunning ? 'Pause' : 'Resume'}
          >
            {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          </button>
          <button
            onClick={handleToggleFavorite}
            className={`icon-action ${isFavorite ? 'bg-amber-500/10 text-amber-500' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-white/10 dark:hover:text-slate-200'}`}
            title={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Star className={`w-4 h-4 ${isFavorite ? 'fill-current' : ''}`} />
          </button>
          <button
            onClick={handleDelete}
            disabled={loadingAction === 'delete'}
            className="icon-action ml-auto bg-red-500/10 text-red-500 hover:bg-red-500/20 disabled:opacity-50"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </Link>
  )
}

export default ContainerCard
