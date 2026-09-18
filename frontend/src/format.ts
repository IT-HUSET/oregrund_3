/** Delad sifferformatering. Alla mått är i mm (docs/api-contract.md). */

/** Heltalsgrupperade mm, max en decimal ("3 610,1"). */
export const mm = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 1 })

/** Meter, en decimal ("200,7 m" skrivs som "200,7"). */
export const meters = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 1 })

/** Kronor, två decimaler. Priserna är mockade, se docs/prd.md §4. */
export const sek = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 })

/** Spillprocent, två decimaler -- samma precision som backend skickar och som CSV-exporten
 *  innehåller, så UI och export går att jämföra rakt av (docs/plan.md #3). */
export const percent = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 })
