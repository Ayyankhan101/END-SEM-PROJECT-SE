import { useState, FormEvent } from 'react'
import { useAuth } from '@/App'
import { api } from '@/services/api'
import { Container, Lock, KeyRound } from 'lucide-react'

function Login() {
  const [username, setUsername] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const [twoFactorCode, setTwoFactorCode] = useState<string>('')
  const [requires2FA, setRequires2FA] = useState<boolean>(false)
  const [userId, setUserId] = useState<number | null>(null)
  const [error, setError] = useState<string>('')
  const { login: authLogin } = useAuth()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (requires2FA) {
        const data = await api.verify2FA(userId!, twoFactorCode)
        authLogin(data.access_token)
      } else {
        const data = await api.login({ username, password })
        if (data.requires_2fa) {
          setRequires2FA(true)
          setUserId(data.user_id || null)
        } else {
          authLogin(data.access_token)
        }
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    }
  }

  const handleResend = () => {
    setRequires2FA(false)
    setUserId(null)
    setTwoFactorCode('')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-96">
        <div className="flex items-center justify-center mb-6">
          <Container className="w-12 h-12 text-blue-500" />
        </div>
        <h1 className="text-2xl font-bold text-white text-center mb-6">DockWatch</h1>
        
        {error && (
          <div className="bg-red-500/20 text-red-400 p-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          {!requires2FA ? (
            <>
              <div className="mb-4">
                <label className="block text-gray-400 text-sm mb-2">Username</label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
              
              <div className="mb-6">
                <label className="block text-gray-400 text-sm mb-2">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                />
              </div>
            </>
          ) : (
            <>
              <div className="mb-4">
                <label className="block text-gray-400 text-sm mb-2">Authentication Code</label>
                <input
                  type="text"
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value)}
                  placeholder="Enter 6-digit code"
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                  maxLength={6}
                  autoComplete="one-time-code"
                />
                <p className="text-gray-500 text-xs mt-2">Enter the 6-digit code from your authenticator app</p>
              </div>
              
              <button
                type="button"
                onClick={handleResend}
                className="text-blue-400 text-sm hover:text-blue-300 mb-4"
              >
                ← Back to login
              </button>
            </>
          )}
          
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
          >
            {requires2FA ? <KeyRound className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
            {requires2FA ? 'Verify' : 'Sign In'}
          </button>
        </form>
        
        <p className="text-gray-500 text-xs text-center mt-4">
          Check logs for temporary password on first start
        </p>
      </div>
    </div>
  )
}

export default Login