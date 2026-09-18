/**
 * Verifierar OID <-> Tag-kopplingen mot den riktiga IFC-filen (docs/plan.md #4, kontroll:
 * "givet känt OID 589830, mappningen hittar rätt expressID i den laddade IFC-modellen").
 *
 * Körs i Node med web-ifcs node-build, men gör exakt samma anrop som src/ifc/loadIfcModel.ts
 * gör i webbläsaren — så den fångar om kopplingen slutar fungera utan att någon startar appen.
 *
 * Kör: npm run verify:ifc   (backend måste vara igång på :8000 för BOM-jämförelsen)
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { IfcAPI, IFCBEAM, IFCCOLUMN } from 'web-ifc'

const IFC_PATH = resolve(import.meta.dirname, '../../data/772_H811_new.ifc')
const TAG_ARGUMENT_INDEX = 7
const KNOWN_OID = '589830'
const KNOWN_NAME_FRAGMENT = 'FD5 Opening header beam'

const failures = []
function check(label, condition, detail = '') {
  console.log(`${condition ? 'OK  ' : 'FEL '} ${label}${detail ? ` — ${detail}` : ''}`)
  if (!condition) failures.push(label)
}

const api = new IfcAPI()
await api.Init()
const modelId = api.OpenModel(new Uint8Array(readFileSync(IFC_PATH)), {
  COORDINATE_TO_ORIGIN: true,
})

const expressIdByOid = new Map()
const nameByOid = new Map()

for (const type of [IFCBEAM, IFCCOLUMN]) {
  const ids = api.GetLineIDsWithType(modelId, type)
  for (let i = 0; i < ids.size(); i++) {
    const expressId = ids.get(i)
    const line = api.GetLine(modelId, expressId)
    let tag = line?.Tag?.value
    if (typeof tag !== 'string' || !tag) {
      const raw = api.GetRawLineData(modelId, expressId)
      const argument = raw?.arguments?.[TAG_ARGUMENT_INDEX]
      tag = argument && typeof argument === 'object' ? argument.value : argument
    }
    if (typeof tag === 'string' && tag) {
      expressIdByOid.set(tag, expressId)
      nameByOid.set(tag, line?.Name?.value ?? '')
    }
  }
}

check('IFC innehåller spårbara element', expressIdByOid.size === 731, `${expressIdByOid.size} st`)

const expressId = expressIdByOid.get(KNOWN_OID)
check(`OID ${KNOWN_OID} mappas till ett expressID`, expressId !== undefined, `expressID ${expressId}`)
check(
  `OID ${KNOWN_OID} är rätt element`,
  (nameByOid.get(KNOWN_OID) ?? '').includes(KNOWN_NAME_FRAGMENT),
  nameByOid.get(KNOWN_OID),
)

if (expressId !== undefined) {
  const mesh = api.GetFlatMesh(modelId, expressId)
  check(`OID ${KNOWN_OID} har geometri att highlighta`, mesh.geometries.size() > 0)
}

// Jämför mot backend om den är igång — annars hoppas steget över, inte fejkas.
try {
  const bom = await (await fetch('http://localhost:8000/api/bom')).json()
  const missing = bom.items.filter((item) => !expressIdByOid.has(item.oid))
  check(
    'alla BOM-rader har ett 3D-element',
    missing.length === 0,
    `${bom.count} rader, ${missing.length} utan geometri`,
  )
} catch {
  console.log('HOPP backend svarar inte på :8000 — BOM-jämförelsen hoppades över')
}

api.CloseModel(modelId)

if (failures.length) {
  console.error(`\n${failures.length} kontroll(er) misslyckades.`)
  process.exit(1)
}
console.log('\nAlla kontroller gick igenom.')
