import { useState } from 'react'
import { BomGroupsView } from './components/BomGroupsView'
import { BomTable } from './components/BomTable'
import { IfcViewer } from './components/IfcViewer'
import { PurchaseOrderView } from './components/PurchaseOrderView'

const TABS = ['Materialbehov', 'Artikelmatchning', 'Inköpsunderlag'] as const
type Tab = (typeof TABS)[number]

function App() {
  const [tab, setTab] = useState<Tab>('Materialbehov')
  const [selectedOid, setSelectedOid] = useState<string | null>(null)

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

      <main>
        {tab === 'Materialbehov' && <BomTable />}
        {tab === 'Artikelmatchning' && <BomGroupsView />}
        {tab === 'Inköpsunderlag' && <PurchaseOrderView onSelectOid={setSelectedOid} />}
      </main>

      <IfcViewer selectedOid={selectedOid} />
    </div>
  )
}

export default App
