export default function Cargando({ estado, children }) {
  if (estado.error) return <p className="error">{estado.error}</p>
  if (estado.cargando) return <p className="tenue">Cargando…</p>
  return children
}
