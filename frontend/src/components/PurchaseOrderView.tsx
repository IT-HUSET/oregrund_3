import { useState } from 'react'
import { getPurchaseOrder } from '../api/client'
import { useFetch } from '../api/useFetch'
import { formatMeters, formatMm, formatPercent, formatSek } from '../format'
import type { Bar, Cut } from '../api/types'

interface PurchaseOrderViewProps {
  /** Inkrement 4 (docs/plan.md #4): klick på en kapbit ska highlighta oid i 3D-vyn. */
  onSelectOid?: (oid: string) => void
  selectedOid: string | null
}

/** Andel av stången som är kapbitar, för stapeln i kaplistan. */
function barSegments(bar: Bar): { cut: Cut; percent: number }[] {
  return bar.cuts.map((cut) => ({ cut, percent: (cut.length_mm / bar.purchase_length_mm) * 100 }))
}

/** Inkrement 3 (docs/plan.md #3): kaplista, spillrapport och inköpsunderlag. */
export function PurchaseOrderView({ onSelectOid, selectedOid }: PurchaseOrderViewProps) {
  const { data, error, loading } = useFetch(getPurchaseOrder)
  const [openGroup, setOpenGroup] = useState<string | null>(null)

  if (loading) return <p>Kör kapoptimering...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/purchase-order: {error}</p>
  if (!data) return null

  const { summary } = data
  const baseline = summary.baseline

  return (
    <section>
      <div className="section-head">
        <h2>Kapoptimering, spill och inköpsunderlag</h2>
        <p className="lede">
          First-Fit-Decreasing med {formatMm(data.kerf_mm)} mm kerf per snitt
          (docs/adr.md ADR-2).
        </p>
      </div>

      {/* --- Spillrapport ------------------------------------------------------------- */}
      <div className="kpis">
        <div className="kpi kpi-primary">
          <span className="kpi-label">Spill efter optimering</span>
          <span className="kpi-value">{formatPercent(summary.total_waste_percent)} %</span>
          {baseline && (
            <span className="kpi-sub">
              mot {formatPercent(baseline.total_waste_percent)} % utan optimering
            </span>
          )}
        </div>
        {baseline && (
          <div className="kpi kpi-good">
            <span className="kpi-label">Besparing</span>
            <span className="kpi-value">{formatPercent(baseline.saved_percent)} %</span>
            <span className="kpi-sub">
              {formatMeters(baseline.saved_length_mm, 0)} m · {formatSek(baseline.saved_cost_sek)} SEK
            </span>
          </div>
        )}
        <div className="kpi">
          <span className="kpi-label">Stänger att köpa</span>
          <span className="kpi-value">{summary.total_bars}</span>
          {baseline && <span className="kpi-sub">mot {baseline.total_bars} ooptimerat</span>}
        </div>
        <div className="kpi">
          <span className="kpi-label">Virke</span>
          <span className="kpi-value">{formatMeters(summary.total_purchased_length_mm, 0)} m</span>
          <span className="kpi-sub">
            behov {formatMeters(summary.total_needed_length_mm, 0)} m
          </span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Kostnad (mockad)</span>
          <span className="kpi-value">{formatSek(summary.total_cost_sek)}</span>
          <span className="kpi-sub">SEK, se docs/prd.md §4</span>
        </div>
        <div className="kpi">
          <span className="kpi-label">Skarvade bitar</span>
          <span className="kpi-value">{summary.spliced_piece_count}</span>
          <span className="kpi-sub">{summary.total_joints} skarvar — granskas manuellt</span>
        </div>
      </div>

      {summary.spliced_piece_count > 0 && (
        <p className="warning">
          <strong>{summary.spliced_piece_count} kapbitar</strong> är längre än längsta
          handelslängden (5400 mm) och byggs av flera inköpta längder. Systemet löser
          materialtäckning — <strong>inte</strong> var skarven strukturellt får sitta. Raderna är
          märkta för konstruktörsgranskning (docs/prd.md §4).
        </p>
      )}

      <div className="toolbar">
        <a className="button" href="/api/purchase-order.csv" download>
          Exportera inköpsunderlag (CSV)
        </a>
        <a className="button" href="/api/cut-list.csv" download>
          Exportera kaplista (CSV)
        </a>
      </div>

      {/* --- Inköpsunderlag ---------------------------------------------------------- */}
      <h3>Inköpsunderlag ({data.order_lines.length} artiklar)</h3>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Tvärsnitt</th>
              <th>Klass</th>
              <th className="num">Handelslängd (mm)</th>
              <th className="num">Antal</th>
              <th>Artikelnummer</th>
              <th className="num">Pris/st (SEK)</th>
              <th className="num">Summa (SEK)</th>
              <th className="num">Leveranstid</th>
            </tr>
          </thead>
          <tbody>
            {data.order_lines.map((line) => (
              <tr key={line.article_number}>
                <td>{line.code}</td>
                <td>{line.mat_code}</td>
                <td className="num">{line.purchase_length_mm}</td>
                <td className="num">{line.quantity}</td>
                <td className="mono">{line.article_number}</td>
                <td className="num">{formatSek(line.price_per_unit_sek)}</td>
                <td className="num">{formatSek(line.total_price_sek)}</td>
                <td className="num">{line.lead_time_days} dgr</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3}>Totalt</td>
              <td className="num">{summary.total_bars}</td>
              <td colSpan={2} />
              <td className="num">{formatSek(summary.total_cost_sek)}</td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>

      {/* --- Kaplista per grupp ------------------------------------------------------ */}
      <h3>Kaplista ({data.groups.length} grupper)</h3>
      <p className="lede">Klicka en kapbit för att highlighta den i 3D-vyn.</p>

      {data.groups.map((group) => {
        const key = `${group.code}-${group.mat_code}`
        const isOpen = openGroup === key
        return (
          <div key={key} className="group-card">
            <button
              type="button"
              className="group-head"
              onClick={() => setOpenGroup(isOpen ? null : key)}
            >
              <span>
                <strong>{group.code}</strong> {group.mat_code}
              </span>
              <span className="group-meta">
                {group.bars.length} stänger · spill {formatPercent(group.waste_percent)} %
                {group.splices.length > 0 && (
                  <span className="tag tag-splice">{group.splices.length} skarvade</span>
                )}
              </span>
              <span className="chevron">{isOpen ? '▾' : '▸'}</span>
            </button>

            {isOpen && (
              <div className="group-body">
                {group.splices.length > 0 && (
                  <div className="splice-list">
                    <h4>Skarvade kapbitar</h4>
                    <table>
                      <thead>
                        <tr>
                          <th>OID</th>
                          <th className="num">Behövd längd (mm)</th>
                          <th className="num">Segment</th>
                          <th>Byggs av (mm)</th>
                          <th className="num">Skarvar</th>
                        </tr>
                      </thead>
                      <tbody>
                        {group.splices.map((splice) => (
                          <tr
                            key={splice.oid}
                            className={splice.oid === selectedOid ? 'selected clickable' : 'clickable'}
                            onClick={() => onSelectOid?.(splice.oid)}
                          >
                            <td>{splice.oid}</td>
                            <td className="num">{formatMm(splice.total_length_mm)}</td>
                            <td className="num">{splice.segment_count}</td>
                            <td>{splice.purchase_lengths_mm.join(' + ')}</td>
                            <td className="num">{splice.joint_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <h4>Stänger</h4>
                <ol className="bars">
                  {group.bars.map((bar, index) => (
                    <li key={index}>
                      <div className="bar-head">
                        <span className="mono">
                          {group.mat_code}-{group.code}-#{String(index + 1).padStart(3, '0')}
                        </span>
                        <span>{bar.purchase_length_mm} mm</span>
                        <span className="muted">
                          kerf {formatMm(bar.kerf_total_mm)} · spill {formatMm(bar.waste_mm)} mm
                        </span>
                      </div>
                      <div className="bar-viz">
                        {barSegments(bar).map(({ cut, percent }, i) => (
                          <button
                            key={`${cut.oid}-${i}`}
                            type="button"
                            style={{ width: `${percent}%` }}
                            className={[
                              'bar-cut',
                              cut.oid === selectedOid ? 'bar-cut-selected' : '',
                              cut.spliced ? 'bar-cut-spliced' : '',
                            ].join(' ')}
                            title={
                              `OID ${cut.oid} · ${formatMm(cut.length_mm)} mm` +
                              (cut.spliced
                                ? ` · skarvsegment ${cut.segment_index} av ${cut.segment_count}`
                                : '')
                            }
                            onClick={() => onSelectOid?.(cut.oid)}
                          >
                            <span>{cut.oid}</span>
                          </button>
                        ))}
                        <span className="bar-waste" style={{ flex: 1 }} title={`Spill ${formatMm(bar.waste_mm)} mm`} />
                      </div>
                      <div className="bar-cuts">
                        {bar.cuts.map((cut, i) => (
                          <button
                            key={`${cut.oid}-${i}`}
                            type="button"
                            className={cut.oid === selectedOid ? 'chip chip-selected' : 'chip'}
                            onClick={() => onSelectOid?.(cut.oid)}
                          >
                            {cut.oid} · {formatMm(cut.length_mm)} mm
                            {cut.spliced && (
                              <span className="tag tag-splice">
                                skarv {cut.segment_index}/{cut.segment_count}
                              </span>
                            )}
                          </button>
                        ))}
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )
      })}
    </section>
  )
}
