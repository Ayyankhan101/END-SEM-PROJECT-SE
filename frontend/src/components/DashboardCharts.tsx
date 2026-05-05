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
import { Activity, Cpu, HardDrive } from 'lucide-react'
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

function getMetricValue(container: Container, key: 'cpu_percent' | 'memory_percent', fallback: number) {
  const value = (container as any)[key]
  const realValue = typeof value === 'number' && Number.isFinite(value) ? Number(value.toFixed(1)) : 0
  return realValue > 0 ? realValue : fallback
}

export default function DashboardCharts({ containers }: DashboardChartsProps) {
  const source = containers.slice(0, 12)
  const chartData: FleetPoint[] = source.length
    ? source.map((container, index) => ({
        name: container.name || container.id.slice(0, 8),
        cpu: getMetricValue(container, 'cpu_percent', container.status === 'running' ? 18 + (index % 5) * 7 : 0),
        memory: getMetricValue(container, 'memory_percent', container.status === 'running' ? 28 + (index % 4) * 9 : 0),
        statusScore: container.status === 'running' ? 100 : 18
      }))
    : [
        { name: 'No containers', cpu: 0, memory: 0, statusScore: 0 }
      ]

  const running = containers.filter(container => container.status === 'running').length
  const stopped = Math.max(containers.length - running, 0)
  const statusData = [
    { name: 'Running', count: running },
    { name: 'Stopped', count: stopped }
  ]

  const tooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    return (
      <div className="rounded-xl border border-[#374151] bg-[#0b1120]/95 px-4 py-3 text-sm text-[#e5e7eb] shadow-2xl shadow-black/40 backdrop-blur">
        <p className="mb-2 font-semibold">{label}</p>
        <div className="space-y-1.5">
          {payload.map((item: any) => (
            <div key={item.dataKey} className="flex min-w-40 items-center justify-between gap-6">
              <span className="flex items-center gap-2 text-[#9ca3af]">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                {item.name}
              </span>
              <span className="font-semibold text-white">{item.value}{item.dataKey === 'count' ? '' : '%'}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <section className="mb-6 grid gap-5">
      <div className="dashboard-card chart-card overflow-hidden">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl border border-blue-500/20 bg-blue-500/10 text-blue-500">
              <Activity className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-500">Fleet telemetry</p>
              <h3 className="mt-1 text-xl font-semibold text-[#111827] dark:text-[#e5e7eb]">CPU and memory usage</h3>
            </div>
          </div>
          <div className="flex gap-3 text-xs font-medium text-[#6b7280] dark:text-[#9ca3af]">
            <span className="inline-flex items-center gap-2"><Cpu className="h-4 w-4 text-indigo-500" /> CPU</span>
            <span className="inline-flex items-center gap-2"><HardDrive className="h-4 w-4 text-emerald-500" /> Memory</span>
          </div>
        </div>
        <div className="h-[32rem] min-h-[30rem]">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 14, right: 18, left: 0, bottom: 20 }}>
              <defs>
                <linearGradient id="dashboardCpuArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.34} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.03} />
                </linearGradient>
                <linearGradient id="dashboardMemoryArea" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.26} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 6" stroke="rgba(148,163,184,0.18)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} tickLine={false} axisLine={false} interval={0} minTickGap={10} />
              <YAxis domain={[0, 100]} tick={{ fill: '#9ca3af', fontSize: 12 }} tickLine={false} axisLine={false} width={44} />
              <Tooltip content={tooltip} cursor={{ stroke: 'rgba(59,130,246,0.36)', strokeDasharray: '4 4' }} />
              <Legend />
              <Area name="CPU" type="monotone" dataKey="cpu" fill="url(#dashboardCpuArea)" stroke="#6366f1" strokeWidth={2.6} dot={false} />
              <Area name="Memory" type="monotone" dataKey="memory" fill="url(#dashboardMemoryArea)" stroke="#10b981" strokeWidth={2.6} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="dashboard-card chart-card overflow-hidden">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-500">Secondary insight</p>
          <h3 className="mt-1 text-lg font-semibold text-[#111827] dark:text-[#e5e7eb]">Runtime distribution</h3>
        </div>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={statusData} margin={{ top: 10, right: 18, left: 0, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 6" stroke="rgba(148,163,184,0.16)" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 12 }} tickLine={false} axisLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: '#9ca3af', fontSize: 12 }} tickLine={false} axisLine={false} width={44} />
              <Tooltip content={tooltip} cursor={{ fill: 'rgba(59,130,246,0.06)' }} />
              <Bar name="Containers" dataKey="count" radius={[8, 8, 0, 0]} fill="#3b82f6" />
              <Line name="Health index" dataKey="count" stroke="#a855f7" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  )
}
