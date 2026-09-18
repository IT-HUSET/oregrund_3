/** Delad sifferformatering. Alla mått är i mm (docs/api-contract.md). */

/** Heltalsgrupperade mm, max en decimal ("3 610,1"). */
export const mm = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 1 })

/** Meter, en decimal ("200,7 m" skrivs som "200,7"). */
export const meters = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 1 })
