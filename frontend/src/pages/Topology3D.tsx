import { useEffect, useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { 
  Container, 
  Layers, 
  Cpu, 
  HardDrive, 
  Network,
  RefreshCw,
  Play,
  Square,
  AlertTriangle
} from 'lucide-react'
import Header from '@/components/Header'
import { api } from '@/services/api'
import { useAuth } from '@/App'
import * as THREE from 'three'

interface ContainerNode {
  id: string
  name: string
  status: string
  image: string
  cpu: number
  memory: number
}

export default function Topology() {
  const { containers, logout, isConnected } = useAuth()
  const mountRef = useRef<HTMLDivElement>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [containerNodes, setContainerNodes] = useState<ContainerNode[]>([])

  const loadData = useCallback(async () => {
    try {
      const stats = await api.getAllContainerStats()
      const nodes: ContainerNode[] = (stats.containers || []).map((c: any) => ({
        id: c.container_id,
        name: c.name || c.container_id?.slice(0, 12),
        status: 'running',
        image: 'unknown',
        cpu: c.cpu_percent || 0,
        memory: c.memory_percent || 0
      }))
      setContainerNodes(nodes)
    } catch (err) {
      console.error('Failed to load container stats:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    const mount = mountRef.current
    if (!mount || containerNodes.length === 0) return

    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0x0a0a0f, 0.08)

    const camera = new THREE.PerspectiveCamera(60, mount.clientWidth / mount.clientHeight, 0.1, 100)
    camera.position.set(0, 3, 8)
    camera.lookAt(0, 0, 0)

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true })
    } catch (e) {
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    renderer.setClearColor(0x0a0a0f)
    mount.appendChild(renderer.domElement)

    const runningContainers = containerNodes.filter(c => c.status === 'running')
    const spacing = Math.max(2, Math.min(4, runningContainers.length))
    const nodeMap = new Map<string, THREE.Mesh>()

    runningContainers.forEach((container, index) => {
      const geo = new THREE.SphereGeometry(0.3, 32, 32)
      
      const cpu = container.cpu || 0
      const color = cpu > 75 ? 0xff4444 : cpu > 50 ? 0xffaa44 : cpu > 25 ? 0x44ff88 : 0x44aaff
      
      const mat = new THREE.MeshPhongMaterial({
        color,
        emissive: new THREE.Color(color).multiplyScalar(0.3),
        shininess: 80
      })
      
      const mesh = new THREE.Mesh(geo, mat)
      
      const row = Math.floor(index / spacing)
      const col = index % spacing
      const x = (col - (spacing - 1) / 2) * 1.8
      const z = (row - Math.floor(runningContainers.length / spacing) / 2) * 1.8
      const y = Math.sin(index * 0.5) * 0.3
      
      mesh.position.set(x, y, z)
      scene.add(mesh)
      nodeMap.set(container.id, mesh)
    })

    containerNodes.forEach((container, index) => {
      if (container.status !== 'running') {
        const geo = new THREE.BoxGeometry(0.4, 0.4, 0.4)
        const mat = new THREE.MeshLambertMaterial({ color: 0x666666 })
        const mesh = new THREE.Mesh(geo, mat)
        
        const row = Math.floor(index / spacing)
        const col = index % spacing
        mesh.position.set(
          (col - (spacing - 1) / 2) * 1.8,
          0,
          (row - Math.floor(containerNodes.length / spacing) / 2) * 1.8
        )
        scene.add(mesh)
      }
    })

    nodeMap.forEach((mesh, id) => {
      const connected = containerNodes.slice(0, 3)
      connected.forEach((_, i) => {
        const otherMesh = Array.from(nodeMap.values())[i]
        if (otherMesh && otherMesh !== mesh) {
          const points = [mesh.position, otherMesh.position]
          const curve = new THREE.LineCurve3(points[0], points[1])
          const tubeGeo = new THREE.TubeGeometry(curve, 8, 0.02, 4, false)
          const tubeMat = new THREE.MeshBasicMaterial({ 
            color: 0x4466aa, 
            transparent: true, 
            opacity: 0.3 
          })
          const tube = new THREE.Mesh(tubeGeo, tubeMat)
          scene.add(tube)
        }
      })
    })
  }, [containerNodes])

  const statusColor = (status: string) => {
    switch (status) {
      case 'running': return 'text-emerald-500'
      case 'paused': return 'text-amber-500'
      default: return 'text-slate-400'
    }
  }

  return (
    <div className="app-surface relative overflow-hidden">
      <Header 
        title="Topology" 
        icon={<Layers size={24} />} 
        onRefresh={loadData}
        isConnected={isConnected}
        onLogout={logout}
      />

      <main className="app-main z-10 flex flex-col lg:flex-row">
        <div className="dashboard-card mb-6 lg:mb-0 lg:mr-6 lg:w-80 shrink-0">
          <h3 className="mb-4 text-lg font-semibold text-[#111827] dark:text-white">
            Containers ({containerNodes.length})
          </h3>
          <div className="max-h-[60vh] space-y-2 overflow-y-auto">
            {containerNodes.map((container) => (
              <div
                key={container.id}
                className="flex items-center justify-between rounded-lg bg-slate-50 p-3 dark:bg-slate-800/50"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-[#111827] dark:text-white">
                    {container.name}
                  </p>
                  <p className="text-xs text-slate-500">
                    {container.id?.slice(0, 12)}
                  </p>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-medium ${statusColor(container.status)}`}>
                    {container.status}
                  </p>
                  <p className="text-xs text-slate-500">
                    CPU: {container.cpu?.toFixed(1)}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="dashboard-card flex-1 min-h-[400px] relative">
          <h3 className="mb-4 text-lg font-semibold text-[#111827] dark:text-white">
            3D Cluster View
          </h3>
          <div ref={mountRef} className="absolute inset-0 w-full min-h-[400px]" />
          {!loading && containerNodes.length === 0 && (
            <div className="flex h-full items-center justify-center">
              <div className="text-center text-slate-500">
                <Network className="mx-auto h-12 w-12" />
                <p className="mt-4">No containers to visualize</p>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}