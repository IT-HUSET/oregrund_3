import { useMemo, useState } from 'react'
import { getBom } from '../api/client'
import { useFetch } from '../api/useFetch'
import { formatMm } from '../format'

interface BomTableProps {
  /** Klick på en rad highlightar biten i 3D-vyn (docs/plan.md #4). */
  onSelectOid?: (oid: string) => void
  selectedOid: string | null
}

/**
 * Inkrement 1 (docs/plan.md #1): tabellvy över GET /api/bom.
 *
 * Kontrollen i planen är "filtrera på tvärsnitt 45x182 -> 72 träffar", så filtret är en riktig
 * kontroll i UI:t, inte något man får göra i webbläsarkonsolen.
 */
export function BomTable({ onSelectOid, selectedOid }: BomTableProps) {
  const { data, error, loading } = useFetch(getBom)
  const [codeFilter, setCodeFilter] = useState('')
  const [matFilter, setMatFilter] = useState('')
  const [search, setSearch] = useState('')

  const codes = useMemo(
    () => [...new Set(data?.items.map((i) => i.code) ?? [])].sort(),
    [data],
  )
  const matCodes = useMemo(
    () => [...new Set(data?.items.map((i) => i.mat_code) ?? [])].sort(),
    [data],
  )

  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return (data?.items ?? []).filter((item) => {
      if (codeFilter && item.code !== codeFilter) return false
      if (matFilter && item.mat_code !== matFilter) return false
      if (!needle) return true
      return [item.oid, item.item_id, item.module_flat, item.module_name, item.use]
        .some((value) => value?.toLowerCase().includes(needle))
    })
  }, [data, codeFilter, matFilter, search])

  const totalLength = useMemo(
    () => rows.reduce((sum, item) => sum + item.length_mm, 0),
    [rows],
  )

  if (loading) return <p>Läser materialbehov...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/bom: {error}</p>
  if (!data) return null

  return (
    <section>
      <div className="section-head">
        <h2>Materialbehov</h2>
        <p className="lede">
          {data.count} virkesbitar inlästa ur <code>components.xml</code> — ingen manuell
          mängdning.
        </p>
      </div>

      <div className="toolbar">
        <label>
          Tvärsnitt
          <select value={codeFilter} onChange={(e) => setCodeFilter(e.target.value)}>
            <option value="">Alla</option>
            {codes.map((code) => (
              <option key={code} value={code}>{code}</option>
            ))}
          </select>
        </label>
        <label>
          Klass
          <select value={matFilter} onChange={(e) => setMatFilter(e.target.value)}>
            <option value="">Alla</option>
            {matCodes.map((mat) => (
              <option key={mat} value={mat}>{mat}</option>
            ))}
          </select>
        </label>
        <label>
          Sök
          <input
            type="search"
            value={search}
            placeholder="OID, position, modul, funktion"
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <span className="count-badge">
          {rows.length} av {data.count} rader · {formatMm(totalLength, 0)} mm totalt
        </span>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>OID</th>
              <th>Position</th>
              <th>Tvärsnitt</th>
              <th>Klass</th>
              <th className="num">Längd (mm)</th>
              <th>Modul</th>
              <th>Rum</th>
              <th>Funktion</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr
                key={item.oid}
                onClick={() => onSelectOid?.(item.oid)}
                className={item.oid === selectedOid ? 'selected clickable' : 'clickable'}
                title="Visa i 3D-vyn"
              >
                <td>{item.oid}</td>
                <td>{item.item_id ?? '—'}</td>
                <td>{item.code}</td>
                <td>{item.mat_code}</td>
                <td className="num">
                  {formatMm(item.length_mm)}
                  {item.length_mm > 5400 && <span className="tag tag-splice" title="Längre än längsta handelslängden (5400 mm) — måste skarvas">skarv</span>}
                </td>
                <td>{item.module_name ?? '—'}</td>
                <td>{item.module_flat ?? '—'}</td>
                <td>{item.use}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="empty">Inga rader matchar filtret.</p>}
      </div>
    </section>
  )
}
