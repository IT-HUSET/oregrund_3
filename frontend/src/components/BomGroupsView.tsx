import { useState } from 'react'
import { getBomGroups } from '../api/client'
import { useFetch } from '../api/useFetch'
import { formatMeters, formatMm } from '../format'

interface BomGroupsViewProps {
  onSelectOid?: (oid: string) => void
  selectedOid: string | null
}

/**
 * Inkrement 2 (docs/plan.md #2): grupperad vy över GET /api/bom/groups.
 *
 * Kontrollen i planen: expandera gruppen 45x182 C24 och se handelslängderna listade.
 */
export function BomGroupsView({ onSelectOid, selectedOid }: BomGroupsViewProps) {
  const { data, error, loading } = useFetch(getBomGroups)
  const [expanded, setExpanded] = useState<string | null>(null)

  if (loading) return <p>Grupperar och matchar handelslängder...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/bom/groups: {error}</p>
  if (!data) return null

  const totalPieces = data.groups.reduce((sum, g) => sum + g.piece_count, 0)

  return (
    <section>
      <div className="section-head">
        <h2>Artikelmatchning</h2>
        <p className="lede">
          {totalPieces} bitar i {data.groups.length} grupper (tvärsnitt × klass), matchade mot
          Svenskt Träs standardlängder ur <code>svensktra_standardlangder_mm.csv</code>.
        </p>
      </div>

      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Tvärsnitt</th>
              <th>Klass</th>
              <th className="num">Bitar</th>
              <th className="num">Total längd (m)</th>
              <th className="num">Längst bit (mm)</th>
              <th>Handelslängder (mm)</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {data.groups.map((group) => {
              const key = `${group.code}-${group.mat_code}`
              const isOpen = expanded === key
              const longest = Math.max(...group.pieces.map((p) => p.length_mm))
              // Undantagsregeln (data/dataspec.md §5) bor i backend — vi speglar bara flaggan.
              const excluded = group.excluded_reason
              const overLength = group.pieces.filter(
                (p) => p.length_mm > group.available_trade_lengths_mm.at(-1)!,
              ).length

              return [
                <tr key={key} className={isOpen ? 'selected' : undefined}>
                  <td>
                    <strong>{group.code}</strong>
                    {excluded && (
                      <span className="tag tag-muted" title={excluded}>ej kapoptimerad</span>
                    )}
                  </td>
                  <td>{group.mat_code}</td>
                  <td className="num">{group.piece_count}</td>
                  <td className="num">{formatMeters(group.total_length_mm)}</td>
                  <td className="num">
                    {formatMm(longest)}
                    {overLength > 0 && (
                      <span className="tag tag-splice" title={`${overLength} bitar måste skarvas`}>
                        {overLength} skarv
                      </span>
                    )}
                  </td>
                  <td className="lengths">
                    {group.available_trade_lengths_mm[0]}–
                    {group.available_trade_lengths_mm.at(-1)} ({group.available_trade_lengths_mm.length} st)
                  </td>
                  <td>
                    <button type="button" onClick={() => setExpanded(isOpen ? null : key)}>
                      {isOpen ? 'Dölj' : 'Expandera'}
                    </button>
                  </td>
                </tr>,
                isOpen && (
                  <tr key={`${key}-detail`} className="detail-row">
                    <td colSpan={7}>
                      <div className="detail">
                        <p>
                          <strong>Handelslängder (mm):</strong>{' '}
                          {group.available_trade_lengths_mm.join(', ')}
                        </p>
                        {excluded && <p className="note">{excluded}</p>}
                        <p>
                          <strong>Kapbitar ({group.piece_count}):</strong> klicka för 3D
                        </p>
                        <div className="chips">
                          {group.pieces.map((piece) => (
                            <button
                              key={piece.oid}
                              type="button"
                              className={piece.oid === selectedOid ? 'chip chip-selected' : 'chip'}
                              onClick={() => onSelectOid?.(piece.oid)}
                            >
                              {piece.oid} · {formatMm(piece.length_mm)} mm
                            </button>
                          ))}
                        </div>
                      </div>
                    </td>
                  </tr>
                ),
              ]
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
