import { useId } from 'react'
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
import type { Metric } from '@/types'

interface ChartDataPoint {
  time: number;
  displayTime: string;
  exactTime: string;
  cpu: number;
  memory: number;
  memoryMb: number;
  ioLoad: number;
  health: number;
}

interface MetricsChartProps {
  data?: Metric[];
  title?: string;
}

const formatTime = (time: number, includeSeconds = false) => new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: includeSeconds ? '2-digit' : undefined,
  hour12: false
}).format(new Date(time))

const getValue = (value: unknown) => typeof value === 'number' && Number.isFinite(value) ? value : 0

function MetricsChart({ data = [], title = 'Metrics' }: MetricsChartProps) {
  const id = useId().replace(/:/g, '')
  const chartData: ChartDataPoint[] = Array.isArray(data)
    ? data.map((d, i) => {
        const fallbackTime = Date.now() - (data.length - i) * 5000
        const date = d.timestamp ? new Date(d.timestamp) : new Date(fallbackTime)
        const time = Number.isNaN(date.getTime()) ? fallbackTime : date.getTime()
        const cpu = Number(getValue(d.cpu_percent).toFixed(2))
        const memory = Number(getValue(d.memory_percent).toFixed(2))
        const memoryMb = Number((getValue(d.memory_usage) / 1024 / 1024).toFixed(1))

        return {
          time,
          displayTime: formatTime(time),
          exactTime: new Intl.DateTimeFormat(undefined, {
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
          }).format(new Date(time)),
          cpu,
          memory,
          memoryMb,
          ioLoad: Number(Math.min(100, Math.max(0, (cpu * 0.58) + (memory * 0.42))).toFixed(2)),
          health: Number(Math.max(0, 100 - Math.max(cpu, memory)).toFixed(2))
        }
      }).sort((a, b) => a.time - b.time)
    : []

  const hasData = chartData.length > 0
  const latest = chartData[chartData.length - 1]
  const peakCpu = hasData ? Math.max(...chartData.map(point => point.cpu)) : 0
  const peakMemory = hasData ? Math.max(...chartData.map(point => point.memory)) : 0
  const avgLoad = hasData
    ? chartData.reduce((sum, point) => sum + point.ioLoad, 0) / chartData.length
    : 0

  const tooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    const point = payload[0]?.payload as ChartDataPoint
    const titleText = point?.exactTime || (typeof label === 'number' ? formatTime(label, true) : label)

    return (
      <div className="rounded-xl border border-[#374151] bg-[#0b1120]/95 px-4 py-3 text-sm text-[#e5e7eb] shadow-2xl shadow-black/40 backdrop-blur">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.12em] text-[#9ca3af]">{titleText}</p>
        <div className="space-y-2">
          {payload.map((item: any) => {
            const isPercent = item.dataKey !== 'memoryMb'
            return (
              <div key={item.dataKey} className="flex min-w-48 items-center justify-between gap-8">
                <span className="flex items-center gap-2 text-[#d1d5db]">
                  <span className="h-2.5 w-2.5 rounded-full shadow-[0_0_10px_currentColor]" style={{ backgroundColor: item.color, color: item.color }} />
                  {item.name}
                </span>
                <span className="font-semibold text-white">
                  {Number(item.value).toFixed(isPercent ? 1 : 0)}{isPercent ? '%' : ' MB'}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const axisText = { fill: '#9ca3af', fontSize: 13, fontWeight: 600 }
  const gridStroke = 'rgba(148,163,184,0.18)'

  const renderEmpty = () => (
    <div className="flex h-full min-h-60 items-center justify-center rounded-xl border border-dashed border-[#374151]/50 text-sm text-[#6b7280] dark:text-[#9ca3af]">
      Waiting for container telemetry...
    </div>
  )

  return (
    <section className="animate-fade-in space-y-5">
      <div className="dashboard-card chart-card overflow-hidden">
        <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-500">Container performance</p>
            <h3 className="mt-2 text-2xl font-semibold text-[#111827] dark:text-[#e5e7eb]">{title}</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-[#6b7280] dark:text-[#d1d5db]">
              Live CPU and memory pressure over time with peak usage, load estimate, and health signals below.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="rounded-xl border border-blue-500/20 bg-blue-500/10 px-3 py-2">
              <p className="text-[#6b7280] dark:text-[#9ca3af]">Peak CPU</p>
              <p className="mt-1 text-lg font-bold text-blue-500">{peakCpu.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2">
              <p className="text-[#6b7280] dark:text-[#9ca3af]">Peak Memory</p>
              <p className="mt-1 text-lg font-bold text-emerald-500">{peakMemory.toFixed(1)}%</p>
            </div>
            <div className="rounded-xl border border-fuchsia-500/20 bg-fuchsia-500/10 px-3 py-2">
              <p className="text-[#6b7280] dark:text-[#9ca3af]">Load Index</p>
              <p className="mt-1 text-lg font-bold text-fuchsia-500">{avgLoad.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        <div className="h-[42rem] min-h-[38rem]">
          {!hasData ? renderEmpty() : (
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 14, right: 28, left: 8, bottom: 42 }}>
                <defs>
                  <linearGradient id={`${id}CpuArea`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-cpu)" stopOpacity={0.36} />
                    <stop offset="95%" stopColor="var(--chart-cpu)" stopOpacity={0.03} />
                  </linearGradient>
                  <linearGradient id={`${id}MemoryArea`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--chart-memory)" stopOpacity={0.30} />
                    <stop offset="95%" stopColor="var(--chart-memory)" stopOpacity={0.02} />
                  </linearGradient>
                  <filter id={`${id}CpuGlow`} x="-20%" y="-20%" width="140%" height="140%">
                    <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                    <feMerge>
                      <feMergeNode in="coloredBlur" />
                      <feMergeNode in="SourceGraphic" />
                    </feMerge>
                  </filter>
                </defs>
                <CartesianGrid strokeDasharray="3 8" stroke={gridStroke} vertical={false} />
                <XAxis
                  dataKey="time"
                  type="number"
                  domain={['dataMin', 'dataMax']}
                  tickFormatter={(value) => formatTime(Number(value))}
                  tick={axisText}
                  tickLine={false}
                  axisLine={{ stroke: 'rgba(148,163,184,0.25)' }}
                  label={{ value: 'Time', position: 'insideBottom', offset: -26, fill: '#9ca3af', fontSize: 13, fontWeight: 700 }}
                  minTickGap={44}
                  interval="preserveStartEnd"
                  padding={{ left: 18, right: 18 }}
                />
                <YAxis
                  domain={[0, 100]}
                  tick={axisText}
                  tickFormatter={(value) => `${Math.round(Number(value))}%`}
                  tickLine={false}
                  axisLine={{ stroke: 'rgba(148,163,184,0.25)' }}
                  label={{ value: 'Utilization (%)', angle: -90, position: 'insideLeft', fill: '#9ca3af', fontSize: 13, fontWeight: 700, dy: 52 }}
                  width={76}
                  allowDecimals={false}
                />
                <Tooltip content={tooltip} cursor={{ stroke: 'rgba(236,72,153,0.38)', strokeWidth: 1.4, strokeDasharray: '5 5' }} />
                <Legend wrapperStyle={{ paddingTop: 18, fontSize: 13, fontWeight: 700 }} />
                <Area name="CPU usage" type="monotone" dataKey="cpu" fill={`url(#${id}CpuArea)`} stroke="none" isAnimationActive animationDuration={900} />
                <Area name="Memory usage" type="monotone" dataKey="memory" fill={`url(#${id}MemoryArea)`} stroke="none" isAnimationActive animationDuration={900} />
                <Line
                  name="CPU usage"
                  type="monotone"
                  dataKey="cpu"
                  stroke="var(--chart-cpu)"
                  strokeWidth={3.4}
                  dot={false}
                  activeDot={{ r: 5, fill: '#c4b5fd', stroke: '#0b1120', strokeWidth: 2 }}
                  filter={`url(#${id}CpuGlow)`}
                  isAnimationActive
                  animationDuration={900}
                />
                <Line
                  name="Memory usage"
                  type="monotone"
                  dataKey="memory"
                  stroke="var(--chart-memory)"
                  strokeWidth={3.4}
                  dot={false}
                  activeDot={{ r: 5, fill: '#6ee7b7', stroke: '#0b1120', strokeWidth: 2 }}
                  isAnimationActive
                  animationDuration={900}
                />
              </ComposedChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SupportChart
          title="CPU vs Memory"
          description="Side-by-side pressure comparison"
          data={chartData}
          tooltip={tooltip}
          empty={renderEmpty()}
          gridStroke={gridStroke}
          axisText={axisText}
          type="comparison"
        />
        <SupportChart
          title="I/O Load Estimate"
          description="Derived from CPU and memory activity"
          data={chartData}
          tooltip={tooltip}
          empty={renderEmpty()}
          gridStroke={gridStroke}
          axisText={axisText}
          type="io"
        />
        <SupportChart
          title="Health Timeline"
          description="Higher is healthier"
          data={chartData}
          tooltip={tooltip}
          empty={renderEmpty()}
          gridStroke={gridStroke}
          axisText={axisText}
          type="health"
        />
      </div>
    </section>
  )
}

interface SupportChartProps {
  title: string;
  description: string;
  data: ChartDataPoint[];
  tooltip: (props: any) => JSX.Element | null;
  empty: JSX.Element;
  gridStroke: string;
  axisText: { fill: string; fontSize: number; fontWeight: number };
  type: 'comparison' | 'io' | 'health';
}

function SupportChart({ title, description, data, tooltip, empty, gridStroke, axisText, type }: SupportChartProps) {
  const hasData = data.length > 0

  return (
    <div className="dashboard-card chart-card">
      <div className="mb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-500">Insight</p>
        <h4 className="mt-1 text-lg font-semibold text-[#111827] dark:text-[#e5e7eb]">{title}</h4>
        <p className="mt-1 text-sm text-[#6b7280] dark:text-[#9ca3af]">{description}</p>
      </div>
      <div className="h-80">
        {!hasData ? empty : (
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 26 }}>
              <CartesianGrid strokeDasharray="3 8" stroke={gridStroke} vertical={false} />
              <XAxis
                dataKey="time"
                type="number"
                domain={['dataMin', 'dataMax']}
                tickFormatter={(value) => formatTime(Number(value))}
                tick={{ ...axisText, fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                minTickGap={36}
              />
              <YAxis
                domain={[0, 100]}
                tick={{ ...axisText, fontSize: 11 }}
                tickFormatter={(value) => `${Math.round(Number(value))}%`}
                tickLine={false}
                axisLine={false}
                width={48}
              />
              <Tooltip content={tooltip} cursor={{ stroke: 'rgba(236,72,153,0.32)', strokeDasharray: '4 4' }} />
              {type === 'comparison' && (
                <>
                  <Bar name="CPU usage" dataKey="cpu" radius={[5, 5, 0, 0]} fill="var(--chart-cpu)" barSize={16} />
                  <Bar name="Memory usage" dataKey="memory" radius={[5, 5, 0, 0]} fill="var(--chart-memory)" barSize={16} />
                </>
              )}
              {type === 'io' && (
                <>
                  <Area name="I/O load estimate" type="monotone" dataKey="ioLoad" fill="var(--chart-io-fill)" stroke="none" />
                  <Line name="I/O load estimate" type="monotone" dataKey="ioLoad" stroke="var(--chart-io)" strokeWidth={2.8} dot={false} />
                </>
              )}
              {type === 'health' && (
                <>
                  <Area name="Health score" type="monotone" dataKey="health" fill="var(--chart-health-fill)" stroke="none" />
                  <Line name="Health score" type="monotone" dataKey="health" stroke="var(--chart-health)" strokeWidth={2.8} dot={false} />
                </>
              )}
            </ComposedChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

export default MetricsChart
