import { useState, useEffect, ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorInfo {
  componentStack?: string
}

export default function ErrorBoundary({ children, fallback }: Props) {
  const [hasError, setHasError] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      console.error('Error caught by boundary:', event.error)
      setError(event.error || new Error('Unknown error'))
      setHasError(true)
    }

    const handleRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection:', event.reason)
      setError(event.reason instanceof Error ? event.reason : new Error(String(event.reason)))
      setHasError(true)
    }

    window.addEventListener('error', handleError)
    window.addEventListener('unhandledrejection', handleRejection)

    return () => {
      window.removeEventListener('error', handleError)
      window.removeEventListener('unhandledrejection', handleRejection)
    }
  }, [])

  const handleReset = () => {
    setHasError(false)
    setError(null)
    window.location.href = '/'
  }

  if (hasError) {
    if (fallback) {
      return fallback
    }

    return (
      <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center p-6">
        <div className="bg-gray-800 p-8 rounded-lg max-w-md text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-red-500/20 rounded-full">
              <AlertTriangle className="w-12 h-12 text-red-400" />
            </div>
          </div>
          <h1 className="text-2xl font-bold mb-2">Something went wrong</h1>
          <p className="text-gray-400 mb-6">
            An unexpected error occurred. Please try again.
          </p>
          {error && (
            <div className="bg-gray-900 p-3 rounded text-left mb-6 overflow-auto max-h-32">
              <p className="text-sm text-red-400 font-mono">
                {error.message || 'Unknown error'}
              </p>
            </div>
          )}
          <button
            onClick={handleReset}
            className="flex items-center gap-2 mx-auto bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return children
}