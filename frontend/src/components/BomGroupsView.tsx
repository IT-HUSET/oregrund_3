import { useMemo } from 'react'
import { getBomGroups } from '../api/client'
import { useFetch } from '../api/useFetch'
import type { BomGroup } from '../api/types'
import { meters, mm } from '../format'

/**
 * Inkrement 2 (docs/plan.md #2): grupperad vy över GET /api/bom/groups.
 *
 * Grupperingen och matchningen mot handelslängder görs i backend (docs/adr.md ADR-1) -- här
 * visas bara svaret. Den enda härledningen är jämförelsen kaplängd > längsta handelslängd, som
 * markerar bitar ingen enskild inköpslängd täcker (docs/prd.md §0). Hur de faktiskt skarvas
 * avgör backend i inkrement 3, inte den här vyn.
 */
export function BomGroupsView() {
  const { data, error, loading } = useFetch(getBomGroups)

  // Störst materialmängd först -- det är där optimeringen i inkrement 3 har mest att hämta.
  const groups = useMemo(
    () => [...(data?.groups ?? [])].sort((a, b) => b.total_length_mm - a.total_length_mm),
    [data],
  )

  if (loading) return <p>Grupperar och matchar handelslängder...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/bom/groups: {error}</p>
  if (!data) return null

  const pieceCount = groups.reduce((sum, g) => sum + g.piece_count, 0)
  const totalLengthM = groups.reduce((sum, g) => sum + g.total_length_mm, 0) / 1000

  return (
    <section>
      <h2>Artikelmatchning</h2>
      <p className="summary">
        {mm.format(groups.length)} grupper · {mm.format(pieceCount)} bitar ·{' '}
        {meters.format(totalLengthM)} m totalt
      </p>
      <p>
        Grupperat per tvärsnitt och hållfasthetsklass, matchat mot Svenskt Träs standardlängder
        (<code>data/svensktra_standardlangder_mm.csv</code>). Expandera en grupp för
        handelslängder och ingående kapbitar.
      </p>

      {groups.map((group) => (
        <GroupDetails key={`${group.code}-${group.mat_code}`} group={group} />
      ))}
    </section>
  )
}

function GroupDetails({ group }: { group: BomGroup }) {
  const longestTradeLength = Math.max(...group.available_trade_lengths_mm)
  // Längst först: samma ordning som FFD packar i (docs/adr.md ADR-2), och de kritiska
  // bitarna -- de som ingen handelslängd täcker -- hamnar överst.
  const pieces = [...group.pieces].sort((a, b) => b.length_mm - a.length_mm)
  const oversizedCount = pieces.filter((p) => p.length_mm > longestTradeLength).length

  return (
    <details>
      <summary>
        <span className="group-name">
          {group.code} {group.mat_code}
        </span>
        <span>{mm.format(group.piece_count)} bitar</span>
        <span>{meters.format(group.total_length_mm / 1000)} m</span>
        <span>
          kapbitar {mm.format(pieces.at(-1)!.length_mm)}–{mm.format(pieces[0].length_mm)} mm
        </span>
        {oversizedCount > 0 && (
          <span className="flag">{mm.format(oversizedCount)} över handelslängd</span>
        )}
      </summary>

      <p>
        Handelslängder (mm): {group.available_trade_lengths_mm.map((l) => mm.format(l)).join(', ')}
      </p>
      {oversizedCount > 0 && (
        <p>
          {mm.format(oversizedCount)} kapbitar är längre än {mm.format(longestTradeLength)} mm och
          täcks inte av en enskild inköpslängd — de skarvas i inköpsunderlaget (docs/prd.md §3.3).
        </p>
      )}

      <table>
        <thead>
          <tr>
            <th>OID</th>
            <th>Längd (mm)</th>
            <th>Täcks av</th>
          </tr>
        </thead>
        <tbody>
          {pieces.map((piece) => (
            <tr key={piece.oid}>
              <td>{piece.oid}</td>
              <td className="num">{mm.format(piece.length_mm)}</td>
              <td>
                {piece.length_mm > longestTradeLength ? (
                  <span className="flag">skarv</span>
                ) : (
                  `${mm.format(shortestFit(piece.length_mm, group.available_trade_lengths_mm))} mm`
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  )
}

/**
 * Kortaste handelslängd som rymmer kapbiten ensam. Rent informativt i den här vyn -- backend
 * packar flera bitar per stång i inkrement 3, så detta är inte ett inköpsbeslut.
 */
function shortestFit(lengthMm: number, tradeLengthsMm: number[]): number {
  return Math.min(...tradeLengthsMm.filter((l) => l >= lengthMm))
}
