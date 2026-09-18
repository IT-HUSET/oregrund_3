/**
 * Laddar 772_H811_new.ifc i webbläsaren och bygger en three.js-scen + en OID-uppslagstabell.
 *
 * Inkrement 4 (docs/plan.md #4, docs/adr.md ADR-3). All IFC-hantering är klientkod: backend
 * öppnar aldrig .ifc-filen och skickar bara `oid` i sina API-svar. Kopplingen är verifierad i
 * data/dataspec.md §2: IFC-objektets `Tag` är exakt samma sträng som FRAMEPIECE `OID`.
 *
 * Spårbarheten begränsas till IfcBeam/IfcColumn (docs/prd.md §7) — det är där OID<->Tag är
 * verifierad 731/731, inte för plattor/övriga entiteter.
 */

import { IFCBEAM, IFCCOLUMN, IfcAPI, type FlatMesh, type PlacedGeometry } from 'web-ifc'
import * as THREE from 'three'

/** Entiteter med verifierad OID<->Tag-koppling (data/dataspec.md §4.1). */
const TRACEABLE_TYPES = [IFCBEAM, IFCCOLUMN]

/** `Tag` ligger på 8:e positionen i IFCBEAM(...)/IFCCOLUMN(...) (data/dataspec.md §2). */
const TAG_ARGUMENT_INDEX = 7

export interface IfcModel {
  /** Alla virkesbitar som en enda mesh-grupp, redo att läggas i en scen. */
  object: THREE.Group
  /** oid (== IFC Tag) -> expressID. Nyckeln hela 3D-spårbarheten vilar på. */
  expressIdByOid: Map<string, number>
  /** expressID -> oid, för klick i 3D-vyn tillbaka till tabellen. */
  oidByExpressId: Map<number, string>
  /** expressID -> de meshar som ritar elementet, för highlight. */
  meshesByExpressId: Map<number, THREE.Mesh[]>
  /** Delat basmaterial för alla virkesbitar — highlight byter material, inte färg på detta. */
  material: THREE.MeshLambertMaterial
  /** Modellens mittpunkt och storlek, för kamerainställning. */
  boundingBox: THREE.Box3
  dispose: () => void
}

export interface LoadProgress {
  phase: 'downloading' | 'parsing' | 'building' | 'done'
  /** 0-1 när det går att veta, annars null (web-ifc rapporterar inte parsningsprogress). */
  ratio: number | null
  message: string
}

function readTag(api: IfcAPI, modelId: number, expressId: number): string | null {
  // GetLine ger typade argument; Tag är ett IfcIdentifier-värde med .value.
  const line = api.GetLine(modelId, expressId) as { Tag?: { value?: unknown } } | null
  const raw = line?.Tag?.value
  if (typeof raw === 'string' && raw.length > 0) return raw
  if (typeof raw === 'number') return String(raw)
  return null
}

function readTagFromRawLine(api: IfcAPI, modelId: number, expressId: number): string | null {
  // Fallback: läs argumentlistan rått om det typade objektet saknar Tag.
  const raw = api.GetRawLineData(modelId, expressId) as { arguments?: unknown[] } | null
  const argument = raw?.arguments?.[TAG_ARGUMENT_INDEX] as { value?: unknown } | undefined
  const value = argument && typeof argument === 'object' ? argument.value : argument
  return typeof value === 'string' && value.length > 0 ? value : null
}

function geometryToMesh(
  api: IfcAPI,
  modelId: number,
  placed: PlacedGeometry,
  material: THREE.Material,
): THREE.Mesh {
  const geometry = api.GetGeometry(modelId, placed.geometryExpressID)
  const vertices = api.GetVertexArray(geometry.GetVertexData(), geometry.GetVertexDataSize())
  const indices = api.GetIndexArray(geometry.GetIndexData(), geometry.GetIndexDataSize())

  // web-ifc packar position+normal omväxlande i samma buffert (6 floats per vertex).
  const positions = new Float32Array(vertices.length / 2)
  const normals = new Float32Array(vertices.length / 2)
  for (let i = 0; i < vertices.length; i += 6) {
    const target = i / 2
    positions[target] = vertices[i]
    positions[target + 1] = vertices[i + 1]
    positions[target + 2] = vertices[i + 2]
    normals[target] = vertices[i + 3]
    normals[target + 1] = vertices[i + 4]
    normals[target + 2] = vertices[i + 5]
  }

  const bufferGeometry = new THREE.BufferGeometry()
  bufferGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  bufferGeometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  bufferGeometry.setIndex(new THREE.BufferAttribute(new Uint32Array(indices), 1))

  const mesh = new THREE.Mesh(bufferGeometry, material)
  mesh.matrix.fromArray(placed.flatTransformation)
  mesh.matrixAutoUpdate = false
  geometry.delete()
  return mesh
}

/**
 * Hämtar, parsar och bygger modellen. `onProgress` anropas löpande så UI:t kan visa status —
 * filen är 18 MB och ska laddas tidigt/i bakgrunden, inte live på scen (docs/prd.md §7).
 */
export async function loadIfcModel(
  url: string,
  onProgress?: (progress: LoadProgress) => void,
  signal?: AbortSignal,
): Promise<IfcModel> {
  onProgress?.({ phase: 'downloading', ratio: 0, message: 'Hämtar 3D-modellen...' })

  const response = await fetch(url, { signal })
  if (!response.ok) {
    throw new Error(`Kunde inte hämta ${url}: ${response.status}`)
  }
  const buffer = new Uint8Array(await response.arrayBuffer())

  onProgress?.({ phase: 'parsing', ratio: null, message: 'Tolkar IFC-filen...' })

  const api = new IfcAPI()
  api.SetWasmPath('/wasm/', true)
  await api.Init()

  const modelId = api.OpenModel(buffer, { COORDINATE_TO_ORIGIN: true })

  // 1. Bygg OID <-> expressID-kartan för spårbara entiteter.
  const expressIdByOid = new Map<string, number>()
  const oidByExpressId = new Map<number, string>()

  for (const type of TRACEABLE_TYPES) {
    const ids = api.GetLineIDsWithType(modelId, type)
    for (let i = 0; i < ids.size(); i++) {
      const expressId = ids.get(i)
      const tag = readTag(api, modelId, expressId) ?? readTagFromRawLine(api, modelId, expressId)
      if (tag === null) continue
      expressIdByOid.set(tag, expressId)
      oidByExpressId.set(expressId, tag)
    }
  }

  // 2. Bygg geometrin, bara för de element vi kan spåra.
  onProgress?.({ phase: 'building', ratio: 0, message: 'Bygger 3D-geometri...' })

  const material = new THREE.MeshLambertMaterial({ color: 0xd8c39a })
  const group = new THREE.Group()
  const meshesByExpressId = new Map<number, THREE.Mesh[]>()

  let processed = 0
  const total = oidByExpressId.size
  api.StreamAllMeshesWithTypes(modelId, TRACEABLE_TYPES, (flatMesh: FlatMesh) => {
    if (!oidByExpressId.has(flatMesh.expressID)) return

    const meshes: THREE.Mesh[] = []
    for (let i = 0; i < flatMesh.geometries.size(); i++) {
      const mesh = geometryToMesh(api, modelId, flatMesh.geometries.get(i), material)
      mesh.userData.expressID = flatMesh.expressID
      group.add(mesh)
      meshes.push(mesh)
    }
    meshesByExpressId.set(flatMesh.expressID, meshes)

    processed += 1
    if (processed % 100 === 0) {
      onProgress?.({
        phase: 'building',
        ratio: total ? processed / total : null,
        message: `Bygger 3D-geometri (${processed}/${total})...`,
      })
    }
  })

  // IFC är Z-upp, three.js är Y-upp.
  group.rotation.x = -Math.PI / 2

  // Matriserna måste räknas ut innan boxen mäts — mesharna har matrixAutoUpdate=false och
  // gruppen roterades nyss, så utan detta mäts boxen på ostransformerad geometri och
  // kameran hamnar tusenfalt för långt bort (blank vy).
  group.updateMatrixWorld(true)
  const boundingBox = new THREE.Box3().setFromObject(group)

  api.CloseModel(modelId)
  onProgress?.({ phase: 'done', ratio: 1, message: `${meshesByExpressId.size} element laddade.` })

  return {
    object: group,
    expressIdByOid,
    oidByExpressId,
    meshesByExpressId,
    material,
    boundingBox,
    dispose() {
      group.traverse((child) => {
        if (child instanceof THREE.Mesh) child.geometry.dispose()
      })
      material.dispose()
    },
  }
}
