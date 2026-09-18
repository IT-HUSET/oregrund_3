import { useState } from 'react'
import './App.css'
import { BomGroupsView } from './components/BomGroupsView'
import { BomTable } from './components/BomTable'
import { IfcViewer } from './components/IfcViewer'
import { PurchaseOrderView } from './components/PurchaseOrderView'

const TABS = ['Materialbehov', 'Artikelmatchning', 'Inköpsunderlag'] as const
type Tab = (typeof TABS)[number]

function App() {
  const [tab, setTab] = useState<Tab>('Materialbehov')
  const [selectedOid, setSelectedOid] = useState<string | null>(null)
  const [hoveredOid, setHoveredOid] = useState<string | null>(null)
  const showViewer = tab === 'Inköpsunderlag'

  return (
    <div className="app">
      <header>
        <h1>Kaplista & inköpsunderlag</h1>
        <nav>
          {TABS.map((t) => (
            <button key={t} type="button" onClick={() => setTab(t)} disabled={t === tab}>
              {t}
            </button>
          ))}
        </nav>
      </header>

      <div className={showViewer ? 'workspace split' : 'workspace'}>
        {/* Panelen döljs med display:none, inte unmount: 18 MB-filen ska laddas i bakgrunden
            från start, inte när fliken öppnas på scen (docs/prd.md §7). */}
        <div className="ifc-pane" style={{ display: showViewer ? undefined : 'none' }}>
          <IfcViewer
            selectedOid={selectedOid}
            onPickOid={setSelectedOid}
            hoveredOid={hoveredOid}
            onHoverOid={setHoveredOid}
          />
        </div>

        <main>
          {tab === 'Materialbehov' && <BomTable />}
          {tab === 'Artikelmatchning' && <BomGroupsView />}
          {tab === 'Inköpsunderlag' && (
            <PurchaseOrderView
              selectedOid={selectedOid}
              onSelectOid={setSelectedOid}
              hoveredOid={hoveredOid}
              onHoverOid={setHoveredOid}
            />
          )}
        </main>
      </div>
    </div>
  )
}

export default App
