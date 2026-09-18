import * as THREE from 'three'
import { IFCBEAM, IFCCOLUMN, IfcAPI, type FlatMesh, type PlacedGeometry } from 'web-ifc'

/**
 * Laddar 772_H811_new.ifc i webbläsaren och bygger en three.js-scen plus OID-mappningarna
 * (docs/adr.md ADR-3). Backend rör aldrig .ifc-filen -- all parsning sker här, i WASM.
 *
 * En mesh per PlacedGeometry, med expressID i userData: det gör picking i 3D-vyn till en rak
 * raycaster-träff. Modellen är 2 512 element, så instansiering behövs inte (ADR-3).
 */

/** Typerna vars Tag matchar FRAMEPIECE OID. Båda behövs: 422 + 309 = alla 731 (docs/prd.md §0). */
const TRACEABLE_TYPES = [IFCBEAM, IFCCOLUMN]

/**
 * Opacitet för element utan Tag (t.ex. plattor/skivor). Backend tar in ALLA FRAMEPIECE utan
 * filtrering (backend/app/services/xml_parser.py, backend/app/services/article_matching.py) och
 * täckningen Tag↔OID är 100 % (docs/prd.md §0) -- så "har Tag" == "finns i inköpsunderlaget".
 */
const GHOST_OPACITY = 0.12

export interface IfcModel {
  root: THREE.Group
  /** Alla meshar som går att klicka på, för raycasting. */
  pickable: THREE.Mesh[]
  meshesByExpressId: Map<number, THREE.Mesh[]>
  /** oid (== IFC Tag) -> expressID. Slås upp när en rad i tabellen klickas. */
  expressIdByTag: Map<string, number>
  /** expressID -> oid. Slås upp när ett element klickas i 3D-vyn. */
  tagByExpressId: Map<number, string>
  dispose: () => void
}

export async function loadIfcModel(
  url: string,
  onProgress: (message: string) => void,
): Promise<IfcModel> {
  const api = new IfcAPI()
  api.SetWasmPath('/', true)
  await api.Init()

  onProgress('Hämtar modellen...')
  const response = await fetch(url)
  if (!response.ok) throw new Error(`${url} svarade ${response.status}`)
  const bytes = new Uint8Array(await response.arrayBuffer())

  onProgress('Parsar IFC...')
  const modelId = api.OpenModel(bytes)

  onProgress('Kopplar OID mot Tag...')
  const { expressIdByTag, tagByExpressId } = readTags(api, modelId)

  const root = new THREE.Group()
  const pickable: THREE.Mesh[] = []
  const meshesByExpressId = new Map<number, THREE.Mesh[]>()
  const materials = new Map<string, THREE.MeshLambertMaterial>()

  onProgress('Bygger geometri...')
  api.StreamAllMeshes(modelId, (flatMesh: FlatMesh) => {
    const expressId = flatMesh.expressID
    // Osynliggör inte helt -- ett tonat spöke visar fortfarande att elementet finns, bara att
    // det inte ingår i inköpsunderlaget (plattor/skivor saknar Tag, docs/adr.md ADR-3).
    const traceable = tagByExpressId.has(expressId)
    for (let i = 0; i < flatMesh.geometries.size(); i++) {
      const mesh = buildMesh(api, modelId, flatMesh.geometries.get(i), materials, traceable)
      mesh.userData.expressId = expressId
      root.add(mesh)
      pickable.push(mesh)

      const existing = meshesByExpressId.get(expressId)
      if (existing) existing.push(mesh)
      else meshesByExpressId.set(expressId, [mesh])
    }
  })

  // 772_H811_new.ifc är redan Y-upp i sina egna världskoordinater (uppmätt: Y-extent ~2.9 m,
  // matchar rumshöjd). Ingen Z-upp-rotation ska appliceras -- annars hamnar huset på långsidan.
  centerOnOrigin(root)

  api.CloseModel(modelId)

  return {
    root,
    pickable,
    meshesByExpressId,
    expressIdByTag,
    tagByExpressId,
    dispose: () => {
      for (const mesh of pickable) mesh.geometry.dispose()
      for (const material of materials.values()) material.dispose()
    },
  }
}

function buildMesh(
  api: IfcAPI,
  modelId: number,
  placed: PlacedGeometry,
  materials: Map<string, THREE.MeshLambertMaterial>,
  traceable: boolean,
): THREE.Mesh {
  const geometry = api.GetGeometry(modelId, placed.geometryExpressID)
  // Interleavat: 6 floats per vertex, position följt av normal.
  const vertices = api.GetVertexArray(geometry.GetVertexData(), geometry.GetVertexDataSize())
  const indices = api.GetIndexArray(geometry.GetIndexData(), geometry.GetIndexDataSize())

  const positions = new Float32Array(vertices.length / 2)
  const normals = new Float32Array(vertices.length / 2)
  for (let i = 0; i < vertices.length / 6; i++) {
    positions[i * 3] = vertices[i * 6]
    positions[i * 3 + 1] = vertices[i * 6 + 1]
    positions[i * 3 + 2] = vertices[i * 6 + 2]
    normals[i * 3] = vertices[i * 6 + 3]
    normals[i * 3 + 1] = vertices[i * 6 + 4]
    normals[i * 3 + 2] = vertices[i * 6 + 5]
  }
  geometry.delete()

  const bufferGeometry = new THREE.BufferGeometry()
  bufferGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
  bufferGeometry.setAttribute('normal', new THREE.BufferAttribute(normals, 3))
  bufferGeometry.setIndex(new THREE.BufferAttribute(new Uint32Array(indices), 1))

  const mesh = new THREE.Mesh(bufferGeometry, materialFor(placed.color, materials, traceable))
  // applyMatrix4, inte matrix.fromArray: det senare kräver att matrixWorldNeedsUpdate sätts för
  // hand när matrixAutoUpdate är av, annars ritar renderloopen allt med identitetsmatris.
  mesh.applyMatrix4(new THREE.Matrix4().fromArray(placed.flatTransformation))
  return mesh
}

function materialFor(
  color: { x: number; y: number; z: number; w: number },
  materials: Map<string, THREE.MeshLambertMaterial>,
  traceable: boolean,
): THREE.MeshLambertMaterial {
  // traceable i nyckeln: samma färg får annars samma cachade material oavsett spårbarhet, och
  // då skulle en spårbar balk bli lika genomskinlig som en icke-spårbar platta med samma kulör.
  const key = `${color.x},${color.y},${color.z},${color.w},${traceable}`
  const cached = materials.get(key)
  if (cached) return cached

  const material = new THREE.MeshLambertMaterial({
    color: new THREE.Color(color.x, color.y, color.z),
    side: THREE.DoubleSide,
    transparent: traceable ? color.w < 1 : true,
    opacity: traceable ? color.w : GHOST_OPACITY,
    // Skriv inte djup för spökade element -- annars sorteras andra genomskinliga ytor bakom
    // dem fel (t.ex. highlightmaterialet, som redan kör med depthTest av av samma anledning).
    depthWrite: traceable,
  })
  materials.set(key, material)
  return material
}

function readTags(api: IfcAPI, modelId: number) {
  const expressIdByTag = new Map<string, number>()
  const tagByExpressId = new Map<number, string>()

  for (const type of TRACEABLE_TYPES) {
    const ids = api.GetLineIDsWithType(modelId, type)
    for (let i = 0; i < ids.size(); i++) {
      const expressId = ids.get(i)
      const tag: string | undefined = api.GetLine(modelId, expressId)?.Tag?.value
      if (!tag) continue
      expressIdByTag.set(tag, expressId)
      tagByExpressId.set(expressId, tag)
    }
  }

  return { expressIdByTag, tagByExpressId }
}

/** Modellen ligger i projektkoordinater långt från origo -- flytta in den så kameran hittar den. */
function centerOnOrigin(root: THREE.Group): void {
  const box = new THREE.Box3().setFromObject(root)
  const center = box.getCenter(new THREE.Vector3())
  root.position.sub(center)
}
