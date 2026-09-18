import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { loadIfcModel, type IfcModel, type LoadProgress } from '../ifc/loadIfcModel'

/** Dev-servern serverer repots data/-mapp, se vite.config.ts (server.fs.allow). */
const IFC_URL = '/data/772_H811_new.ifc'

// Basfärgen på virket sätts i loadIfcModel (delat material); här bara highlight-färgen.
const HIGHLIGHT_COLOR = 0xff4d2e
const DIMMED_OPACITY = 0.18

interface IfcViewerProps {
  /** oid att highlighta (== IFCBEAM.Tag). Sätts av tabellvyerna. */
  selectedOid: string | null
  /** Klick på ett element i 3D-vyn -> tillbaka till tabellen (data/dataspec.md §8). */
  onPickOid?: (oid: string) => void
}

/**
 * 3D-vy av 772_H811_new.ifc med highlight via OID<->Tag (docs/plan.md #4, docs/adr.md ADR-3).
 *
 * Modellen laddas en gång när komponenten monteras och ligger kvar — filen är 18 MB och ska
 * inte parsas om live på scen (docs/prd.md §7). Highlight byter bara material på de meshar
 * som hör till valt oid, ingen omladdning.
 */
export function IfcViewer({ selectedOid, onPickOid }: IfcViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  const modelRef = useRef<IfcModel | null>(null)
  const highlightRef = useRef<THREE.Mesh[]>([])
  const materialsRef = useRef<{ base: THREE.MeshLambertMaterial; highlight: THREE.MeshLambertMaterial } | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsTargetRef = useRef(new THREE.Vector3())
  /** Sätts av mount-effekten: zooma kameran så en markerad bit faktiskt syns. */
  const focusRef = useRef<((box: THREE.Box3) => void) | null>(null)

  const [progress, setProgress] = useState<LoadProgress>({
    phase: 'downloading',
    ratio: 0,
    message: 'Startar...',
  })
  const [error, setError] = useState<string | null>(null)
  const [ready, setReady] = useState(false)
  const [pickedOid, setPickedOid] = useState<string | null>(null)

  // --- Scen, kamera, rendering, muskontroller -------------------------------------------
  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf7f7f5)

    // Near/far sätts om efter att modellen mätts upp — web-ifc levererar geometrin i meter
    // (inte mm som IFC-filen), så en fast klippzon i mm-skala klipper bort hela modellen.
    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 1000)
    cameraRef.current = camera

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mount.appendChild(renderer.domElement)

    scene.add(new THREE.AmbientLight(0xffffff, 1.6))
    const key = new THREE.DirectionalLight(0xffffff, 2.2)
    key.position.set(1, 2, 1.5)
    scene.add(key)
    const fill = new THREE.DirectionalLight(0xffffff, 0.8)
    fill.position.set(-1, -0.5, -1)
    scene.add(fill)

    // Enkel orbit: vänster drag = rotera, hjul = zoom, höger drag = panorera.
    // Skriven för hand i stället för att dra in OrbitControls -- det här är allt vyn behöver.
    const spherical = new THREE.Spherical(1, Math.PI / 3, Math.PI / 4)
    const target = controlsTargetRef.current
    // Sätts när modellen mätts upp; defaulten gäller bara innan dess.
    const zoomLimits = { min: 0.1, max: 1000 }
    let modelExtent = 1
    let dragging: 'orbit' | 'pan' | null = null
    let lastX = 0
    let lastY = 0

    function applyCamera() {
      camera.position.setFromSpherical(spherical).add(target)
      camera.lookAt(target)
    }

    function onPointerDown(event: PointerEvent) {
      dragging = event.button === 2 || event.shiftKey ? 'pan' : 'orbit'
      lastX = event.clientX
      lastY = event.clientY
      renderer.domElement.setPointerCapture(event.pointerId)
    }

    function onPointerMove(event: PointerEvent) {
      if (!dragging) return
      const dx = event.clientX - lastX
      const dy = event.clientY - lastY
      lastX = event.clientX
      lastY = event.clientY

      if (dragging === 'orbit') {
        spherical.theta -= dx * 0.005
        spherical.phi = Math.min(Math.PI - 0.05, Math.max(0.05, spherical.phi - dy * 0.005))
      } else {
        const panScale = spherical.radius * 0.0012
        const right = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 0)
        const up = new THREE.Vector3().setFromMatrixColumn(camera.matrix, 1)
        target.addScaledVector(right, -dx * panScale).addScaledVector(up, dy * panScale)
      }
      applyCamera()
    }

    function onPointerUp(event: PointerEvent) {
      dragging = null
      renderer.domElement.releasePointerCapture(event.pointerId)
    }

    function onWheel(event: WheelEvent) {
      event.preventDefault()
      // Gränserna är relativa till modellens storlek (se zoomLimits), inte absoluta mått.
      const { min, max } = zoomLimits
      spherical.radius = Math.max(min, Math.min(max, spherical.radius * (1 + event.deltaY * 0.001)))
      applyCamera()
    }

    function onContextMenu(event: MouseEvent) {
      event.preventDefault()
    }

    // Klick (utan drag) i 3D -> plocka elementets oid, se data/dataspec.md §8.
    const raycaster = new THREE.Raycaster()
    const pointer = new THREE.Vector2()
    let downX = 0
    let downY = 0

    function rememberDown(event: PointerEvent) {
      downX = event.clientX
      downY = event.clientY
    }

    function onClick(event: MouseEvent) {
      if (Math.hypot(event.clientX - downX, event.clientY - downY) > 4) return
      const model = modelRef.current
      if (!model) return

      const rect = renderer.domElement.getBoundingClientRect()
      pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1
      pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1
      raycaster.setFromCamera(pointer, camera)

      const hit = raycaster.intersectObject(model.object, true)[0]
      const expressId = hit?.object.userData.expressID as number | undefined
      const oid = expressId === undefined ? undefined : model.oidByExpressId.get(expressId)
      if (oid) {
        setPickedOid(oid)
        onPickOid?.(oid)
      }
    }

    const canvas = renderer.domElement
    canvas.addEventListener('pointerdown', onPointerDown)
    canvas.addEventListener('pointerdown', rememberDown)
    canvas.addEventListener('pointermove', onPointerMove)
    canvas.addEventListener('pointerup', onPointerUp)
    canvas.addEventListener('wheel', onWheel, { passive: false })
    canvas.addEventListener('contextmenu', onContextMenu)
    canvas.addEventListener('click', onClick)

    function resize() {
      const { clientWidth, clientHeight } = mount!
      if (!clientWidth || !clientHeight) return
      renderer.setSize(clientWidth, clientHeight, false)
      camera.aspect = clientWidth / clientHeight
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(mount)
    resize()

    let frame = 0
    function animate() {
      frame = requestAnimationFrame(animate)
      renderer.render(scene, camera)
    }
    animate()

    // Zooma in på en markerad bit. Utan detta blir en 255 mm-regel några pixlar stor i en
    // 15 m byggnad — tekniskt korrekt highlight, men omöjlig att se på en projektor.
    focusRef.current = (box: THREE.Box3) => {
      box.getCenter(target)
      const extent = Math.max(...box.getSize(new THREE.Vector3()).toArray())
      // Backa undan tillräckligt för att biten ska fylla vyn, men behåll lite omgivning
      // så man ser VAR i stommen den sitter.
      spherical.radius = Math.max(extent * 3.5, modelExtent / 25)
      applyCamera()
    }

    // Ett enda highlight-material för hela sessionen -- skapas inte om per markering.
    const highlightMaterial = new THREE.MeshLambertMaterial({ color: HIGHLIGHT_COLOR })

    // --- Ladda modellen (en gång) --------------------------------------------------------
    const abort = new AbortController()
    loadIfcModel(IFC_URL, setProgress, abort.signal)
      .then((model) => {
        if (abort.signal.aborted) {
          model.dispose()
          return
        }
        modelRef.current = model
        materialsRef.current = { base: model.material, highlight: highlightMaterial }
        scene.add(model.object)

        const size = model.boundingBox.getSize(new THREE.Vector3())
        model.boundingBox.getCenter(target)

        // Skala kamera och klippzon efter modellens faktiska storlek i stället för att anta
        // en enhet — då fungerar vyn oavsett om geometrin kommer i meter eller millimeter.
        const extent = Math.max(size.x, size.y, size.z) || 1
        modelExtent = extent
        spherical.radius = extent * 1.6
        camera.near = extent / 1000
        camera.far = extent * 100
        camera.updateProjectionMatrix()
        zoomLimits.min = extent / 50
        zoomLimits.max = extent * 10
        applyCamera()
        setReady(true)
      })
      .catch((err: unknown) => {
        if (abort.signal.aborted) return
        setError(err instanceof Error ? err.message : String(err))
      })

    return () => {
      abort.abort()
      cancelAnimationFrame(frame)
      observer.disconnect()
      canvas.removeEventListener('pointerdown', onPointerDown)
      canvas.removeEventListener('pointerdown', rememberDown)
      canvas.removeEventListener('pointermove', onPointerMove)
      canvas.removeEventListener('pointerup', onPointerUp)
      canvas.removeEventListener('wheel', onWheel)
      canvas.removeEventListener('contextmenu', onContextMenu)
      canvas.removeEventListener('click', onClick)
      modelRef.current?.dispose()
      modelRef.current = null
      materialsRef.current = null
      focusRef.current = null
      highlightRef.current = []
      highlightMaterial.dispose()
      // Nollställ så highlight-effekten kör igång igen när modellen laddats om (StrictMode
      // monterar av/på i dev; utan detta fastnar `ready` på true och effekten hoppas över).
      setReady(false)
      renderer.dispose()
      mount!.removeChild(canvas)
    }
    // Monteras en gång: modellen är 18 MB och laddas aldrig om (docs/prd.md §7).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // --- Highlight: byt material på valt oid ----------------------------------------------
  useEffect(() => {
    const model = modelRef.current
    const materials = materialsRef.current
    if (!model || !materials || !ready) return

    // Alla meshar delar basmaterialet, så highlight sker genom att byta MATERIAL på de valda
    // mesharna (inte genom att färga om ett delat material -- det skulle färga hela modellen).
    for (const mesh of highlightRef.current) {
      mesh.material = materials.base
    }
    highlightRef.current = []

    const expressId = selectedOid === null ? undefined : model.expressIdByOid.get(selectedOid)
    const meshes = expressId === undefined ? [] : model.meshesByExpressId.get(expressId) ?? []

    // Tona ner resten bara när något faktiskt är markerat och hittat i modellen.
    const dimmed = meshes.length > 0
    materials.base.transparent = dimmed
    materials.base.opacity = dimmed ? DIMMED_OPACITY : 1
    materials.base.depthWrite = !dimmed
    materials.base.needsUpdate = true

    if (!dimmed) return

    for (const mesh of meshes) {
      mesh.material = materials.highlight
    }
    highlightRef.current = meshes

    // Zooma in på den valda biten så den syns, inte bara rikta kameran mot den.
    const box = new THREE.Box3()
    for (const mesh of meshes) box.expandByObject(mesh)
    if (!box.isEmpty()) focusRef.current?.(box)
  }, [selectedOid, ready])

  const known = selectedOid !== null && (modelRef.current?.expressIdByOid.has(selectedOid) ?? false)

  return (
    <section className="viewer">
      <div className="viewer-header">
        <h2>3D-vy — 772_H811_new.ifc</h2>
        <p className="viewer-status">
          {error ? (
            <span role="alert">Kunde inte ladda 3D-modellen: {error}</span>
          ) : !ready ? (
            <>
              {progress.message}
              {progress.ratio !== null && ` ${Math.round(progress.ratio * 100)}%`}
            </>
          ) : selectedOid === null ? (
            <>
              {modelRef.current?.expressIdByOid.size ?? 0} spårbara element. Klicka en kapbit i
              tabellen — eller ett element i modellen.
            </>
          ) : known ? (
            <>
              Markerad: OID <strong>{selectedOid}</strong>
            </>
          ) : (
            <>OID {selectedOid} saknar geometri i modellen (FRAMEPIECE/IFCBEAM-begränsning).</>
          )}
        </p>
      </div>

      <div ref={mountRef} className="viewer-canvas" />

      <p className="viewer-hint">
        Vänster drag: rotera · Hjul: zoom · Höger/Shift-drag: panorera
        {pickedOid && <> · Senast klickad i 3D: OID {pickedOid}</>}
      </p>
    </section>
  )
}
