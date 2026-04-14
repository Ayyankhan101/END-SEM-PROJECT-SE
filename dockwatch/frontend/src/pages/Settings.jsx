import { Link } from 'react-router-dom'
import { ArrowLeft, Settings as SettingsIcon } from 'lucide-react'

function Settings() {
  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="p-6">
        <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white mb-6">
          <ArrowLeft className="w-4 h-4" />
          Back to Dashboard
        </Link>

        <h1 className="text-2xl font-bold mb-6">Settings</h1>

        <div className="bg-gray-800 p-6 rounded-lg max-w-2xl">
          <div className="flex items-center gap-3 mb-4">
            <SettingsIcon className="w-6 h-6 text-blue-500" />
            <h2 className="text-xl font-medium">Configuration</h2>
          </div>

          <p className="text-gray-400 mb-4">
            DockWatch is configured via YAML configuration file. The configuration file is located at:
          </p>

          <div className="bg-gray-900 p-3 rounded font-mono text-sm text-gray-300 mb-4">
            dockwatch/config/config.yaml
          </div>

          <h3 className="font-medium mb-2">Configuration Options:</h3>
          <ul className="text-gray-400 text-sm space-y-1 mb-4">
            <li>• Docker socket path</li>
            <li>• Poll interval (seconds)</li>
            <li>• Monitoring thresholds (CPU, memory)</li>
            <li>• Recovery actions</li>
            <li>• JWT settings</li>
          </ul>

          <h3 className="font-medium mb-2">Default Credentials:</h3>
          <ul className="text-gray-400 text-sm space-y-1">
            <li>• Username: <span className="text-white">admin</span></li>
            <li>• Password: <span className="text-white">admin123</span></li>
          </ul>
        </div>
      </div>
    </div>
  )
}

export default Settings