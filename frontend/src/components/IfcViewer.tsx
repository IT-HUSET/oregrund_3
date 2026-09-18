interface IfcViewerProps {
  /** oid att highlighta (== IFCBEAM.Tag). Sätts av PurchaseOrderView.onSelectOid. */
  selectedOid: string | null
}

/**
 * Platshållare för inkrement 4 (docs/plan.md #4, docs/adr.md ADR-3).
 *
 * Riktig implementation: web-ifc + three.js laddar data/772_H811_new.ifc i webbläsaren,
 * bygger en expressID <-> Tag-karta vid inläsning, och slår upp `selectedOid` mot Tag för att
 * highlighta rätt element. Backend öppnar aldrig .ifc-filen (ADR-3) -- allt detta är
 * klientkod. Se docs/prd.md §7 för risker (18 MB-filen, ladda tidigt/i bakgrunden).
 */
export function IfcViewer({ selectedOid }: IfcViewerProps) {
  return (
    <section>
      <h2>3D-vy</h2>
      <div style={{ border: '1px dashed #999', padding: '2rem', textAlign: 'center' }}>
        <p>IFC-viewer ej implementerad än (inkrement 4).</p>
        <p>Vald oid: {selectedOid ?? '(ingen)'}</p>
      </div>
    </section>
  )
}
