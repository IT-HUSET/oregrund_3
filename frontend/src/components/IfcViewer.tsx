import { useEffect, useRef, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { getBom } from '../api/client'
import { useFetch } from '../api/useFetch'
import { mm } from '../format'
import { type IfcModel, loadIfcModel } from '../ifc/loadIfcModel'

const MODEL_URL = '/772_H811_new.ifc'
const HIGHLIGHT_COLOR = 0xff6a00

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
}

/**
 * Inkrement 4 (docs/plan.md #4, docs/adr.md ADR-3): 3D-vy av 772_H811_new.ifc med
 * dubbelriktad spårbarhet mot materiallistan via OID↔Tag.
 */
export function IfcViewer({ selectedOid, onPickOid }: IfcViewerProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  const modelRef = useRef<IfcModel | null>(null)
  const focusRef = useRef<((expressId: number) => void) | null>(null)
  const [status, setStatus] = useState('Startar 3D-vy...')
  const [error, setError] = useState<string | null>(null)

  const { data: bom } = useFetch(getBom)
  const piece = bom?.items.find((item) => item.oid === selectedOid)

  // Senaste onPickOid utan att bygga om scenen när föräldern renderar om.
  const onPickRef = useRef(onPickOid)
  useEffect(() => {
    onPickRef.current = onPickOid
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
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(window.devicePixelRatio)
    mount.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true

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

    /** Flytta kameran så elementet syns -- annars vet ingen vad som lyste upp. */
    const focus = (expressId: number) => {
      const meshes = modelRef.current?.meshesByExpressId.get(expressId)
      if (!meshes?.length) return

      const box = new THREE.Box3()
      for (const mesh of meshes) box.expandByObject(mesh)
      const center = box.getCenter(new THREE.Vector3())
      const distance = Math.max(box.getSize(new THREE.Vector3()).length() * 2.5, 3)

      controls.target.copy(center)
      camera.position.copy(center).add(new THREE.Vector3(1, 1, 1).setLength(distance))
    }
    focusRef.current = focus

    const raycaster = new THREE.Raycaster()
    const onClick = (event: MouseEvent) => {
      const model = modelRef.current
      if (!model) return

      const rect = renderer.domElement.getBoundingClientRect()
      const pointer = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      )
      raycaster.setFromCamera(pointer, camera)

      for (const hit of raycaster.intersectObjects(model.pickable, false)) {
        const tag = model.tagByExpressId.get(hit.object.userData.expressId as number)
        // Plattor och skivor saknar Tag och är därför inte spårbara (docs/adr.md ADR-3).
        if (tag) {
          onPickRef.current?.(tag)
          return
        }
      }
    }
    renderer.domElement.addEventListener('click', onClick)

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
      renderer.domElement.removeEventListener('click', onClick)
      controls.dispose()
      renderer.dispose()
      mount.removeChild(renderer.domElement)
      // model.dispose() körs inte: modellen är delad mellan mounts (se modelPromise).
    }
  }, [])

  // Highlight följer selectedOid, oavsett om valet kom från tabellen eller från 3D-vyn.
  useEffect(() => {
    const model = modelRef.current
    if (!model || !selectedOid) return

    const expressId = model.expressIdByTag.get(selectedOid)
    if (expressId === undefined) return

    const restore = highlight(model, expressId)
    focusRef.current?.(expressId)
    return restore
  }, [selectedOid, status])

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
        rad i materiallistan — plattor och skivor saknar OID och är inte spårbara.
      </p>
    </section>
  )
}

/** Byter material på elementets meshar och returnerar en funktion som ställer tillbaka dem. */
function highlight(model: IfcModel, expressId: number): () => void {
  const meshes = model.meshesByExpressId.get(expressId) ?? []
  const original = meshes.map((mesh) => mesh.material as THREE.Material)
  // depthTest av: regeln sitter oftast inuti väggen, bakom beklädnaden. Utan detta highlightas
  // rätt element men är dolt -- och då bevisar vyn ingenting för den som tittar.
  const material = new THREE.MeshBasicMaterial({
    color: HIGHLIGHT_COLOR,
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
