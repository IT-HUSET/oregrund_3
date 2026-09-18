import { useState } from 'react'
import { BomGroupsView } from './components/BomGroupsView'
import { BomTable } from './components/BomTable'
import { IfcViewer } from './components/IfcViewer'
import { PurchaseOrderView } from './components/PurchaseOrderView'

const TABS = ['Materialbehov', 'Artikelmatchning', 'Inköpsunderlag'] as const
type Tab = (typeof TABS)[number]

/**
 * Demoflödet i ordning (docs/prd.md §5): materialbehov -> artikelmatchning -> inköpsunderlag,
 * med 3D-vyn alltid synlig bredvid.
 *
 * Flikarna renderas alla tre och döljs med CSS i stället för att monteras av/på: 3D-vyn ligger
 * kvar och modellen (18 MB) laddas en enda gång (docs/prd.md §7).
 */
function App() {
  const [tab, setTab] = useState<Tab>('Materialbehov')
  const [selectedOid, setSelectedOid] = useState<string | null>(null)

  return (
    <div className="app">
      <header>
        <div>
          <h1>Kaplista &amp; inköpsunderlag</h1>
          <p className="subtitle">
            Lindbäcks Bygg, projekt 772_H811 — från konstruktionsunderlag till spilloptimerat
            inköpsunderlag
          </p>
        </div>
        <nav>
          {TABS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={t === tab ? 'tab tab-active' : 'tab'}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>

      <div className="layout">
        <main>
          <div hidden={tab !== 'Materialbehov'}>
            <BomTable onSelectOid={setSelectedOid} selectedOid={selectedOid} />
          </div>
          <div hidden={tab !== 'Artikelmatchning'}>
            <BomGroupsView onSelectOid={setSelectedOid} selectedOid={selectedOid} />
          </div>
          <div hidden={tab !== 'Inköpsunderlag'}>
            <PurchaseOrderView onSelectOid={setSelectedOid} selectedOid={selectedOid} />
          </div>
        </main>

        <aside>
          <IfcViewer selectedOid={selectedOid} onPickOid={setSelectedOid} />
          {selectedOid && (
            <button type="button" className="clear" onClick={() => setSelectedOid(null)}>
              Rensa markering (OID {selectedOid})
            </button>
          )}
        </aside>
      </div>
    </div>
  )
}

export default App
