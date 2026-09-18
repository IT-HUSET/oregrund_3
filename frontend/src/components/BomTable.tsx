import { getBom } from '../api/client'
import { useFetch } from '../api/useFetch'

/** Inkrement 1 (docs/plan.md #1): tabellvy över GET /api/bom. */
export function BomTable() {
  const { data, error, loading } = useFetch(getBom)

  if (loading) return <p>Läser materialbehov...</p>
  if (error) return <p role="alert">Kunde inte läsa /api/bom: {error}</p>
  if (!data) return null

  return (
    <section>
      <h2>Materialbehov ({data.count} rader)</h2>
      <table>
        <thead>
          <tr>
            <th>OID</th>
            <th>Tvärsnitt</th>
            <th>Klass</th>
            <th>Längd (mm)</th>
            <th>Modul</th>
            <th>Funktion</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((item) => (
            <tr key={item.oid}>
              <td>{item.oid}</td>
              <td>{item.code}</td>
              <td>{item.mat_code}</td>
              <td>{item.length_mm}</td>
              <td>{item.module_flat ?? item.module_name}</td>
              <td>{item.use}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
