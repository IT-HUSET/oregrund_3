import { getBomGroups } from '../api/client'
import { useFetch } from '../api/useFetch'

/** Inkrement 2 (docs/plan.md #2): grupperad vy över GET /api/bom/groups. */
export function BomGroupsView() {
  const { data, error, loading } = useFetch(getBomGroups)

  if (loading) return <p>Grupperar och matchar handelslängder...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/bom/groups: {error}</p>
  if (!data) return null

  return (
    <section>
      <h2>Artikelmatchning ({data.groups.length} grupper)</h2>
      {data.groups.map((group) => (
        <details key={`${group.code}-${group.mat_code}`}>
          <summary>
            {group.code} {group.mat_code} -- {group.piece_count} bitar, {group.total_length_mm} mm totalt
          </summary>
          <p>Handelslängder (mm): {group.available_trade_lengths_mm.join(', ')}</p>
        </details>
      ))}
    </section>
  )
}
