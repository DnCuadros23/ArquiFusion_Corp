import { api } from '../api.js'
import { usarDatos } from './usarDatos.js'
import Cargando from './Cargando.jsx'

export default function Tecnicos() {
  const estado = usarDatos(() => api.tecnicos())
  return (
    <Cargando estado={estado}>
      <table>
        <thead><tr><th>Técnico</th><th>Especialidad</th><th>Zona</th><th>Disponible</th><th>Incidentes activos</th></tr></thead>
        <tbody>
          {(estado.datos || []).map((t) => (
            <tr key={t.tecnico_id}>
              <td><b>{t.nombre}</b> <span className="tenue">{t.tecnico_id}</span></td>
              <td>{t.especialidad}</td>
              <td>{t.zona}</td>
              <td>{t.disponible ? <span className="chip ok">sí</span> : <span className="chip">ocupado</span>}</td>
              <td>{t.incidentes_activos}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Cargando>
  )
}
