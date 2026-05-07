import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  Bell,
  Brain,
  Calendar,
  Container,
  FileText,
  Layers,
  LogOut,
  Menu,
  Network,
  RefreshCw,
  Server,
  Settings,
  ShieldCheck,
  Users,
  X
} from 'lucide-react'

interface HeaderProps {
  title: string
  icon: React.ReactNode
  onRefresh?: () => void
  isConnected?: boolean
  onLogout?: () => void
}

const navItems = [
  { path: '/', label: 'Dashboard', icon: Container },
  { path: '/containers', label: 'Containers', icon: Layers },
  { path: '/stacks', label: 'Stacks', icon: Server },
  { path: '/hosts', label: 'Hosts', icon: Server },
  { path: '/alerts', label: 'Alerts', icon: Bell },
  { path: '/alert-rules', label: 'Alert Rules', icon: Bell },
  { path: '/schedules', label: 'Schedules', icon: Calendar },
  { path: '/users', label: 'Users', icon: Users },
  { path: '/audit', label: 'Audit Logs', icon: FileText },
  { path: '/notifications', label: 'Notifications', icon: Bell },
  { path: '/backup', label: 'Backup', icon: RefreshCw },
  { path: '/docker', label: 'Docker', icon: Container },
  { path: '/compare', label: 'Compare', icon: RefreshCw },
  { path: '/ai', label: 'AI Insights', icon: Brain },
  { path: '/topology', label: 'Topology', icon: Network },
  { path: '/security', label: 'Security', icon: ShieldCheck },
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Header({ title, icon, onRefresh, isConnected, onLogout }: HeaderProps) {
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)

  return (
    <>
      {navOpen && (
        <button
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/70 backdrop-blur-sm lg:hidden"
          onClick={() => setNavOpen(false)}
        />
      )}

      <aside className={`
        app-sidebar group/sidebar
        ${navOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <div className="flex h-16 items-center justify-between border-b border-[#e5e7eb] px-5 dark:border-[#374151] lg:px-4">
          <Link to="/" onClick={() => setNavOpen(false)} className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-lg shadow-blue-500/20">
              <Container className="h-5 w-5" />
            </div>
            <div className="min-w-0 transition duration-200 lg:pointer-events-none lg:w-0 lg:opacity-0 lg:group-hover/sidebar:pointer-events-auto lg:group-hover/sidebar:w-auto lg:group-hover/sidebar:opacity-100">
              <p className="text-sm font-bold tracking-tight text-[#111827] dark:text-[#e5e7eb]">DockWatch</p>
              <p className="text-xs text-[#6b7280] dark:text-[#9ca3af]">Docker operations</p>
            </div>
          </Link>
          <button
            onClick={() => setNavOpen(false)}
            className="rounded-md p-2 text-[#6b7280] transition hover:bg-blue-50 hover:text-[#111827] dark:text-[#9ca3af] dark:hover:bg-[#1f2937] dark:hover:text-[#e5e7eb] lg:hidden"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path ||
              (item.path === '/containers' && location.pathname.startsWith('/container'))

            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setNavOpen(false)}
                title={item.label}
                className={`
                  group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition duration-200 lg:justify-center lg:group-hover/sidebar:justify-start
                  ${isActive
                    ? 'bg-gradient-to-r from-[#2563eb] to-[#4f46e5] text-white shadow-lg shadow-blue-500/15'
                    : 'text-[#6b7280] hover:bg-blue-50 hover:text-[#111827] dark:text-[#9ca3af] dark:hover:bg-[#1f2937] dark:hover:text-[#e5e7eb]'
                  }
                `}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="transition duration-200 lg:w-0 lg:overflow-hidden lg:opacity-0 lg:group-hover/sidebar:w-auto lg:group-hover/sidebar:opacity-100">{item.label}</span>
              </Link>
            )
          })}
        </nav>

        <div className="border-t border-[#e5e7eb] p-4 dark:border-[#374151] lg:p-3">
          <div className="rounded-xl border border-[#e5e7eb] bg-[#f9fafb] p-3 dark:border-[#374151] dark:bg-[#111827] lg:flex lg:items-center lg:justify-center lg:group-hover/sidebar:block">
            <div className="flex items-center gap-2 text-sm font-medium text-[#111827] dark:text-[#e5e7eb] lg:justify-center lg:group-hover/sidebar:justify-start">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span className="transition duration-200 lg:hidden lg:group-hover/sidebar:inline">Runtime health</span>
            </div>
            {isConnected !== undefined && (
              <div className={`mt-2 flex items-center gap-2 text-xs lg:justify-center lg:group-hover/sidebar:justify-start ${isConnected ? 'text-emerald-500' : 'text-red-500'}`}>
                <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-500'}`} />
                <span className="transition duration-200 lg:hidden lg:group-hover/sidebar:inline">{isConnected ? 'Connected to monitor' : 'Monitor offline'}</span>
              </div>
            )}
          </div>
        </div>
      </aside>

      <header className="app-header">
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <button
              onClick={() => setNavOpen(true)}
              className="rounded-lg border border-[#e5e7eb] p-2 text-[#6b7280] transition hover:bg-blue-50 hover:text-[#111827] dark:border-[#374151] dark:text-[#9ca3af] dark:hover:bg-[#1f2937] dark:hover:text-[#e5e7eb] lg:hidden"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <div className="hidden h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#e5e7eb] bg-[#f9fafb] text-[#2563eb] dark:border-[#374151] dark:bg-[#111827] dark:text-[#3b82f6] sm:flex">
              {icon}
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold text-[#111827] dark:text-[#e5e7eb]">{title}</h1>
              <p className="hidden text-xs text-[#6b7280] dark:text-[#9ca3af] sm:block">Production Docker monitoring workspace</p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {onRefresh && (
              <button
                onClick={onRefresh}
                className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-[#2563eb] to-[#4f46e5] px-3 py-2 text-sm font-semibold text-white shadow-lg shadow-blue-500/15 transition duration-200 hover:-translate-y-0.5 hover:brightness-110 hover:shadow-blue-500/25 active:scale-[0.98]"
                title="Sync containers"
              >
                <RefreshCw className="h-4 w-4" />
                <span className="hidden sm:inline">Sync</span>
              </button>
            )}

            {isConnected !== undefined && (
              <span className={`hidden items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium sm:flex ${
                isConnected
                  ? 'border-emerald-400/25 bg-emerald-400/10 text-emerald-500'
                  : 'border-red-400/25 bg-red-400/10 text-red-500'
              }`}>
                <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-red-500'}`} />
                {isConnected ? 'Online' : 'Offline'}
              </span>
            )}

            {onLogout && (
              <button
                onClick={onLogout}
                className="inline-flex items-center gap-2 rounded-lg border border-[#e5e7eb] bg-white px-3 py-2 text-sm font-medium text-[#6b7280] transition duration-200 hover:-translate-y-0.5 hover:bg-blue-50 hover:text-[#111827] active:scale-[0.98] dark:border-[#374151] dark:bg-[#111827] dark:text-[#9ca3af] dark:hover:bg-[#1f2937] dark:hover:text-[#e5e7eb]"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            )}
          </div>
        </div>
      </header>
    </>
  )
}
