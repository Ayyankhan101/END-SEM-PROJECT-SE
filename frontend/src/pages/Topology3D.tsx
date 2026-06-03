import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import {
  Layers,
  Network,
  Play,
  Square,
  Search,
  Sparkles,
  X,
  Cpu,
  HardDrive,
} from 'lucide-react'
import Header from '@/components/Header'
import { api } from '@/services/api'
import { useAuth } from '@/App'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'

interface ContainerNode {
  id: string
  name: string
  status: string
  cpu: number
  memory: number
  network: string
}

// Live metrics pushed into a ref each poll so the render loop can lerp toward
// them without tearing down and rebuilding the whole scene every 3s.
interface LiveMetric {
  cpu: number
  memory: number
  status: string
}

const short = (id: string) => (id || '').slice(0, 12)

// Deterministic hue per network name → stable cluster colours across reloads.
const hueFromString = (s: string): number => {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360
  return h
}

const cpuColor = (cpu: number): number =>
  cpu > 75 ? 0xff4444 : cpu > 50 ? 0xffaa44 : cpu > 25 ? 0x44ff88 : 0x44aaff

export default function Topology() {
  const { logout, isConnected } = useAuth()
  const mountRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  const [loading, setLoading] = useState<boolean>(true)
  const [nodes, setNodes] = useState<ContainerNode[]>([])
  const [networkSig, setNetworkSig] = useState<string>('')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState<string>('')
  const [bloomOn, setBloomOn] = useState<boolean>(true)
  const [actionMsg, setActionMsg] = useState<string>('')

  // Refs the render loop / event handlers read without forcing re-init.
  const nodesRef = useRef<ContainerNode[]>([])
  const liveRef = useRef<Map<string, LiveMetric>>(new Map())
  const selectedRef = useRef<string | null>(null)
  const searchRef = useRef<string>('')
  const bloomRef = useRef<boolean>(true)
  const networksRef = useRef<Map<string, string[]>>(new Map())

  useEffect(() => { selectedRef.current = selectedId }, [selectedId])
  useEffect(() => { searchRef.current = search.toLowerCase() }, [search])
  useEffect(() => { bloomRef.current = bloomOn }, [bloomOn])

  const loadData = useCallback(async () => {
    try {
      const [stats, networks] = await Promise.all([
        api.getAllContainerStats(),
        api.getNetworks().catch(() => [] as any[]),
      ])

      // containerId(12) -> [networkName, ...]
      const membership = new Map<string, string[]>()
      const netContainers = new Map<string, string[]>()
      ;(networks || []).forEach((net: any) => {
        const members: string[] = (net.containers || []).map(short)
        netContainers.set(net.name, members)
        members.forEach((cid) => {
          const list = membership.get(cid) || []
          list.push(net.name)
          membership.set(cid, list)
        })
      })
      networksRef.current = netContainers

      const live = new Map<string, LiveMetric>()
      const next: ContainerNode[] = (stats.containers || []).map((c: any) => {
        const id = c.container_id
        const cpu = c.cpu_percent || 0
        const memory = c.memory_percent || 0
        live.set(short(id), { cpu, memory, status: 'running' })
        return {
          id,
          name: c.name || short(id),
          status: 'running',
          cpu,
          memory,
          network: (membership.get(short(id)) || ['bridge'])[0],
        }
      })
      liveRef.current = live
      setNodes(next)
      // Signature drives scene rebuild only on structural change.
      setNetworkSig(
        next.map((n) => `${short(n.id)}:${n.network}`).sort().join(',')
      )
    } catch (err) {
      console.error('Failed to load topology data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
    const t = setInterval(loadData, 3000)
    return () => clearInterval(t)
  }, [loadData])

  useEffect(() => { nodesRef.current = nodes }, [nodes])

  // Rebuild the scene only when the set of nodes / their network changes.
  const sceneKey = useMemo(() => networkSig, [networkSig])

  useEffect(() => {
    const mount = mountRef.current
    const current = nodesRef.current
    if (!mount || current.length === 0) return

    const scene = new THREE.Scene()
    scene.fog = new THREE.FogExp2(0x05060a, 0.045)

    const ambient = new THREE.AmbientLight(0xffffff, 0.5)
    scene.add(ambient)
    const key = new THREE.PointLight(0x88aaff, 2.2, 60)
    key.position.set(8, 10, 8)
    scene.add(key)
    const rim = new THREE.PointLight(0xff5588, 1.4, 60)
    rim.position.set(-8, -6, -8)
    scene.add(rim)

    const w = mount.clientWidth
    const h = mount.clientHeight || 420

    // --- cluster layout: one ring slot per network ---
    const byNetwork = new Map<string, ContainerNode[]>()
    current.forEach((n) => {
      const arr = byNetwork.get(n.network) || []
      arr.push(n)
      byNetwork.set(n.network, arr)
    })
    const netNames = Array.from(byNetwork.keys())
    const clusterCount = netNames.length
    const ringR = Math.max(4, clusterCount * 2.2)
    const clusterCenter = new Map<string, THREE.Vector3>()
    netNames.forEach((name, i) => {
      const a = (i / Math.max(1, clusterCount)) * Math.PI * 2
      clusterCenter.set(
        name,
        new THREE.Vector3(Math.cos(a) * ringR, 0, Math.sin(a) * ringR)
      )
    })

    const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 500)
    const camDist = ringR * 2.2 + 6
    camera.position.set(0, camDist * 0.55, camDist)
    camera.lookAt(0, 0, 0)

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    } catch {
      return
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(w, h)
    renderer.setClearColor(0x05060a, 1)
    mount.appendChild(renderer.domElement)

    // Post-processing (bloom). Render through the composer when bloom is on.
    const composer = new EffectComposer(renderer)
    composer.addPass(new RenderPass(scene, camera))
    const bloom = new UnrealBloomPass(new THREE.Vector2(w, h), 0.9, 0.5, 0.15)
    composer.addPass(bloom)
    composer.setSize(w, h)
    composer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.autoRotate = true
    controls.autoRotateSpeed = 0.6
    controls.minDistance = 3
    controls.maxDistance = camDist * 2.5
    let idleTimer: ReturnType<typeof setTimeout> | null = null
    controls.addEventListener('start', () => {
      controls.autoRotate = false
      if (idleTimer) clearTimeout(idleTimer)
    })
    controls.addEventListener('end', () => {
      if (idleTimer) clearTimeout(idleTimer)
      idleTimer = setTimeout(() => { controls.autoRotate = true }, 4000)
    })

    const makeLabel = (text: string): THREE.Sprite => {
      const canvas = document.createElement('canvas')
      const ctx = canvas.getContext('2d')!
      const font = 44
      ctx.font = `bold ${font}px sans-serif`
      const pad = 22
      const tw = ctx.measureText(text).width
      canvas.width = tw + pad * 2
      canvas.height = font + pad
      ctx.font = `bold ${font}px sans-serif`
      ctx.fillStyle = 'rgba(8,10,20,0.7)'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.fillStyle = '#ffffff'
      ctx.textBaseline = 'middle'
      ctx.fillText(text, pad, canvas.height / 2)
      const tex = new THREE.CanvasTexture(canvas)
      tex.minFilter = THREE.LinearFilter
      const sprite = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false })
      )
      const lh = 0.5
      sprite.scale.set((canvas.width / canvas.height) * lh, lh, 1)
      sprite.position.set(0, 0.7, 0)
      return sprite
    }

    interface MeshMeta {
      mesh: THREE.Mesh
      id: string
      name: string
      netColor: THREE.Color
    }
    const metas: MeshMeta[] = []
    const meshById = new Map<string, THREE.Mesh>()
    const draggable: THREE.Mesh[] = []

    // Place each container inside its network cluster (small spiral).
    byNetwork.forEach((members, netName) => {
      const center = clusterCenter.get(netName)!
      const netColor = new THREE.Color().setHSL(hueFromString(netName) / 360, 0.6, 0.55)
      members.forEach((node, i) => {
        const running = node.status === 'running'
        const color = cpuColor(node.cpu)
        const mesh = running
          ? new THREE.Mesh(
              new THREE.SphereGeometry(0.3, 32, 32),
              new THREE.MeshPhongMaterial({
                color,
                emissive: new THREE.Color(color).multiplyScalar(0.3),
                shininess: 80,
              })
            )
          : new THREE.Mesh(
              new THREE.BoxGeometry(0.4, 0.4, 0.4),
              new THREE.MeshLambertMaterial({ color: 0x666666 })
            )
        const ring = Math.floor(Math.sqrt(i))
        const ang = i * 2.399 // golden angle spiral
        const rr = ring * 0.9
        mesh.position.set(
          center.x + Math.cos(ang) * rr,
          Math.sin(i * 0.6) * 0.3,
          center.z + Math.sin(ang) * rr
        )
        mesh.add(makeLabel(node.name))
        scene.add(mesh)
        meshById.set(short(node.id), mesh)
        draggable.push(mesh)
        metas.push({ mesh, id: short(node.id), name: node.name, netColor })
      })
    })

    // Links: connect every member of a network to its cluster centroid hub.
    interface LinkRec { a: THREE.Mesh; center: THREE.Vector3; line: THREE.Line }
    const links: LinkRec[] = []
    networksRef.current.forEach((members, netName) => {
      const center = clusterCenter.get(netName)
      if (!center) return
      const netColor = new THREE.Color().setHSL(hueFromString(netName) / 360, 0.7, 0.6)
      members.forEach((cid) => {
        const mesh = meshById.get(cid)
        if (!mesh) return
        const geom = new THREE.BufferGeometry().setFromPoints([
          mesh.position.clone(),
          center.clone(),
        ])
        const line = new THREE.Line(
          geom,
          new THREE.LineBasicMaterial({ color: netColor, transparent: true, opacity: 0.35 })
        )
        scene.add(line)
        links.push({ a: mesh, center, line })
      })
    })

    // --- pointer: drag nodes, hover tooltip, click to select ---
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    const dragPlane = new THREE.Plane()
    const hit = new THREE.Vector3()
    const offset = new THREE.Vector3()
    const camDir = new THREE.Vector3()
    let dragged: THREE.Mesh | null = null
    let downPos = { x: 0, y: 0 }
    let moved = false
    const dom = renderer.domElement
    const tip = tooltipRef.current

    const setPointer = (e: PointerEvent) => {
      const rect = dom.getBoundingClientRect()
      pointer.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      pointer.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
    }

    const onDown = (e: PointerEvent) => {
      setPointer(e)
      downPos = { x: e.clientX, y: e.clientY }
      moved = false
      raycaster.setFromCamera(pointer, camera)
      const hits = raycaster.intersectObjects(draggable, false)
      if (hits.length) {
        dragged = hits[0].object as THREE.Mesh
        controls.enabled = false
        camera.getWorldDirection(camDir)
        dragPlane.setFromNormalAndCoplanarPoint(camDir.clone().negate(), dragged.position)
        if (raycaster.ray.intersectPlane(dragPlane, hit)) offset.copy(hit).sub(dragged.position)
        dom.style.cursor = 'grabbing'
      }
    }

    const onMove = (e: PointerEvent) => {
      if (Math.abs(e.clientX - downPos.x) + Math.abs(e.clientY - downPos.y) > 4) moved = true
      setPointer(e)
      raycaster.setFromCamera(pointer, camera)

      if (dragged) {
        if (raycaster.ray.intersectPlane(dragPlane, hit)) dragged.position.copy(hit.sub(offset))
        return
      }

      const hits = raycaster.intersectObjects(draggable, false)
      if (hits.length && tip) {
        const meta = metas.find((m) => m.mesh === hits[0].object)
        const m = meta ? liveRef.current.get(meta.id) : null
        dom.style.cursor = 'grab'
        if (meta) {
          const rect = mount.getBoundingClientRect()
          tip.style.display = 'block'
          tip.style.left = `${e.clientX - rect.left + 14}px`
          tip.style.top = `${e.clientY - rect.top + 14}px`
          tip.innerHTML =
            `<div style="font-weight:600">${meta.name}</div>` +
            `<div>CPU ${(m?.cpu ?? 0).toFixed(1)}% · MEM ${(m?.memory ?? 0).toFixed(1)}%</div>` +
            `<div style="opacity:.7">${m?.status ?? 'unknown'}</div>`
        }
      } else if (tip) {
        dom.style.cursor = 'default'
        tip.style.display = 'none'
      }
    }

    const onUp = (e: PointerEvent) => {
      if (dragged && !moved) {
        const meta = metas.find((m) => m.mesh === dragged)
        if (meta) setSelectedId(meta.id)
      } else if (!dragged && !moved) {
        // Click on empty space → check for node selection.
        setPointer(e)
        raycaster.setFromCamera(pointer, camera)
        const hits = raycaster.intersectObjects(draggable, false)
        if (hits.length) {
          const meta = metas.find((m) => m.mesh === hits[0].object)
          if (meta) setSelectedId(meta.id)
        }
      }
      dragged = null
      controls.enabled = true
      dom.style.cursor = 'default'
    }

    dom.addEventListener('pointerdown', onDown)
    dom.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)

    // --- render loop: lerp visuals toward live metrics ---
    const clock = new THREE.Clock()
    let animId: number
    const animate = () => {
      animId = requestAnimationFrame(animate)
      const t = clock.getElapsedTime()
      controls.update()

      const sel = selectedRef.current
      const q = searchRef.current

      metas.forEach((meta) => {
        const m = liveRef.current.get(meta.id)
        const cpu = m?.cpu ?? 0
        const mem = m?.memory ?? 0
        const mat = meta.mesh.material as THREE.MeshPhongMaterial
        if (mat && (mat as any).emissive) {
          const base = new THREE.Color(cpuColor(cpu))
          mat.color.lerp(base, 0.1)
          // Pulse emissive faster the busier the container is.
          const pulse = 0.25 + Math.abs(Math.sin(t * (1 + cpu / 30))) * (cpu / 200 + 0.1)
          mat.emissive.lerp(base.clone().multiplyScalar(pulse), 0.15)
        }
        // Size tracks memory usage.
        const target = 0.7 + (mem / 100) * 1.1
        const s = THREE.MathUtils.lerp(meta.mesh.scale.x, target, 0.1)
        meta.mesh.scale.setScalar(s)

        // Search dim + selection emphasis.
        const matched = !q || meta.name.toLowerCase().includes(q)
        const isSel = sel === meta.id
        if (mat) {
          mat.opacity = matched ? 1 : 0.12
          mat.transparent = !matched
        }
        const label = meta.mesh.children[0] as THREE.Sprite | undefined
        if (label && label.material) {
          (label.material as THREE.SpriteMaterial).opacity = matched ? (isSel ? 1 : 0.85) : 0.1
        }
        if (isSel) meta.mesh.scale.setScalar(s * 1.35)
      })

      links.forEach(({ a, center, line }) => {
        const pos = line.geometry.attributes.position as THREE.BufferAttribute
        pos.setXYZ(0, a.position.x, a.position.y, a.position.z)
        pos.setXYZ(1, center.x, center.y, center.z)
        pos.needsUpdate = true
      })

      if (bloomRef.current) composer.render()
      else renderer.render(scene, camera)
    }
    animate()

    const onResize = () => {
      const nw = mount.clientWidth
      const nh = mount.clientHeight || 420
      camera.aspect = nw / nh
      camera.updateProjectionMatrix()
      renderer.setSize(nw, nh)
      composer.setSize(nw, nh)
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(animId)
      if (idleTimer) clearTimeout(idleTimer)
      window.removeEventListener('resize', onResize)
      dom.removeEventListener('pointerdown', onDown)
      dom.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
      controls.dispose()
      composer.dispose()
      renderer.dispose()
      scene.traverse((o) => {
        const mesh = o as THREE.Mesh
        if (mesh.geometry) mesh.geometry.dispose()
        const mat = (mesh as any).material
        if (Array.isArray(mat)) mat.forEach((mm: THREE.Material) => mm.dispose())
        else if (mat) (mat as THREE.Material).dispose()
      })
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement)
    }
  }, [sceneKey])

  const selected = nodes.find((n) => short(n.id) === selectedId) || null

  const doAction = async (action: 'start' | 'stop') => {
    if (!selected) return
    setActionMsg(`${action === 'start' ? 'Starting' : 'Stopping'} ${selected.name}…`)
    try {
      if (action === 'start') await api.startContainer(selected.id)
      else await api.stopContainer(selected.id)
      setActionMsg(`${selected.name} ${action}ed`)
      await loadData()
    } catch (err) {
      setActionMsg(`Failed to ${action} ${selected.name}`)
      console.error(err)
    }
  }

  const statusColor = (status: string) =>
    status === 'running' ? 'text-emerald-500'
    : status === 'paused' ? 'text-amber-500'
    : 'text-slate-400'

  const visible = nodes.filter(
    (n) => !search || n.name.toLowerCase().includes(search.toLowerCase())
  )

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
        <div className="dashboard-card mb-6 lg:mb-0 lg:mr-6 lg:w-80 shrink-0 flex flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-[#111827] dark:text-white">
              Containers ({nodes.length})
            </h3>
            <button
              onClick={() => setBloomOn((b) => !b)}
              title="Toggle bloom glow"
              className={`flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${
                bloomOn
                  ? 'bg-indigo-500/15 text-indigo-500'
                  : 'bg-slate-200 text-slate-500 dark:bg-slate-700'
              }`}
            >
              <Sparkles size={14} /> Glow
            </button>
          </div>

          <div className="relative mb-3">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search containers…"
              className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-8 pr-2 text-sm outline-none focus:border-indigo-400 dark:border-slate-700 dark:bg-slate-800/50 dark:text-white"
            />
          </div>

          {selected && (
            <div className="mb-3 rounded-lg border border-indigo-400/30 bg-indigo-500/5 p-3">
              <div className="mb-2 flex items-start justify-between">
                <div className="min-w-0">
                  <p className="truncate font-semibold text-[#111827] dark:text-white">
                    {selected.name}
                  </p>
                  <p className="truncate text-xs text-slate-500">{short(selected.id)}</p>
                  <p className="text-xs text-slate-400">net: {selected.network}</p>
                </div>
                <button onClick={() => setSelectedId(null)} className="text-slate-400 hover:text-slate-600">
                  <X size={16} />
                </button>
              </div>
              <div className="mb-2 flex gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1"><Cpu size={12} /> {selected.cpu.toFixed(1)}%</span>
                <span className="flex items-center gap-1"><HardDrive size={12} /> {selected.memory.toFixed(1)}%</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => doAction('start')}
                  className="flex flex-1 items-center justify-center gap-1 rounded-md bg-emerald-500/15 py-1.5 text-xs font-medium text-emerald-600 hover:bg-emerald-500/25"
                >
                  <Play size={13} /> Start
                </button>
                <button
                  onClick={() => doAction('stop')}
                  className="flex flex-1 items-center justify-center gap-1 rounded-md bg-rose-500/15 py-1.5 text-xs font-medium text-rose-600 hover:bg-rose-500/25"
                >
                  <Square size={13} /> Stop
                </button>
              </div>
              {actionMsg && <p className="mt-2 text-xs text-slate-400">{actionMsg}</p>}
            </div>
          )}

          <div className="max-h-[50vh] space-y-2 overflow-y-auto">
            {visible.map((c) => (
              <button
                key={c.id}
                onClick={() => setSelectedId(short(c.id))}
                className={`flex w-full items-center justify-between rounded-lg p-3 text-left transition ${
                  selectedId === short(c.id)
                    ? 'bg-indigo-500/15 ring-1 ring-indigo-400/40'
                    : 'bg-slate-50 hover:bg-slate-100 dark:bg-slate-800/50 dark:hover:bg-slate-800'
                }`}
              >
                <div className="min-w-0">
                  <p className="truncate font-medium text-[#111827] dark:text-white">{c.name}</p>
                  <p className="text-xs text-slate-500">{short(c.id)}</p>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-medium ${statusColor(c.status)}`}>{c.status}</p>
                  <p className="text-xs text-slate-500">CPU: {c.cpu.toFixed(1)}%</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        <div className="dashboard-card flex-1 flex flex-col min-h-[500px]">
          <h3 className="mb-2 text-lg font-semibold text-[#111827] dark:text-white">
            3D Cluster View
          </h3>
          <p className="mb-2 text-xs text-slate-400">
            Drag to orbit · scroll to zoom · click a node to select · drag a node to move it
          </p>
          <div className="relative flex-1 min-h-[420px] rounded-lg overflow-hidden bg-[#05060a]">
            <div ref={mountRef} className="w-full h-full" style={{ minHeight: 420 }} />
            <div
              ref={tooltipRef}
              className="pointer-events-none absolute z-20 hidden rounded-md bg-slate-900/90 px-2 py-1 text-xs text-white shadow-lg"
              style={{ display: 'none' }}
            />
            {!loading && nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-center text-slate-500">
                  <Network className="mx-auto h-12 w-12" />
                  <p className="mt-4">No containers to visualize</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
