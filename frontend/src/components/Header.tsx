import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Container, Layers, Server, Bell, Settings, FileText, Users, Calendar, Brain, RefreshCw, Menu, X } from 'lucide-react'

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
  { path: '/settings', label: 'Settings', icon: Settings },
]

export default function Header({ title, icon, onRefresh, isConnected, onLogout }: HeaderProps) {
  const location = useLocation()
  const [navOpen, setNavOpen] = useState(false)
  
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        {/* Left: Logo + Title */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="bg-blue-600 p-2 rounded-lg shrink-0">
            {icon}
          </div>
          <h1 className="text-lg font-bold text-white truncate">{title}</h1>
        </div>
        
        {/* Center: Hamburger + Nav (hidden on mobile unless toggled) */}
        <div className="relative">
          <button 
            onClick={() => setNavOpen(!navOpen)}
            className="lg:hidden text-gray-400 hover:text-white p-2"
            aria-label="Toggle menu"
          >
            {navOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
          
          {/* Nav items - scrollable on desktop, dropdown on mobile */}
          <nav className={`
            ${navOpen ? 'absolute top-full right-0 mt-2 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50' : 'hidden'}
            lg:flex lg:static lg:mt-0 lg:bg-transparent lg:border-0 lg:shadow-none lg:overflow-visible
            flex-wrap items-center gap-1 min-w-0
          `}>
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path || 
                (item.path === '/containers' && location.pathname.startsWith('/container'))
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setNavOpen(false)}
                  className={`
                    flex items-center gap-1.5 px-2 py-1.5 rounded text-sm whitespace-nowrap
                    transition-colors
                    ${isActive 
                      ? 'bg-blue-600 text-white' 
                      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    }
                  `}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="hidden xl:inline">{item.label}</span>
                </Link>
              )
            })}
          </nav>
        </div>
        
        {/* Right: Actions */}
        <div className="flex items-center gap-2 shrink-0">
          {onRefresh && (
            <button 
              onClick={onRefresh} 
              className="flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-sm text-white"
              title="Sync containers"
            >
              <RefreshCw className="w-4 h-4" />
              Sync
            </button>
          )}
          
          {isConnected !== undefined && (
            <span className={`flex items-center gap-1.5 text-sm ${
              isConnected ? 'text-green-400' : 'text-red-400'
            }`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
              <span className="hidden sm:inline">{isConnected ? 'Online' : 'Offline'}</span>
            </span>
          )}
          
          {onLogout && (
            <button onClick={onLogout} className="text-gray-400 hover:text-white text-sm px-2 py-1">
              Logout
            </button>
          )}
        </div>
      </div>
    </header>
  )
}