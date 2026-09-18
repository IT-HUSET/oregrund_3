import { useMemo } from 'react'
import { getPurchaseOrder } from '../api/client'
import { useFetch } from '../api/useFetch'
import type { Cut, GroupCuttingResult, PurchaseOrderResponse } from '../api/types'
import { type CsvValue, downloadCsv, toCsv } from '../csv'
import { meters, mm, percent, sek } from '../format'

const ALGORITHM_LABEL = { greedy: 'girig FFD', exact: 'exakt (CP-SAT)' } as const

interface PurchaseOrderViewProps {
  /** Inkrement 4 (docs/plan.md #4): klick på en kapbit ska highlighta oid i 3D-vyn. */
  onSelectOid?: (oid: string) => void
}

/**
 * Inkrement 3 (docs/plan.md #3): kaplista, spillrapport och inköpsunderlag med CSV-export.
 *
 * Optimeringen körs i backend (docs/adr.md ADR-1/ADR-2) -- här visas och exporteras svaret.
 * Vyn hämtar alltid standardläget (girig FFD); den valbara exakta lösaren tar sekunder till
 * minuter och ska triggas explicit av användaren (docs/api-contract.md), vilket står som eget
 * spår i docs/plan.md ("Tillägg efter demot") och inte ingår här.
 */
export function PurchaseOrderView({ onSelectOid }: PurchaseOrderViewProps) {
  const { data, error, loading } = useFetch(getPurchaseOrder)

  // Störst inköpt materialmängd först -- samma ordning som artikelmatchningen.
  const groups = useMemo(
    () => [...(data?.groups ?? [])].sort((a, b) => purchasedLengthMm(b) - purchasedLengthMm(a)),
    [data],
  )

  if (loading) return <p>Kör kapoptimering...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/purchase-order: {error}</p>
  if (!data) return null

  const { summary } = data

  return (
    <section>
      <h2>Kapoptimering & spillrapport</h2>

      <p className="summary">
        {percent.format(summary.total_waste_percent)} % spill · {mm.format(summary.total_bars)} handelslängder
        · {sek.format(summary.total_cost_sek)} SEK
      </p>
      <p>
        {meters.format(summary.total_purchased_length_mm / 1000)} m inköpt mot{' '}
        {meters.format(summary.total_needed_length_mm / 1000)} m behov. Algoritm:{' '}
        {ALGORITHM_LABEL[data.algorithm]}, kerf {mm.format(data.kerf_mm)} mm.{' '}
        {summary.spliced_piece_count > 0 && (
          <>
            {mm.format(summary.spliced_piece_count)} kapbitar är skarvade över{' '}
            {mm.format(summary.total_joints)} skarvar — skarvens placering är inte strukturellt
            validerad (docs/prd.md §4).
          </>
        )}{' '}
        Pris, artikelnummer och leveranstid är mockade (docs/prd.md §4).
      </p>

      <p className="filter">
        <button type="button" onClick={() => exportOrderLines(data)}>
          Exportera inköpsunderlag (CSV)
        </button>
        <button type="button" onClick={() => exportCuttingList(data)}>
          Exportera kaplista (CSV)
        </button>
      </p>

      <h3>Kaplista</h3>
      {groups.map((group) => (
        <GroupCuts
          key={`${group.code}-${group.mat_code}`}
          group={group}
          onSelectOid={onSelectOid}
        />
      ))}

      <h3>Inköpsunderlag</h3>
      <table>
        <thead>
          <tr>
            <th>Tvärsnitt</th>
            <th>Klass</th>
            <th>Handelslängd (mm)</th>
            <th>Antal</th>
            <th>Artikelnr</th>
            <th>Pris/st (SEK)</th>
            <th>Leveranstid (dagar)</th>
            <th>Summa (SEK)</th>
          </tr>
        </thead>
        <tbody>
          {data.order_lines.map((line) => (
            <tr key={line.article_number}>
              <td>{line.code}</td>
              <td>{line.mat_code}</td>
              <td className="num">{mm.format(line.purchase_length_mm)}</td>
              <td className="num">{mm.format(line.quantity)}</td>
              <td>{line.article_number}</td>
              <td className="num">{sek.format(line.price_per_unit_sek)}</td>
              <td className="num">{line.lead_time_days}</td>
              <td className="num">{sek.format(line.total_price_sek)}</td>
            </tr>
          ))}
          <tr>
            <th colSpan={3}>Totalt</th>
            <th className="num">{mm.format(summary.total_bars)}</th>
            <th colSpan={3} />
            <th className="num">{sek.format(summary.total_cost_sek)}</th>
          </tr>
        </tbody>
      </table>
    </section>
  )
}

function GroupCuts({
  group,
  onSelectOid,
}: {
  group: GroupCuttingResult
  onSelectOid?: (oid: string) => void
}) {
  const splicedOids = new Set(group.splices.map((s) => s.oid))

  return (
    <details>
      <summary>
        <span className="group-name">
          {group.code} {group.mat_code}
        </span>
        <span>{percent.format(group.waste_percent)} % spill</span>
        <span>{mm.format(group.bars.length)} handelslängder</span>
        {splicedOids.size > 0 && (
          <span className="flag">{mm.format(splicedOids.size)} skarvade</span>
        )}
        {/* Girig FFD gör inget optimalitetsanspråk, så "optimal" visas bara för exakt läge
            (docs/api-contract.md, ADR-2-tillägget). */}
        {group.algorithm === 'exact' && (
          <span className={group.optimal ? undefined : 'flag'}>
            {group.optimal ? 'bevisat optimal' : 'bästa hittade'} (
            {mm.format(group.solve_time_ms)} ms)
          </span>
        )}
      </summary>

      <table>
        <thead>
          <tr>
            <th>Handelslängd (mm)</th>
            <th>Kapbitar (OID)</th>
            <th>Använt (mm)</th>
            <th>Kerf (mm)</th>
            <th>Spill (mm)</th>
          </tr>
        </thead>
        <tbody>
          {group.bars.map((bar, index) => (
            <tr key={index}>
              <td className="num">{mm.format(bar.purchase_length_mm)}</td>
              <td>
                {bar.cuts.map((cut) => (
                  <button
                    key={`${cut.oid}-${cut.segment_index ?? 0}`}
                    type="button"
                    className={cut.spliced ? 'cut flag' : 'cut'}
                    onClick={() => onSelectOid?.(cut.oid)}
                  >
                    {cut.oid} · {mm.format(cut.length_mm)} mm{segmentLabel(cut)}
                  </button>
                ))}
              </td>
              <td className="num">{mm.format(bar.used_length_mm)}</td>
              <td className="num">{mm.format(bar.kerf_total_mm)}</td>
              <td className="num">{mm.format(bar.waste_mm)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {group.splices.length > 0 && (
        <>
          <h4>Skarvade kapbitar</h4>
          <table>
            <thead>
              <tr>
                <th>OID</th>
                <th>Behovslängd (mm)</th>
                <th>Byggd av (mm)</th>
                <th>Skarvar</th>
              </tr>
            </thead>
            <tbody>
              {group.splices.map((splice) => (
                <tr key={splice.oid}>
                  <td>{splice.oid}</td>
                  <td className="num">{mm.format(splice.total_length_mm)}</td>
                  <td>{splice.purchase_lengths_mm.map((l) => mm.format(l)).join(' + ')}</td>
                  <td className="num">{splice.joint_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </details>
  )
}

function segmentLabel(cut: Cut): string {
  return cut.spliced ? ` (skarv ${cut.segment_index}/${cut.segment_count})` : ''
}

function purchasedLengthMm(group: GroupCuttingResult): number {
  return group.bars.reduce((sum, bar) => sum + bar.purchase_length_mm, 0)
}

function exportOrderLines(data: PurchaseOrderResponse): void {
  const rows: CsvValue[][] = [
    [
      'Tvärsnitt',
      'Klass',
      'Handelslängd (mm)',
      'Antal',
      'Artikelnummer',
      'Pris/st (SEK)',
      'Leveranstid (dagar)',
      'Summa (SEK)',
    ],
    ...data.order_lines.map((line): CsvValue[] => [
      line.code,
      line.mat_code,
      line.purchase_length_mm,
      line.quantity,
      line.article_number,
      line.price_per_unit_sek,
      line.lead_time_days,
      line.total_price_sek,
    ]),
    [],
    ['Algoritm', data.algorithm],
    ['Kerf (mm)', data.kerf_mm],
    ['Antal handelslängder', data.summary.total_bars],
    ['Behov (mm)', data.summary.total_needed_length_mm],
    ['Inköpt (mm)', data.summary.total_purchased_length_mm],
    ['Spill (%)', data.summary.total_waste_percent],
    ['Skarvade kapbitar', data.summary.spliced_piece_count],
    ['Skarvar totalt', data.summary.total_joints],
    ['Total kostnad (SEK, mockat pris)', data.summary.total_cost_sek],
  ]

  downloadCsv('inkopsunderlag.csv', toCsv(rows))
}

/**
 * Kaplistan per kapbit. Skarvade bitar måste vara märkta även här, inte bara i UI:t
 * (docs/prd.md §3.3) -- annars kan en skarvad bit läsas som en enda odelad längd nedströms.
 */
function exportCuttingList(data: PurchaseOrderResponse): void {
  const rows: CsvValue[][] = [
    [
      'Tvärsnitt',
      'Klass',
      'Handelslängd (mm)',
      'OID',
      'Kaplängd (mm)',
      'Skarvad',
      'Segment',
      'Använt på handelslängden (mm)',
      'Kerf (mm)',
      'Spill (mm)',
    ],
  ]

  for (const group of data.groups) {
    group.bars.forEach((bar) => {
      for (const cut of bar.cuts) {
        rows.push([
          group.code,
          group.mat_code,
          bar.purchase_length_mm,
          cut.oid,
          cut.length_mm,
          cut.spliced ? 'ja' : 'nej',
          cut.spliced ? `${cut.segment_index}/${cut.segment_count}` : '',
          bar.used_length_mm,
          bar.kerf_total_mm,
          bar.waste_mm,
        ])
      }
    })
  }

  downloadCsv('kaplista.csv', toCsv(rows))
}
