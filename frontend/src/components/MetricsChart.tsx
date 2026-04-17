import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Legend 
} from 'recharts'
import type { Metric } from '@/types'

interface ChartDataPoint {
  time: string;
  cpu: number;
  memory: number;
}

interface MetricsChartProps {
  data?: Metric[];
  title?: string;
}

function MetricsChart({ data = [], title = "Metrics" }: MetricsChartProps) {
  const chartData: ChartDataPoint[] = Array.isArray(data) 
    ? data.map((d, i) => ({
        time: d.timestamp 
          ? new Date(d.timestamp).toLocaleTimeString() 
          : new Date(Date.now() - (data.length - i) * 5000).toLocaleTimeString(),
        cpu: d.cpu_percent || 0,
        memory: d.memory_percent || 0
      })).reverse() 
    : []

  return (
    <div className="bg-gray-800 p-4 rounded-lg">
      <h3 className="text-lg font-medium mb-4">{title}</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="time" stroke="#9CA3AF" fontSize={12} />
            <YAxis stroke="#9CA3AF" fontSize={12} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#1F2937', border: 'none', borderRadius: '8px' }}
              labelStyle={{ color: '#9CA3AF' }}
            />
            <Legend />
            <Line type="monotone" dataKey="cpu" stroke="#3B82F6" strokeWidth={2} dot={false} name="CPU %" />
            <Line type="monotone" dataKey="memory" stroke="#10B981" strokeWidth={2} dot={false} name="Memory %" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default MetricsChart