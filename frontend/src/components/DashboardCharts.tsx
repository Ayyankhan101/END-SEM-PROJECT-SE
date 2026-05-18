import { useState, useEffect } from 'react'
import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from 'recharts'
import { Activity, Cpu, HardDrive, X, Download } from 'lucide-react'
import type { Container } from '@/types'

interface DashboardChartsProps {
  containers: Container[];
}

interface FleetPoint {
  name: string;
  cpu: number;
  memory: number;
  statusScore: number;
}

function getMetricValue(
  container: Container,
  key: 'cpu_percent' | 'memory_percent',
  fallback: number
) {
  const value = (container as any)[key]
  const realValue =
    typeof value === 'number' && Number.isFinite(value)
      ? Number(value.toFixed(1))
      : 0

  return realValue > 0 ? realValue : fallback
}

export default function DashboardCharts({ containers }: DashboardChartsProps) {
  const [fullscreenChart, setFullscreenChart] =
    useState<'main' | 'status' | null>(null)

  useEffect(() => {
    document.body.style.overflow = fullscreenChart ? 'hidden' : 'unset'
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [fullscreenChart])

  const source = containers.slice(0, 12)

  const chartData: FleetPoint[] =
    source.length > 0
      ? source.map(container => ({
          name: container.name || container.id.slice(0, 8),
          cpu: getMetricValue(container, 'cpu_percent', 0),
          memory: getMetricValue(container, 'memory_percent', 0),
          statusScore: container.status === 'running' ? 100 : 0
        }))
      : [{ name: 'No containers', cpu: 0, memory: 0, statusScore: 0 }]

  const running = containers.filter(c => c.status === 'running').length
  const stopped = Math.max(containers.length - running, 0)

  const statusData = [
    { name: 'Running', count: running },
    { name: 'Stopped', count: stopped }
  ]

  const maxCpu = chartData.length ? Math.max(...chartData.map(d => d.cpu)) : 0
  const maxMemory = chartData.length ? Math.max(...chartData.map(d => d.memory)) : 0
  const yMax = Math.max(10, Math.ceil(Math.max(maxCpu, maxMemory) * 1.1))

  const statusYMax = Math.max(
    5,
    Math.ceil(Math.max(...statusData.map(d => d.count)) * 1.1)
  )

  // FIXED TOOLTIP (Recharts-safe, no TS break)
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null

    return (
      <div className="rounded-xl border border-[#374151] bg-[#0b1120]/95 px-4 py-3 text-sm text-[#e5e7eb] shadow-2xl">
        <p className="mb-2 font-semibold">{label}</p>

        <div className="space-y-1">
          {payload.map((item: any) => (
            <div key={item.dataKey} className="flex justify-between gap-6">
              <span className="text-[#9ca3af]">{item.name}</span>
              <span className="text-white font-semibold">
                {item.value}{item.dataKey === 'count' ? '' : '%'}
              </span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const handleDownload = (e: React.MouseEvent) => {
    e.stopPropagation()

    const dataToExport =
      fullscreenChart === 'main' ? chartData : statusData

    if (!dataToExport.length) return

    const headers = Object.keys(dataToExport[0])

    const csv = [
      headers.join(','),
      ...dataToExport.map(row =>
        headers
          .map(h => {
            const v = (row as any)[h]
            return typeof v === 'string'
              ? `"${v.replace(/"/g, '""')}"`
              : v
          })
          .join(',')
      )
    ].join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = `fleet_${fullscreenChart || 'data'}.csv`
    a.click()

    URL.revokeObjectURL(url)
  }

  return (
    <section className="mb-6 grid gap-5">

      {/* MAIN CHART */}
      <div
        className="dashboard-card cursor-pointer"
        onClick={() => setFullscreenChart('main')}
      >
        <div className="h-[28rem]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 6" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, yMax]} />
              <Tooltip content={<CustomTooltip />} />
              <Legend />

              <Area dataKey="cpu" stroke="#6366f1" fill="#6366f1" />
              <Area dataKey="memory" stroke="#10b981" fill="#10b981" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* STATUS CHART */}
      <div
        className="dashboard-card cursor-pointer"
        onClick={() => setFullscreenChart('status')}
      >
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={statusData}>
              <XAxis dataKey="name" />
              <YAxis domain={[0, statusYMax]} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey="count" fill="#3b82f6" />
              <Line dataKey="count" stroke="#a855f7" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* FULLSCREEN */}
      {fullscreenChart && (
        <div
          className="fixed inset-0 z-50 bg-black/90"
          onClick={() => setFullscreenChart(null)}
        >
          <button onClick={handleDownload}>
            <Download />
          </button>
          <button onClick={() => setFullscreenChart(null)}>
            <X />
          </button>
        </div>
      )}
    </section>
  )
}
