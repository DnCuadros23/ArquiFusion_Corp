import { api } from '../api.js'
import { usarDatos } from './usarDatos.js'
import Cargando from './Cargando.jsx'
import { numero } from './util.js'

function Tabla({ titulo, filas, columnas, vacio }) {
  return (
    <section className="tarjeta">
      <h3>{titulo}</h3>
      {filas?.length ? (
        <table>
          <thead><tr>{columnas.map(([, t]) => <th key={t}>{t}</th>)}</tr></thead>
          <tbody>
            {filas.map((f, n) => (
              <tr key={n}>{columnas.map(([k]) => <td key={k}>{typeof f[k] === 'number' ? numero(f[k], 2) : String(f[k] ?? '—')}</td>)}</tr>
            ))}
          </tbody>
        </table>
      ) : <p className="tenue">{vacio}</p>}
    </section>
  )
}

export default function Planificacion({ rol }) {
  const estado = usarDatos(() => api.reporte())
  const r = estado.datos
  return (
    <Cargando estado={estado}>
      {r && (
        <>
          <section className="tarjeta resumen">
            <h2>Resumen del día {r.fecha && <span className="tenue">({r.fecha})</span>}</h2>
            <p>{r.resumen_gerente || 'Sin resumen.'}</p>
            {r.prioridades?.length > 0 && (
              <>
                <b>Prioridades de hoy</b>
                <ol>{r.prioridades.map((p) => <li key={p}>{p}</li>)}</ol>
              </>
            )}
            <p className="tenue pequeno">Resumen redactado por IA a partir de los datos del día; revisar antes de decidir.</p>
          </section>
          <div className="columnas">
            <Tabla titulo="Mantenimiento preventivo" filas={r.preventivo} vacio="Sin máquinas por atender."
              columnas={[['maquina_id', 'Máquina'], ['horas_desde_mant', 'Horas desde el último'], ['carga_media_t', 'Carga media (t)'], ['prioridad', 'Prioridad']]} />
            <Tabla titulo="Combustible fuera de lo esperado" filas={r.combustible} vacio="Sin consumos anormales."
              columnas={[['maquina_id', 'Máquina'], ['modelo', 'Modelo'], ['l_por_t', 'L por tonelada'], ['mediana_modelo', 'Mediana del modelo'], ['exceso_pct', 'Exceso %']]} />
            <Tabla titulo="Utilización" filas={r.utilizacion} vacio="Sin máquinas ociosas ni sobreusadas."
              columnas={[['maquina_id', 'Máquina'], ['tipo', 'Situación'], ['pct_operando', '% operando'], ['horas_dia', 'Horas/día'], ['costo_dia_usd', 'Costo/día USD']]} />
            {rol !== 'gerente' || r.repuestos?.length ? (
              <Tabla titulo="Repuestos" filas={r.repuestos} vacio="Stock suficiente."
                columnas={[['repuesto_id', 'Repuesto'], ['stock', 'Stock'], ['demanda_7d', 'Demanda 7 días'], ['stock_minimo', 'Mínimo']]} />
            ) : null}
          </div>
        </>
      )}
    </Cargando>
  )
}
