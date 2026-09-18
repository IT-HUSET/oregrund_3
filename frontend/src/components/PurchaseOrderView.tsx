import { getPurchaseOrder } from '../api/client'
import { useFetch } from '../api/useFetch'
import type { Cut } from '../api/types'

interface PurchaseOrderViewProps {
  /** Inkrement 4 (docs/plan.md #4): klick på en kapbit ska highlighta oid i 3D-vyn. */
  onSelectOid?: (oid: string) => void
}

/** Inkrement 3 (docs/plan.md #3): kaplista, spillrapport och inköpsunderlag. */
export function PurchaseOrderView({ onSelectOid }: PurchaseOrderViewProps) {
  const { data, error, loading } = useFetch(getPurchaseOrder)

  if (loading) return <p>Kör kapoptimering...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/purchase-order: {error}</p>
  if (!data) return null

  function renderCut(cut: Cut) {
    return (
      <button key={cut.oid} type="button" onClick={() => onSelectOid?.(cut.oid)}>
        {cut.oid} ({cut.length_mm} mm)
      </button>
    )
  }

  return (
    <section>
      <h2>Kapoptimering & spillrapport</h2>
      <p>Kerf: {data.kerf_mm} mm. Totalt spill: {data.summary.total_waste_percent.toFixed(1)}%.</p>

      {data.groups.map((group) => (
        <div key={`${group.code}-${group.mat_code}`}>
          <h3>
            {group.code} {group.mat_code} -- spill {group.waste_percent.toFixed(1)}%
          </h3>
          <ul>
            {group.bars.map((bar, i) => (
              <li key={i}>
                Stång {bar.purchase_length_mm} mm, spill {bar.waste_mm} mm:{' '}
                {bar.cuts.map(renderCut)}
              </li>
            ))}
          </ul>
        </div>
      ))}

      <h3>Inköpsunderlag</h3>
      <table>
        <thead>
          <tr>
            <th>Tvärsnitt</th>
            <th>Klass</th>
            <th>Längd (mm)</th>
            <th>Antal</th>
            <th>Artikelnr</th>
            <th>Pris/st (SEK)</th>
            <th>Summa (SEK)</th>
          </tr>
        </thead>
        <tbody>
          {data.order_lines.map((line) => (
            <tr key={line.article_number}>
              <td>{line.code}</td>
              <td>{line.mat_code}</td>
              <td>{line.purchase_length_mm}</td>
              <td>{line.quantity}</td>
              <td>{line.article_number}</td>
              <td>{line.price_per_unit_sek}</td>
              <td>{line.total_price_sek}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>
        Totalt {data.summary.total_bars} stänger, {data.summary.total_cost_sek} SEK (mockat pris,
        se docs/prd.md §4).
      </p>
    </section>
  )
}
