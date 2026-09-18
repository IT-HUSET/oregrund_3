/**
 * CSV-export för inköpsunderlaget (docs/plan.md #3, docs/prd.md §3.5).
 *
 * Semikolon som avgränsare och komma som decimaltecken -- det är vad Excel i svensk lokal
 * förväntar sig, och underlaget ska kunna öppnas och jämföras mot UI:t direkt.
 */

export type CsvValue = string | number

function cell(value: CsvValue): string {
  if (typeof value === 'number') return String(value).replace('.', ',')
  return /[;"\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value
}

export function toCsv(rows: CsvValue[][]): string {
  return rows.map((row) => row.map(cell).join(';')).join('\r\n')
}

export function downloadCsv(filename: string, content: string): void {
  // BOM först, annars tolkar Excel inte UTF-8 och å/ä/ö blir fel.
  const blob = new Blob(['﻿', content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
