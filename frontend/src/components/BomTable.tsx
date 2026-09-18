import { useMemo, useState } from 'react'
import { getBom } from '../api/client'
import { useFetch } from '../api/useFetch'
import type { FramePiece } from '../api/types'

const ALL_CODES = 'Alla'

const mm = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 1 })
const meters = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 0 })

interface BomSummary {
  codes: string[]
  matCodeCount: number
  totalLengthM: number
}

function summarize(items: FramePiece[]): BomSummary {
  const codes = new Set<string>()
  const matCodes = new Set<string>()
  let totalLengthMm = 0

  for (const item of items) {
    codes.add(item.code)
    matCodes.add(item.mat_code)
    totalLengthMm += item.length_mm
  }

  return {
    codes: [...codes].sort(byCrossSection),
    matCodeCount: matCodes.size,
    totalLengthM: totalLengthMm / 1000,
  }
}

/**
 * Sortera dropdownen numeriskt på bredd, sedan höjd ("45x95" före "45x182") i stället för som
 * text. CODE är inte alltid rent "BxH" -- den kan ha prefix ("GL 90x220", "CLS PAR 9.76x95")
 * eller suffix ("45x220_S"), så måtten plockas ut med regex; koder utan mått hamnar sist.
 */
function byCrossSection(a: string, b: string): number {
  const [aWidth, aHeight] = dimensions(a)
  const [bWidth, bHeight] = dimensions(b)
  return aWidth - bWidth || aHeight - bHeight || a.localeCompare(b, 'sv')
}

function dimensions(code: string): [number, number] {
  const match = /(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)/.exec(code)
  return match ? [Number(match[1]), Number(match[2])] : [Infinity, Infinity]
}

/** Inkrement 1 (docs/plan.md #1): tabellvy över GET /api/bom. */
export function BomTable() {
  const { data, error, loading } = useFetch(getBom)
  const [code, setCode] = useState<string>(ALL_CODES)

  const items = data?.items
  const summary = useMemo(() => (items ? summarize(items) : null), [items])
  const rows = useMemo(
    () => (items ?? []).filter((item) => code === ALL_CODES || item.code === code),
    [items, code],
  )

  if (loading) return <p>Läser materialbehov...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/bom: {error}</p>
  if (!data || !summary) return null

  return (
    <section>
      <h2>Materialbehov</h2>
      <p className="summary">
        {mm.format(data.count)} poster · {summary.codes.length} tvärsnitt · {summary.matCodeCount}{' '}
        klasser · {meters.format(summary.totalLengthM)} m totalt
      </p>

      <p className="filter">
        <label htmlFor="code-filter">Tvärsnitt: </label>
        <select id="code-filter" value={code} onChange={(e) => setCode(e.target.value)}>
          <option value={ALL_CODES}>{ALL_CODES}</option>
          {summary.codes.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>{' '}
        <output htmlFor="code-filter">
          {mm.format(rows.length)} av {mm.format(data.count)} rader
        </output>
      </p>

      <table>
        <thead>
          <tr>
            <th>OID</th>
            <th>Tvärsnitt</th>
            <th>Klass</th>
            <th>Längd (mm)</th>
            <th>Modul</th>
            <th>Funktion</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((item) => (
            <tr key={item.oid}>
              <td>{item.oid}</td>
              <td>{item.code}</td>
              <td>{item.mat_code}</td>
              <td className="num">{mm.format(item.length_mm)}</td>
              <td>{item.module_flat ?? item.module_name}</td>
              <td>{item.use}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
