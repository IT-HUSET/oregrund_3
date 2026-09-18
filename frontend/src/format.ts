/** Delade formaterare. Svenska tal (decimalkomma) — underlaget läses av svenska inköpare. */

export function formatMm(value: number, decimals = 1): string {
  return value.toLocaleString('sv-SE', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatMeters(mm: number, decimals = 1): string {
  return (mm / 1000).toLocaleString('sv-SE', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatSek(value: number): string {
  return value.toLocaleString('sv-SE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export function formatPercent(value: number, decimals = 2): string {
  return value.toLocaleString('sv-SE', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}
