import { useEffect, useRef } from 'react'
import * as THREE from 'three'

export default function ThreeLoginBackground() {
  const mountRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(55, mount.clientWidth / mount.clientHeight, 0.1, 100)
    camera.position.set(0, 0.35, 6.5)

    let renderer: THREE.WebGLRenderer
    try {
      renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    } catch (e) {
      return // silently skip 3D background if WebGL not available
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.8))
    renderer.setSize(mount.clientWidth, mount.clientHeight)
    renderer.domElement.setAttribute('aria-hidden', 'true')
    mount.appendChild(renderer.domElement)

    const particleCount = 180
    const positions = new Float32Array(particleCount * 3)
    for (let i = 0; i < particleCount; i += 1) {
      positions[i * 3] = (Math.random() - 0.5) * 11
      positions[i * 3 + 1] = (Math.random() - 0.5) * 7
      positions[i * 3 + 2] = (Math.random() - 0.5) * 5
    }

    const particleGeometry = new THREE.BufferGeometry()
    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particles = new THREE.Points(
      particleGeometry,
      new THREE.PointsMaterial({
        color: 0x72a7ff,
        size: 0.035,
        transparent: true,
        opacity: 0.72,
        depthWrite: false
      })
    )
    scene.add(particles)

    const grid = new THREE.GridHelper(12, 36, 0x2563eb, 0x4f46e5)
    grid.position.y = -2.35
    grid.rotation.x = Math.PI * 0.04
    ;(grid.material as THREE.Material).transparent = true
    ;(grid.material as THREE.Material).opacity = 0.18
    scene.add(grid)

    const shapeGroup = new THREE.Group()
    const torus = new THREE.Mesh(
      new THREE.TorusKnotGeometry(0.72, 0.018, 120, 8),
      new THREE.MeshBasicMaterial({ color: 0x3b82f6, transparent: true, opacity: 0.42 })
    )
    torus.position.set(-2.6, 0.9, -0.4)

    const ring = new THREE.Mesh(
      new THREE.TorusGeometry(1.05, 0.012, 12, 96),
      new THREE.MeshBasicMaterial({ color: 0x7c3aed, transparent: true, opacity: 0.34 })
    )
    ring.position.set(2.6, -0.65, -0.8)
    ring.rotation.x = Math.PI * 0.42
    ring.rotation.y = Math.PI * 0.18

    shapeGroup.add(torus, ring)
    scene.add(shapeGroup)

    let animationFrame = 0
    const animate = () => {
      animationFrame = requestAnimationFrame(animate)
      const time = performance.now() * 0.001
      particles.rotation.y = time * 0.035
      particles.rotation.x = Math.sin(time * 0.25) * 0.025
      grid.position.z = (time * 0.18) % 1
      shapeGroup.rotation.y = time * 0.08
      torus.rotation.x = time * 0.16
      torus.rotation.y = time * 0.11
      ring.rotation.z = time * -0.08
      renderer.render(scene, camera)
    }
    animate()

    const handleResize = () => {
      if (!mount.clientWidth || !mount.clientHeight) return
      camera.aspect = mount.clientWidth / mount.clientHeight
      camera.updateProjectionMatrix()
      renderer.setSize(mount.clientWidth, mount.clientHeight)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(animationFrame)
      window.removeEventListener('resize', handleResize)
      particleGeometry.dispose()
      ;(particles.material as THREE.Material).dispose()
      ;(grid.material as THREE.Material).dispose()
      torus.geometry.dispose()
      ;(torus.material as THREE.Material).dispose()
      ring.geometry.dispose()
      ;(ring.material as THREE.Material).dispose()
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [])

  return <div ref={mountRef} className="pointer-events-none absolute inset-0 opacity-80" />
}
