import { useState, FormEvent } from 'react'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { Activity, Boxes, Container, Eye, EyeOff, KeyRound, Lock, ShieldCheck, UserRound } from 'lucide-react'
import ThreeLoginBackground from '@/components/ThreeLoginBackground'

function Login() {
  const [username, setUsername] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const [showPassword, setShowPassword] = useState<boolean>(false)
  const [twoFactorCode, setTwoFactorCode] = useState<string>('')
  const [requires2FA, setRequires2FA] = useState<boolean>(false)
  const [userId, setUserId] = useState<number | null>(null)
  const [error, setError] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const { login: authLogin } = useAuth()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      if (requires2FA) {
        const currentUserId = userId || parseInt(localStorage.getItem('pendingUserId') || '0', 10)
        if (!currentUserId) {
          setError('Session expired. Please login again.')
          setRequires2FA(false)
          setIsLoading(false)
          return
        }
        const data = await api.verify2FA(currentUserId, twoFactorCode)
        authLogin(data.access_token, currentUserId)
        localStorage.removeItem('pendingUserId')
      } else {
        const data = await api.login({ username, password })
        if (data.requires_2fa) {
          setRequires2FA(true)
          setIsLoading(false)
          const newUserId = data.user_id || null
          setUserId(newUserId)
          if (newUserId) {
            localStorage.setItem('pendingUserId', String(newUserId))
          }
        } else {
          authLogin(data.access_token, data.user_id)
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleResend = () => {
    setRequires2FA(false)
    setUserId(null)
    setTwoFactorCode('')
  }

  return (
    <div className="login-page relative flex min-h-screen overflow-hidden bg-[#0b1120] font-sans text-[#e5e7eb]">
      <div className="login-gradient absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(37,99,235,0.32),transparent_30%),radial-gradient(circle_at_82%_8%,rgba(79,70,229,0.3),transparent_28%),linear-gradient(135deg,rgba(11,17,32,0.98),rgba(2,6,23,1))]" />
      <ThreeLoginBackground />
      <div className="absolute -left-28 top-16 h-72 w-72 rounded-full border border-blue-500/20 bg-blue-500/10 blur-2xl" />
      <div className="absolute -right-20 bottom-12 h-80 w-80 rounded-full border border-indigo-500/20 bg-indigo-500/10 blur-2xl" />
      <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-blue-950/45 to-transparent" />
      <div className="relative grid min-h-screen w-full lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden flex-col justify-between border-r border-white/10 p-10 lg:flex">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 text-white shadow-xl shadow-blue-500/25">
              <Container className="h-6 w-6" />
            </div>
            <div>
              <p className="text-lg font-bold">DockWatch</p>
              <p className="text-sm text-[#9ca3af]">Container observability console</p>
            </div>
          </div>

          <div className="max-w-xl">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-blue-500/20 bg-blue-500/10 px-3 py-1 text-sm font-medium text-blue-600 dark:text-blue-300">
              <ShieldCheck className="h-4 w-4" />
              Secure Docker operations
            </div>
            <h1 className="text-5xl font-semibold leading-tight text-[#e5e7eb]">
              Admin access for production Docker monitoring.
            </h1>
            <p className="mt-5 max-w-lg text-base leading-7 text-[#9ca3af]">
              Track health, metrics, logs, ports, and environments from a focused DevOps dashboard built for fast operational decisions.
            </p>
            <div className="mt-8 grid max-w-lg grid-cols-3 gap-3">
              {[
                { icon: <Activity className="h-5 w-5" />, label: 'Live metrics' },
                { icon: <Boxes className="h-5 w-5" />, label: 'Stacks' },
                { icon: <Lock className="h-5 w-5" />, label: 'Protected' }
              ].map((item) => (
                <div key={item.label} className="rounded-xl border border-white/10 bg-[#111827]/58 p-4 shadow-lg shadow-black/20 backdrop-blur-xl">
                  <div className="text-blue-500">{item.icon}</div>
                  <p className="mt-3 text-sm font-medium">{item.label}</p>
                </div>
              ))}
            </div>
          </div>

          <p className="text-sm text-slate-500 dark:text-slate-500">Grafana-inspired telemetry for Docker workloads.</p>
        </section>

        <section className="flex items-center justify-center px-4 py-10 sm:px-6">
          <div className="login-card w-full max-w-md rounded-2xl border border-white/12 bg-[#111827]/72 p-7 shadow-2xl shadow-black/40 backdrop-blur-2xl sm:p-8">
            <div className="mb-7 flex items-center gap-3 lg:hidden">
              <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-violet-600 text-white">
                <Container className="h-5 w-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold">DockWatch</h1>
                <p className="text-sm text-[#9ca3af]">Container monitoring</p>
              </div>
            </div>

            <div className="mb-7">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-blue-500">Welcome back</p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[#e5e7eb]">{requires2FA ? 'Verify your session' : 'Sign in'}</h2>
              <p className="mt-2 text-sm text-[#9ca3af]">
                {requires2FA ? 'Enter the authentication code from your device.' : 'Use your username and password to continue.'}
              </p>
            </div>
        
        {error && (
          <div className="mb-4 rounded-lg border border-red-400/20 bg-red-500/10 p-3 text-sm text-red-500 dark:text-red-300">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-5">
          {!requires2FA ? (
            <>
              <div>
                <label htmlFor="username" className="mb-2 block text-sm font-medium text-[#e5e7eb]">Username</label>
                <div className="relative">
                  <UserRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    id="username"
                    type="text"
                    name="username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="w-full rounded-xl border border-[#374151] bg-[#0b1120]/70 px-4 py-3 pl-11 text-[#e5e7eb] outline-none transition placeholder:text-[#6b7280] focus:border-[#3b82f6] focus:ring-4 focus:ring-[#3b82f6]/20"
                    placeholder="Enter username"
                    required
                    autoComplete="username"
                  />
                </div>
              </div>
              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium text-[#e5e7eb]">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-xl border border-[#374151] bg-[#0b1120]/70 px-4 py-3 pl-11 pr-11 text-[#e5e7eb] outline-none transition placeholder:text-[#6b7280] focus:border-[#3b82f6] focus:ring-4 focus:ring-[#3b82f6]/20"
                    placeholder="Enter password"
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-400 transition hover:bg-blue-500/10 hover:text-blue-500"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <div>
                <label htmlFor="twoFactorCode" className="mb-2 block text-sm font-medium text-slate-600 dark:text-slate-300">Authentication Code</label>
                <input
                  id="twoFactorCode"
                  type="text"
                  inputMode="numeric"
                  name="one-time-code"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  placeholder="Enter 6-digit code"
                  className="w-full rounded-xl border border-[#374151] bg-[#0b1120]/70 px-4 py-3 text-[#e5e7eb] outline-none transition placeholder:text-[#6b7280] focus:border-[#3b82f6] focus:ring-4 focus:ring-[#3b82f6]/20"
                  required
                  maxLength={6}
                  autoComplete="one-time-code"
                />
                <p className="mt-2 text-xs text-slate-500">Enter the 6-digit code from your authenticator app</p>
              </div>
              
              <button
                type="button"
                onClick={handleResend}
                className="text-sm font-medium text-blue-500 transition hover:text-violet-500"
                aria-label="Back to login"
              >
                Back to login
              </button>
            </>
          )}
          
          <button
            type="submit"
            disabled={isLoading}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#2563eb] via-[#3b82f6] to-[#4f46e5] px-4 py-3 font-semibold text-white shadow-lg shadow-blue-500/25 transition duration-200 hover:-translate-y-0.5 hover:brightness-110 hover:shadow-blue-500/35 active:scale-[0.98] disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isLoading ? (
              <span>Signing in...</span>
            ) : (
              <>
                {requires2FA ? <KeyRound className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
                {requires2FA ? 'Verify' : 'Sign In'}
              </>
            )}
          </button>
        </form>
          </div>
        </section>
      </div>
    </div>
  )
}

export default Login
