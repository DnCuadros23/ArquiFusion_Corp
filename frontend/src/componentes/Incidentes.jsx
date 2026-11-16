import { useMemo, useState } from 'react'
import { USA_MOCK, api } from '../api.js'
import { usarDatos } from './usarDatos.js'
import Cargando from './Cargando.jsx'
import DetalleIncidente from './DetalleIncidente.jsx'
import { fecha } from './util.js'

const SEVERIDADES = ['OBSERVACION', 'MEDIA', 'CRITICA']
const ESTADOS = ['DETECTADO', 'ANALIZADO', 'ASIGNADO', 'EN_ATENCION', 'CERRADO', 'DESCARTADO']

export default function Incidentes({ sesion, soloLectura }) {
  const [soloAbiertos, setSoloAbiertos] = useState(true)
  // El gerente arranca viendo solo los críticos
  const [severidad, setSeveridad] = useState(sesion.rol === 'gerente' ? 'CRITICA' : '')
  const [estadoFiltro, setEstadoFiltro] = useState('')
  const [seleccion, setSeleccion] = useState(null)
  const estado = usarDatos(() => api.incidentes(soloAbiertos), [soloAbiertos])

  const lista = useMemo(() => {
    let l = estado.datos || []
    // Con la API real, AWS ya filtra por rol. Con datos de prueba se simula: el técnico ve lo suyo.
    if (USA_MOCK && sesion.rol === 'tecnico') l = l.filter((i) => i.tecnico_asignado?.nombre === sesion.nombre)
    if (severidad) l = l.filter((i) => i.severidad === severidad)
    if (estadoFiltro) l = l.filter((i) => i.estado === estadoFiltro)
    return [...l].sort((a, b) => (b.creado_ts || '').localeCompare(a.creado_ts || ''))
  }, [estado.datos, severidad, estadoFiltro, sesion])

  if (seleccion) {
    return (
      <DetalleIncidente
        id={seleccion}
        sesion={sesion}
        soloLectura={soloLectura}
        volver={() => { setSeleccion(null); estado.recargar() }}
        respaldo={(estado.datos || []).find((i) => i.incidente_id === seleccion)}
      />
    )
  }

  return (
    <>
      <div className="filtros">
        <label><input type="checkbox" checked={soloAbiertos} onChange={(e) => setSoloAbiertos(e.target.checked)} /> Solo abiertos</label>
        <select value={severidad} onChange={(e) => setSeveridad(e.target.value)}>
          <option value="">Toda severidad</option>
          {SEVERIDADES.map((s) => <option key={s}>{s}</option>)}
        </select>
        <select value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)}>
          <option value="">Todo estado</option>
          {ESTADOS.map((s) => <option key={s}>{s}</option>)}
        </select>
        <button className="secundario" onClick={estado.recargar}>Actualizar</button>
      </div>

      <Cargando estado={estado}>
        {lista.length === 0 ? <p className="tenue">No hay incidentes con estos filtros.</p> : (
          <table>
            <thead>
              <tr><th>Fecha</th><th>Máquina</th><th>Zona</th><th>Severidad</th><th>Estado</th><th>Técnico</th><th></th></tr>
            </thead>
            <tbody>
              {lista.map((i) => (
                <tr key={i.incidente_id} onClick={() => setSeleccion(i.incidente_id)} className="clic">
                  <td>{fecha(i.creado_ts)}</td>
                  <td><b>{i.maquina_id}</b> <span className="tenue">{i.modelo}</span></td>
                  <td>{i.zona}</td>
                  <td><span className={`chip sev-${i.severidad}`}>{i.severidad}</span></td>
                  <td>{i.estado}</td>
                  <td>{i.tecnico_asignado?.nombre || '—'}</td>
                  <td>{i.grupo_causa_comun && <span className="chip causa">Posible causa común</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Cargando>
    </>
  )
}
