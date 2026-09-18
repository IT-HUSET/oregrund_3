import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { getBom } from '../api/client'
import { useFetch } from '../api/useFetch'
import { mm } from '../format'
import { type IfcModel, loadIfcModel } from '../ifc/loadIfcModel'

const MODEL_URL = '/772_H811_new.ifc'
const SELECT_COLOR = 0xff6a00
const HOVER_COLOR = 0x2f8fff

/**
 * Modellen laddas en gång per sidladdning, inte en gång per mount. React StrictMode monterar
 * effekter dubbelt i dev, och 18 MB IFC ska inte parsas två gånger (docs/prd.md §7).
 */
let modelPromise: Promise<IfcModel> | null = null

function getModel(onProgress: (message: string) => void): Promise<IfcModel> {
  modelPromise ??= loadIfcModel(MODEL_URL, onProgress)
  return modelPromise
}

interface IfcViewerProps {
  /** oid att highlighta (== IFCBEAM/IFCCOLUMN Tag). Sätts av klick i kaplistan. */
  selectedOid: string | null
  /** Klick på ett element i 3D-vyn. Omvända riktningen, docs/prd.md §3.4. */
  onPickOid?: (oid: string) => void
  /** oid att hovra (blå highlight, ingen kamerarörelse). Sätts av hover i kaplistan. */
  hoveredOid?: string | null
  /** Hover över ett element i 3D-vyn. Omvända riktningen, samma princip som onPickOid. */
  onHoverOid?: (oid: string | null) => void
}

/**
 * Inkrement 4 (docs/plan.md #4, docs/adr.md ADR-3): 3D-vy av 772_H811_new.ifc med
 * dubbelriktad spårbarhet mot materiallistan via OID↔Tag.
 */
export function IfcViewer({ selectedOid, onPickOid, hoveredOid, onHoverOid }: IfcViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  const modelRef = useRef<IfcModel | null>(null)
  const [status, setStatus] = useState('Startar 3D-vy...')
  const [error, setError] = useState<string | null>(null)

  const { data: bom } = useFetch(getBom)
  const piece = bom?.items.find((item) => item.oid === selectedOid)

  // Senaste onPickOid/onHoverOid utan att bygga om scenen när föräldern renderar om.
  const onPickRef = useRef(onPickOid)
  const onHoverRef = useRef(onHoverOid)
  useEffect(() => {
    onPickRef.current = onPickOid
    onHoverRef.current = onHoverOid
  })

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0xf4f4f4)
    scene.add(new THREE.AmbientLight(0xffffff, 1.6))
    const sun = new THREE.DirectionalLight(0xffffff, 1.6)
    sun.position.set(1, 2, 1)
    scene.add(sun)

    const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 2000)
    // Fast "upp" == taket pekar alltid uppåt. loadIfcModel roterar IFC:ns Z-upp till Y-upp,
    // så (0,1,0) räcker -- ingen roll ska någonsin appliceras på kameran.
    camera.up.set(0, 1, 0)
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    mount.appendChild(renderer.domElement)

    // Kameran låst till huset: bara azimut (rotation) och polarvinkel (pitch) kring en fast
    // pivot i origo, ingen panorering (som annars skulle flytta pivoten) och ingen roll.
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.enablePan = false
    controls.target.set(0, 0, 0)
    // Undvik polerna (rakt uppifrån/underifrån): där blir azimut singulär och en liten
    // musrörelse kan få huset att verka vändas upp och ner.
    controls.minPolarAngle = 0.05
    controls.maxPolarAngle = Math.PI - 0.05

    const resize = () => {
      const { clientWidth, clientHeight } = mount
      renderer.setSize(clientWidth, clientHeight)
      camera.aspect = clientWidth / clientHeight
      camera.updateProjectionMatrix()
    }
    const observer = new ResizeObserver(resize)
    observer.observe(mount)
    resize()

    let running = true
    const tick = () => {
      if (!running) return
      controls.update()
      renderer.render(scene, camera)
      requestAnimationFrame(tick)
    }
    tick()

    const raycaster = new THREE.Raycaster()
    /** Tag under muspekaren, eller null om inget spårbart element träffas. */
    const pickTag = (event: MouseEvent): string | null => {
      const model = modelRef.current
      if (!model) return null

      const rect = renderer.domElement.getBoundingClientRect()
      const pointer = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      )
      raycaster.setFromCamera(pointer, camera)

      for (const hit of raycaster.intersectObjects(model.pickable, false)) {
        const tag = model.tagByExpressId.get(hit.object.userData.expressId as number)
        // Plattor och skivor saknar Tag och är därför inte spårbara (docs/adr.md ADR-3).
        if (tag) return tag
      }
      return null
    }

    // click triggras så fort mousedown/mouseup landar på samma element (canvasen), oavsett hur
    // långt pekaren rört sig däremellan -- så att avsluta en kameradragning ovanpå ett element
    // annars felaktigt tolkas som ett klick på det. Kräv att pekaren knappt rört sig.
    const CLICK_DRAG_THRESHOLD_PX = 5
    let pointerDownPos: { x: number; y: number } | null = null
    const onPointerDown = (event: PointerEvent) => {
      pointerDownPos = { x: event.clientX, y: event.clientY }
    }
    const onClick = (event: MouseEvent) => {
      if (pointerDownPos) {
        const dx = event.clientX - pointerDownPos.x
        const dy = event.clientY - pointerDownPos.y
        if (dx * dx + dy * dy > CLICK_DRAG_THRESHOLD_PX ** 2) return
      }
      const tag = pickTag(event)
      if (tag) onPickRef.current?.(tag)
    }
    renderer.domElement.addEventListener('pointerdown', onPointerDown)
    renderer.domElement.addEventListener('click', onClick)

    // Hover: samma raycast som klick, men rapporterar bara ändringar (annars triggas
    // onHoverOid -> React-render på varje musrörelse) och rör aldrig kameran.
    let lastHoveredTag: string | null = null
    let hoverPending = false
    const onPointerMove = (event: MouseEvent) => {
      if (hoverPending) return
      hoverPending = true
      requestAnimationFrame(() => {
        hoverPending = false
        const tag = pickTag(event)
        renderer.domElement.style.cursor = tag ? 'pointer' : 'default'
        if (tag !== lastHoveredTag) {
          lastHoveredTag = tag
          onHoverRef.current?.(tag)
        }
      })
    }
    const onPointerLeave = () => {
      lastHoveredTag = null
      renderer.domElement.style.cursor = 'default'
      onHoverRef.current?.(null)
    }
    renderer.domElement.addEventListener('pointermove', onPointerMove)
    renderer.domElement.addEventListener('pointerleave', onPointerLeave)

    getModel(setStatus)
      .then((model) => {
        if (!running) return
        modelRef.current = model
        scene.add(model.root)

        const box = new THREE.Box3().setFromObject(model.root)
        const size = box.getSize(new THREE.Vector3()).length()
        camera.position.set(size * 0.6, size * 0.5, size * 0.6)
        camera.far = size * 10
        camera.updateProjectionMatrix()
        controls.target.set(0, 0, 0)

        setStatus(
          `${mm.format(model.pickable.length)} meshar, ${mm.format(model.tagByExpressId.size)} spårbara element`,
        )
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : String(err))
      })

    return () => {
      running = false
      observer.disconnect()
      renderer.domElement.removeEventListener('pointerdown', onPointerDown)
      renderer.domElement.removeEventListener('click', onClick)
      renderer.domElement.removeEventListener('pointermove', onPointerMove)
      renderer.domElement.removeEventListener('pointerleave', onPointerLeave)
      controls.dispose()
      renderer.dispose()
      mount.removeChild(renderer.domElement)
      // model.dispose() körs inte: modellen är delad mellan mounts (se modelPromise).
    }
  }, [])

  // Val (klick): bara highlight. Kameran är låst till huset (origo) och flyttas aldrig --
  // se OrbitControls-uppsättningen ovan.
  useEffect(() => {
    const model = modelRef.current
    if (!model || !selectedOid) return

    const expressId = model.expressIdByTag.get(selectedOid)
    if (expressId === undefined) return

    return highlight(model, expressId, SELECT_COLOR)
  }, [selectedOid, status])

  // Hover: bara highlight, aldrig kamerarörelse.
  useEffect(() => {
    const model = modelRef.current
    if (!model || !hoveredOid || hoveredOid === selectedOid) return

    const expressId = model.expressIdByTag.get(hoveredOid)
    if (expressId === undefined) return

    return highlight(model, expressId, HOVER_COLOR)
  }, [hoveredOid, selectedOid, status])

  return (
    <section>
      <h2>3D-vy</h2>
      <p>
        {error ? (
          <span role="alert">Kunde inte ladda {MODEL_URL}: {error}</span>
        ) : (
          status
        )}
        {piece && (
          <>
            {' — vald: '}
            <strong>{piece.oid}</strong> {piece.code} {piece.mat_code},{' '}
            {mm.format(piece.length_mm)} mm, {piece.module_flat ?? piece.module_name},{' '}
            {piece.use}
          </>
        )}
        {selectedOid && !piece && ` — vald: ${selectedOid}`}
      </p>
      <div ref={mountRef} className="viewer" />
      <p className="hint">
        Dra för att rotera, scrolla för att zooma. Klicka på en regel eller stolpe för att se dess
        rad i materiallistan — plattor och skivor saknar OID, är inte spårbara och visas nedtonade.
      </p>
    </section>
  )
}

/** Byter material på elementets meshar och returnerar en funktion som ställer tillbaka dem. */
function highlight(model: IfcModel, expressId: number, color: number): () => void {
  const meshes = model.meshesByExpressId.get(expressId) ?? []
  const original = meshes.map((mesh) => mesh.material as THREE.Material)
  // depthTest av: regeln sitter oftast inuti väggen, bakom beklädnaden. Utan detta highlightas
  // rätt element men är dolt -- och då bevisar vyn ingenting för den som tittar.
  const material = new THREE.MeshBasicMaterial({
    color,
    depthTest: false,
    transparent: true,
  })

  for (const mesh of meshes) {
    mesh.material = material
    mesh.renderOrder = 1
  }

  return () => {
    meshes.forEach((mesh, index) => {
      mesh.material = original[index]
      mesh.renderOrder = 0
    })
    material.dispose()
  }
}
